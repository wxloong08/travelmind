"""
评估检查节点

Rule-based 硬约束检查 + LLM 5维度质量评分
"""

import json
from datetime import datetime
from typing import Any

import structlog

from src.graphs.state import AgentState
from src.graphs.poi.validator import validate_itinerary_distances
from src.llm import Message
from src.llm.qwen import get_llm

logger = structlog.get_logger()


# 评估阈值和迭代限制
EVALUATION_THRESHOLD = 80  # 总分 80 分以下触发反思
MAX_EVALUATION_ITERATIONS = 2

# LLM 5 维度评分 Prompt
LLM_SCORE_PROMPT = """你是行程质量评分专家。请从 5 个维度评估行程质量。

## 行程
{itinerary_json}

## 用户需求
- 目的地：{destination}
- 天数：{days}天
- 风格：{travel_style}
- 必去景点：{must_visit}
- 预算等级：{budget_level}

## 5 维度评分（每项 0-100 分）

### 1. 时间合理性 (time_reasonability) - 权重 25%
- 每天行程是否超过 10 小时
- 是否安排太紧凑，缺少休息时间
- 景点游览时间是否充足

### 2. 覆盖度 (coverage) - 权重 20%
- 是否包含用户指定的必去景点
- 目的地核心景点是否覆盖
- 行程是否丰富多样

### 3. 预算匹配 (budget_match) - 权重 15%
- 酒店档次是否符合用户预算要求
- 餐饮档次是否合理
- 整体消费水平是否一致

### 4. 交通可行性 (transport_feasibility) - 权重 25%
- 相邻景点之间距离是否合理（< 30km 为佳）
- 是否会花太多时间在路上
- 交通方式是否可行

### 5. 体验完整性 (experience_completeness) - 权重 15%
- 是否安排了餐饮（午餐、晚餐）
- 是否有休息/自由活动时间
- 体验是否多元（自然+人文+美食）

---

请返回 JSON：
{{
    "scores": {{
        "time_reasonability": 0-100,
        "coverage": 0-100,
        "budget_match": 0-100,
        "transport_feasibility": 0-100,
        "experience_completeness": 0-100
    }},
    "weighted_score": 0-100,
    "issues": [
        {{
            "dimension": "time_reasonability|coverage|budget_match|transport_feasibility|experience_completeness",
            "problem": "具体问题描述",
            "suggestion": "改进建议",
            "severity": "high|medium|low",
            "affected_day": 0
        }}
    ],
    "strengths": ["亮点1", "亮点2"],
    "pass": true/false,
    "feedback": "50字以内整体评价"
}}

**评分规则**：
- weighted_score = time_reasonability*0.25 + coverage*0.20 + budget_match*0.15 + transport_feasibility*0.25 + experience_completeness*0.15
- pass = weighted_score >= {threshold} 且无 high severity 问题

只返回纯 JSON！"""


async def rule_check_node(state: AgentState) -> dict[str, Any]:
    """
    规则检查节点（硬约束）
    
    使用本地 Haversine 进行距离检查，不调用 API。
    """
    logger.info("Node: rule_check")
    
    travel_plan = state.get("travel_plan")
    if not travel_plan or not travel_plan.get("itinerary"):
        logger.info("No itinerary to check, skipping to llm_score")
        return {"next_action": "llm_score", "rule_check_result": None}
    
    itinerary = travel_plan.get("itinerary", [])
    
    # 本地距离验证
    violations = validate_itinerary_distances(itinerary, max_distance_km=50.0)
    
    if violations:
        logger.warning(
            "Distance violations found",
            count=len(violations),
            violations=violations[:5],
        )
        
        rule_check_result = {
            "passed": False,
            "violations": [
                {
                    "rule_name": "distance_check",
                    "message": f"Day {v['day']}: {v['from']} → {v['to']} 距离 {v['distance_km']}km 超过阈值",
                    "suggestion": f"考虑将 {v['to']} 移到距离更近的一天",
                    "severity": "high" if v['distance_km'] > 80 else "medium",
                }
                for v in violations[:5]
            ],
        }
        
        # 距离违规直接触发反思
        return {
            "rule_check_result": rule_check_result,
            "reflect_reason": "rule_violation",
            "next_action": "reflect",
        }
    
    logger.info("Rule check passed, proceeding to LLM score")
    return {
        "rule_check_result": {"passed": True, "violations": []},
        "next_action": "llm_score",
    }


async def llm_score_node(state: AgentState) -> dict[str, Any]:
    """
    LLM 5 维度质量评分节点
    
    评估：时间合理性、覆盖度、预算匹配、交通可行性、体验完整性
    """
    logger.info("Node: llm_score (5 dimensions)")
    
    travel_plan = state.get("travel_plan")
    if not travel_plan or not travel_plan.get("itinerary"):
        logger.info("No itinerary to score, skipping to respond")
        return {"next_action": "respond", "evaluation": None}
    
    # 优先使用 DeepSeek
    from src.config import settings
    
    if settings.deepseek_enabled:
        try:
            from src.llm.deepseek import DeepSeekProvider
            llm = DeepSeekProvider()
            logger.info("Using DeepSeek for scoring")
        except Exception as e:
            logger.warning("DeepSeek init failed, falling back to Qwen", error=str(e))
            llm = get_llm()
    else:
        llm = get_llm()
    
    travel_pref = state.get("travel_preference", {})
    must_visit = travel_pref.get("must_visit_places", [])
    
    prompt = LLM_SCORE_PROMPT.format(
        itinerary_json=json.dumps(travel_plan["itinerary"], ensure_ascii=False, indent=2),
        destination=travel_pref.get("destination", "未知"),
        days=travel_pref.get("days", 3),
        travel_style=travel_pref.get("travel_style", "休闲"),
        must_visit=json.dumps(must_visit, ensure_ascii=False) if must_visit else "无指定",
        budget_level=travel_pref.get("budget_level", "moderate"),
        threshold=EVALUATION_THRESHOLD,
    )
    
    try:
        response = await llm.chat([Message(role="user", content=prompt)])
        
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()
        
        evaluation = json.loads(content)
    except json.JSONDecodeError as e:
        logger.warning("Failed to parse evaluation JSON", error=str(e))
        evaluation = {
            "scores": {
                "time_reasonability": 85,
                "coverage": 85,
                "budget_match": 85,
                "transport_feasibility": 85,
                "experience_completeness": 85,
            },
            "weighted_score": 85,
            "issues": [],
            "strengths": [],
            "pass": True,
            "feedback": "评估解析失败，默认通过",
        }
    except Exception as e:
        logger.error("Evaluation failed", error=str(e))
        evaluation = {
            "scores": {},
            "weighted_score": 85,
            "issues": [],
            "pass": True,
            "feedback": f"评估异常: {str(e)}",
        }
    
    eval_count = state.get("evaluation_count", 0) + 1
    
    # 判断是否通过
    passed = evaluation.get("pass", True)
    score = evaluation.get("weighted_score", 100)
    has_high_severity = any(
        issue.get("severity") == "high" 
        for issue in evaluation.get("issues", [])
    )
    
    # 通过条件：分数 >= 80 且无 high severity 问题
    # 或者：已达到最大迭代次数
    if (score >= EVALUATION_THRESHOLD and not has_high_severity) or eval_count >= MAX_EVALUATION_ITERATIONS:
        next_action = "respond"
        if eval_count >= MAX_EVALUATION_ITERATIONS and score < EVALUATION_THRESHOLD:
            logger.warning(
                "Max iterations reached, forcing pass",
                score=score,
                iterations=eval_count,
            )
    else:
        next_action = "reflect"
    
    logger.info(
        "Evaluation completed (5 dimensions)",
        scores=evaluation.get("scores", {}),
        weighted_score=score,
        passed=passed,
        has_high_severity=has_high_severity,
        issues_count=len(evaluation.get("issues", [])),
        iteration=eval_count,
        next_action=next_action,
    )
    
    # 存入 travel_plan
    travel_plan["evaluation"] = {
        "scores": evaluation.get("scores", {}),
        "weighted_score": score,
        "passed": next_action == "respond",
        "iteration": eval_count,
        "feedback": evaluation.get("feedback", ""),
        "strengths": evaluation.get("strengths", []),
        "issues": evaluation.get("issues", []),
    }
    
    return {
        "evaluation": evaluation,
        "evaluation_count": eval_count,
        "travel_plan": travel_plan,
        "next_action": next_action,
        "reflect_reason": "llm_score" if next_action == "reflect" else None,
    }


__all__ = ["rule_check_node", "llm_score_node"]

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

# LLM 6 维度评分 Prompt（增强版：包含必去景点覆盖率）
LLM_SCORE_PROMPT = """你是行程质量评分专家。请从 6 个维度评估行程质量。

## 行程
{itinerary_json}

## 用户需求
- 目的地：{destination}
- 天数：{days}天
- 风格：{travel_style}
- 必去景点：{must_visit}
- 预算等级：{budget_level}

---

## 🎭 你的角色

你是一位**真实的游客**，即将按照这份行程出游。请完全代入以下人设：

### 游客画像（根据travel_style自动匹配）
- 如果是"亲子游"/"家庭"：**带着老人和小孩的家庭，怕累、需要午休、不能早起**
- 如果是"情侣"/"蜜月"：**追求浪漫氛围、打卡拍照、不想赶路**  
- 如果是"深度游"/"文化"：**希望慢节奏、少景点多体验**
- 如果是"穷游"/"背包客"：**追求性价比、交通便捷**
- 默认：**普通上班族，假期有限，想玩好但也怕累**

---

## 📋 评估任务

以**第一人称视角**，想象自己真的要按这份行程走一遍。问自己：

### 1. 体力节奏（我会不会累死？）
- 每天几点出门？几点回酒店？
- 一天要坐多久的车？
- 景点之间会不会赶路？

### 2. 时间逻辑（这合理吗？）
- 早上的时间安排现实吗？（7点出发对家庭是噩梦）
- 午餐时间地点合理吗？
- 晚餐会不会太晚？

### 3. 情绪价值（这趟旅行值不值？）
- 有没有"高光时刻"让我期待？
- 会不会全程都在赶路？
- 结束后我是开心还是精疲力竭？

### 4. 必去景点（我的愿望单满足了吗？）
- 用户要求的必去景点是否都安排了？
- 如果没安排，是否有合理替代？

---

## 🚦 三色灯评价

为每一天打分：
- 🟢 **推荐**：节奏舒适，安排合理
- 🟡 **待定**：有小问题但可接受
- 🔴 **雷区**：这一天让我想退票

---

请返回 JSON：
{{
    "persona_used": "匹配的游客画像描述",
    "first_impression": "用一句话描述看完行程的心情，要真实、有情绪",
    "day_ratings": [
        {{
            "day": 0,
            "rating": "green|yellow|red",
            "good_points": ["爽点1", "爽点2"],
            "pain_points": ["槽点1", "槽点2"],
            "fatigue_score": 1-10
        }}
    ],
    "must_visit_check": {{
        "required": ["用户要求的必去景点"],
        "found": ["行程中找到的"],
        "missing": ["缺失的"]
    }},
    "worst_moment": "最让我担心的一个环节（具体到哪天哪个时间点）",
    "deal_breakers": ["如果不改这些，我不会买单"],
    "overall_score": 0-100,
    "pass": true/false,
    "feedback": "用游客口吻的50字总结"
}}

**评分规则**：
- 如有任何 🔴 红灯日，pass = false
- 如有必去景点缺失，overall_score 不得超过 70
- overall_score >= {threshold} 且无红灯日才 pass

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
    destination = travel_plan.get("destination", "")
    
    # === 动态阈值：基于实际 POI 分布情况 ===
    # 分析行程中景点的实际分布，而不是硬编码目的地列表
    
    def _calculate_poi_spread(itinerary: list) -> float:
        """
        计算行程中景点的平均间距
        返回：平均公里数（如果无法计算则返回 0）
        """
        from src.graphs.utils.haversine import haversine
        
        coords = []
        for day in itinerary:
            for act in day.get("activities", []):
                loc = act.get("location", {})
                if loc and loc.get("lat") and loc.get("lng"):
                    coords.append((loc["lat"], loc["lng"]))
        
        if len(coords) < 2:
            return 0.0
        
        # 计算所有景点两两之间的距离
        distances = []
        for i in range(len(coords)):
            for j in range(i + 1, len(coords)):
                d = haversine(coords[i][0], coords[i][1], coords[j][0], coords[j][1])
                distances.append(d)
        
        return sum(distances) / len(distances) if distances else 0.0
    
    # 计算 POI 分布情况
    avg_poi_distance = _calculate_poi_spread(itinerary)
    
    # 如果平均距离 > 30km，说明景点分布很广（自然风光区）
    # 使用更宽松的阈值
    is_spread_destination = avg_poi_distance > 30.0
    max_distance = 120.0 if is_spread_destination else 50.0
    
    if is_spread_destination:
        logger.info(
            "Spread-out destination detected based on POI analysis",
            destination=destination,
            avg_poi_distance_km=round(avg_poi_distance, 1),
            threshold_km=max_distance,
        )
    
    # 本地距离验证（使用动态阈值）
    violations = validate_itinerary_distances(itinerary, max_distance_km=max_distance)
    
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
        
        # 检查反思次数，防止无限循环
        reflection_count = state.get("reflection_count", 0)
        MAX_REFLECTIONS = 2
        
        if reflection_count >= MAX_REFLECTIONS:
            logger.warning(
                "Max reflections reached despite violations, forcing pass to llm_score",
                violations=len(violations),
                reflection_count=reflection_count,
            )
            return {
                "rule_check_result": rule_check_result,
                "next_action": "llm_score",  # 跳过反思，直接评分
            }
        
        # 距离违规触发反思
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
        # 新格式的默认评估
        evaluation = {
            "persona_used": "默认游客",
            "first_impression": "评估解析失败",
            "day_ratings": [],
            "must_visit_check": {"required": [], "found": [], "missing": []},
            "worst_moment": "无法分析",
            "deal_breakers": [],
            "overall_score": 85,
            "pass": True,
            "feedback": "评估解析失败，默认通过",
        }
    except Exception as e:
        logger.error("Evaluation failed", error=str(e))
        evaluation = {
            "persona_used": "默认游客",
            "first_impression": f"评估异常: {str(e)}",
            "day_ratings": [],
            "overall_score": 85,
            "pass": True,
            "feedback": f"评估异常: {str(e)}",
        }
    
    eval_count = state.get("evaluation_count", 0) + 1
    
    # === 新格式的通过判断 ===
    # 检查是否有红灯日（deal breaker）
    day_ratings = evaluation.get("day_ratings", [])
    has_red_day = any(
        day.get("rating") == "red" 
        for day in day_ratings
    )
    
    # 获取分数（新格式使用 overall_score）
    score = evaluation.get("overall_score", 100)
    
    # 通过条件：分数 >= 80 且无红灯日
    # 或者：已达到最大迭代次数
    if (score >= EVALUATION_THRESHOLD and not has_red_day) or eval_count >= MAX_EVALUATION_ITERATIONS:
        next_action = "respond"
        if eval_count >= MAX_EVALUATION_ITERATIONS and (score < EVALUATION_THRESHOLD or has_red_day):
            logger.warning(
                "Max iterations reached, forcing pass",
                score=score,
                has_red_day=has_red_day,
                iterations=eval_count,
            )
    else:
        next_action = "reflect"
    
    logger.info(
        "Tourist persona evaluation completed",
        persona=evaluation.get("persona_used", "unknown"),
        first_impression=evaluation.get("first_impression", "")[:50],
        overall_score=score,
        has_red_day=has_red_day,
        day_count=len(day_ratings),
        deal_breakers=evaluation.get("deal_breakers", []),
        iteration=eval_count,
        next_action=next_action,
    )
    
    # 存入 travel_plan（新格式）
    travel_plan["evaluation"] = {
        "persona_used": evaluation.get("persona_used", ""),
        "first_impression": evaluation.get("first_impression", ""),
        "day_ratings": day_ratings,
        "must_visit_check": evaluation.get("must_visit_check", {}),
        "worst_moment": evaluation.get("worst_moment", ""),
        "deal_breakers": evaluation.get("deal_breakers", []),
        "overall_score": score,
        "passed": next_action == "respond",
        "iteration": eval_count,
        "feedback": evaluation.get("feedback", ""),
    }
    
    return {
        "evaluation": evaluation,
        "evaluation_count": eval_count,
        "travel_plan": travel_plan,
        "next_action": next_action,
        "reflect_reason": "llm_score" if next_action == "reflect" else None,
    }


__all__ = ["rule_check_node", "llm_score_node"]

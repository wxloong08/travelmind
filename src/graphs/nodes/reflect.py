"""
反思优化节点

根据评估反馈针对性修改行程
"""

import json
from datetime import datetime
from typing import Any

import structlog

from src.graphs.state import AgentState
from src.llm import Message
from src.llm.qwen import get_llm

logger = structlog.get_logger()


REFLECT_PROMPT = """你是一个行程优化专家。请根据评估反馈修改行程。

## 当前行程
{current_itinerary}

## 评估反馈（需要修改的问题）
{evaluation_issues}

## 修改要求
1. **只修改有问题的部分**，保留好的安排
2. 针对每个 issue 进行具体修改
3. 保持 JSON 格式完全一致
4. 保留每个活动的 poi_id 和 location 字段

请返回修改后的完整 itinerary JSON 数组。

只返回纯 JSON 数组！"""


async def reflect_node(state: AgentState) -> dict[str, Any]:
    """
    反思优化节点
    
    根据规则违规或 LLM 评分反馈优化行程。
    有最大反思次数限制，防止无限循环。
    """
    logger.info("Node: reflect")
    
    # 使用顶层 state 字段追踪反思次数（更可靠）
    current_reflection_count = state.get("reflection_count", 0)
    MAX_REFLECTIONS = 2
    
    logger.info("Reflection count check", current=current_reflection_count, max=MAX_REFLECTIONS)
    
    if current_reflection_count >= MAX_REFLECTIONS:
        logger.warning(
            "Max reflection count reached, skipping to respond",
            reflection_count=current_reflection_count,
            max=MAX_REFLECTIONS,
        )
        return {"next_action": "respond"}
    
    reflect_reason = state.get("reflect_reason", "llm_score")
    travel_plan = state.get("travel_plan", {})
    
    if not travel_plan:
        logger.info("No travel_plan to reflect on, continuing to llm_score")
        return {"next_action": "llm_score"}
    
    llm = get_llm()
    
    # 根据反思来源构建 issues
    if reflect_reason == "rule_violation":
        rule_check_result = state.get("rule_check_result", {})
        violations = rule_check_result.get("violations", [])
        
        if not violations:
            logger.info("No rule violations to fix, continuing to llm_score")
            return {"next_action": "llm_score"}
        
        issues_to_fix = [
            {
                "dimension": v.get("rule_name"),
                "problem": v.get("message"),
                "suggestion": v.get("suggestion"),
                "severity": v.get("severity"),
            }
            for v in violations
            if v.get("severity") in ("critical", "high", "medium")
        ]
        logger.info("Reflecting on rule violations", count=len(issues_to_fix))
    else:
        evaluation = state.get("evaluation", {})
        issues_to_fix = [
            issue for issue in evaluation.get("issues", [])
            if issue.get("severity") in ["high", "medium"]
        ]
        
        if not issues_to_fix:
            logger.info("No high/medium severity issues, continuing to respond")
            return {"next_action": "respond"}
        
        logger.info("Reflecting on LLM evaluation issues", count=len(issues_to_fix))
    
    prompt = REFLECT_PROMPT.format(
        current_itinerary=json.dumps(travel_plan["itinerary"], ensure_ascii=False, indent=2),
        evaluation_issues=json.dumps(issues_to_fix, ensure_ascii=False, indent=2),
    )
    
    try:
        response = await llm.chat([Message(role="user", content=prompt)])
        
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()
        
        improved_itinerary = json.loads(content)
        
        if isinstance(improved_itinerary, list) and len(improved_itinerary) > 0:
            travel_plan["itinerary"] = improved_itinerary
            travel_plan["reflection_applied"] = True
            travel_plan["reflection_count"] = travel_plan.get("reflection_count", 0) + 1
            logger.info(
                "Reflection applied successfully",
                days_count=len(improved_itinerary),
                reflection_count=travel_plan["reflection_count"],
            )
        else:
            logger.warning("Invalid reflection output format, keeping original")
            
    except json.JSONDecodeError as e:
        logger.warning("Failed to parse reflection JSON", error=str(e))
    except Exception as e:
        logger.error("Reflection failed", error=str(e))
    
    # 反思后重新验证，同时增加反思计数
    return {
        "travel_plan": travel_plan,
        "reflection_count": current_reflection_count + 1,  # 顶层 state 字段，确保持久化
        "route_enriched": False,
        "next_action": "route_enrich",
        "updated_at": datetime.now().isoformat(),
    }


__all__ = ["reflect_node"]

"""
反思优化节点

增强版：检测信息缺失类问题 → 触发补充搜索
"""

import json
from datetime import datetime
from typing import Any

import structlog

from src.graphs.state import AgentState
from src.llm import Message
from src.llm.qwen import get_llm

logger = structlog.get_logger()


REFLECT_PROMPT = """你是一个行程优化专家。请根据游客视角的评估反馈修改行程。

## 当前行程
{current_itinerary}

## 评估反馈（游客槽点）
{evaluation_issues}

## 核心修复策略

### 🔴 如果有"红灯日"或"疲劳度高"的问题：
1. **连续远郊问题**：在两个远郊景点之间插入一天市区/近郊轻松游
2. **早起问题**：将 7:00-8:00 出发改为 8:30-9:00 出发
3. **一天多景点**：减少当天景点数量，保留最核心的 1-2 个
4. **晚归问题**：提前结束当天行程，预留晚餐和休息时间

### 🟡 如果是"节奏赶"的问题：
1. 增加景点之间的自由活动/休息时间
2. 午餐时间至少安排 1-1.5 小时
3. 删除可选景点，保留必去景点

### 具体修改示例：
- 原："7:00 出发去巴松措" → 改为 "8:30 出发去巴松措"
- 原：Day1 巴松措 + Day2 雅鲁藏布大峡谷 → 在中间插入 "Day2 林芝市区休整日"
- 原："打车 20 分钟到巴松措" → 改为 "包车 2.5 小时到巴松措"

## 修改要求
1. **只修改有问题的部分**，保留好的安排
2. **必须解决至少一个红灯问题**
3. 保持 JSON 格式完全一致
4. 保留每个活动的 poi_id 和 location 字段

请返回修改后的完整 itinerary JSON 数组。

只返回纯 JSON 数组！"""


def _is_info_deficiency_issue(issue: dict) -> tuple[bool, str | None]:
    """
    判断问题是否属于"信息缺失"类
    
    Returns:
        (是否信息缺失, 需要搜索的查询)
    """
    dimension = issue.get("dimension", "")
    problem = issue.get("problem", "")
    suggestion = issue.get("suggestion", "")
    
    # 必去景点未覆盖 → 需要补充搜索该景点攻略
    if dimension == "coverage" and "必去景点" in problem:
        # 尝试提取景点名
        import re
        match = re.search(r"必去景点[「『【]?([^」』】]+)[」』】]?未", problem)
        if match:
            place_name = match.group(1).strip()
            return True, f"{place_name} 攻略 怎么玩 游玩时间"
        # 兜底
        if "未在行程中" in problem or "未覆盖" in problem:
            return True, None
    
    # 信息充分度不足
    if dimension == "info_sufficiency" and issue.get("severity") in ["high", "critical"]:
        return True, suggestion if suggestion else None
    
    # 缺少某类信息
    if "缺少" in problem or "缺失" in problem or "信息不足" in problem:
        return True, suggestion if suggestion else None
    
    return False, None


async def reflect_node(state: AgentState) -> dict[str, Any]:
    """
    反思优化节点（增强版）
    
    1. 检测问题类型：信息缺失 vs 逻辑问题
    2. 信息缺失 → 触发 supplementary_search
    3. 逻辑问题 → LLM 改写
    4. 有最大反思次数限制，防止无限循环
    """
    logger.info("Node: reflect (enhanced)")
    
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
    travel_pref = state.get("travel_preference", {})
    destination = travel_pref.get("destination", "")
    
    if not travel_plan:
        logger.info("No travel_plan to reflect on, continuing to llm_score")
        return {"next_action": "llm_score"}
    
    # ========== 收集需要处理的问题 ==========
    issues_to_fix = []
    
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
        # === 新格式：从 deal_breakers 和 day_ratings 提取问题 ===
        evaluation = state.get("evaluation", {})
        
        # 1. 从 deal_breakers 获取致命问题
        deal_breakers = evaluation.get("deal_breakers", [])
        
        # 2. 从 day_ratings 中获取红灯日的 pain_points
        day_ratings = evaluation.get("day_ratings", [])
        red_day_issues = []
        for day in day_ratings:
            if day.get("rating") == "red":
                for pain in day.get("pain_points", []):
                    red_day_issues.append({
                        "dimension": "experience",
                        "problem": f"Day {day.get('day', '?')}: {pain}",
                        "suggestion": "重新调整该天的行程节奏",
                        "severity": "high",
                    })
        
        # 3. 从 worst_moment 添加关键问题
        worst_moment = evaluation.get("worst_moment", "")
        if worst_moment and worst_moment != "无法分析":
            red_day_issues.append({
                "dimension": "experience",
                "problem": f"最担心环节: {worst_moment}",
                "suggestion": "重点调整该时间段安排",
                "severity": "high",
            })
        
        # 合并所有问题
        issues_to_fix = [
            {"dimension": "deal_breaker", "problem": db, "suggestion": "必须解决", "severity": "high"}
            for db in deal_breakers
        ] + red_day_issues
        
        if not issues_to_fix:
            logger.info("No deal_breakers or red days, continuing to respond")
            return {"next_action": "respond"}
        
        logger.info("Reflecting on tourist persona issues", count=len(issues_to_fix), deal_breakers=len(deal_breakers))
    
    # ========== 关键增强：检测信息缺失类问题 ==========
    supplementary_count = state.get("supplementary_search_count", 0)
    
    for issue in issues_to_fix:
        is_info_deficiency, query = _is_info_deficiency_issue(issue)
        
        if is_info_deficiency and supplementary_count < 1:
            # 信息缺失 → 触发补充搜索
            fallback_query = query
            if not fallback_query and destination:
                # 构建通用查询
                must_visit = travel_pref.get("must_visit_places", [])
                if must_visit:
                    fallback_query = f"{destination} {must_visit[0]} 攻略 详细行程"
                else:
                    fallback_query = f"{destination} 旅游攻略 景点推荐"
            
            if fallback_query:
                logger.info(
                    "Info deficiency detected, triggering supplementary search",
                    issue=issue,
                    query=fallback_query,
                )
                return {
                    "next_action": "supplementary_search",
                    "fallback_query": fallback_query,
                    "reflection_count": current_reflection_count + 1,
                    "updated_at": datetime.now().isoformat(),
                }
    
    # ========== 非信息缺失问题 → LLM 改写 ==========
    llm = get_llm()
    
    prompt = REFLECT_PROMPT.format(
        current_itinerary=json.dumps(travel_plan.get("itinerary", []), ensure_ascii=False, indent=2),
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
        
        try:
            improved_itinerary = json.loads(content)
        except json.JSONDecodeError:
            logger.warning("Standard JSON parse failed, trying json_repair")
            try:
                import json_repair
                improved_itinerary = json_repair.repair_json(content, return_objects=True)
            except ImportError:
                logger.error("json_repair not installed, cannot recover")
                raise
            except Exception as e:
                logger.error("json_repair failed", error=str(e))
                raise
        
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
            
    except Exception as e:
        logger.error("Reflection failed", error=str(e))
    
    # 反思后重新进入路线增强（闭环）
    return {
        "travel_plan": travel_plan,
        "reflection_count": current_reflection_count + 1,  # 顶层 state 字段，确保持久化
        "route_enriched": False,
        "next_action": "route_enrich",
        "updated_at": datetime.now().isoformat(),
    }


__all__ = ["reflect_node"]

"""
意图理解节点

分析用户消息，识别任务类型和提取关键信息
"""

import json
import re
from datetime import datetime
from typing import Any

import structlog
from langchain_core.messages import HumanMessage

from src.graphs.state import AgentState, PlanningPhase, TaskType
from src.graphs.nodes.base import INTENT_CLASSIFICATION_PROMPT
from src.llm import Message
from src.llm.qwen import get_llm

logger = structlog.get_logger()


async def understand_intent_node(state: AgentState) -> dict[str, Any]:
    """
    意图理解节点

    分析用户消息，识别任务类型和提取关键信息
    """
    logger.info("Node: understand_intent")

    # 获取最新的用户消息
    user_message = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            user_message = msg.content
            break

    if not user_message:
        return {"next_action": "respond"}

    # 调用 LLM 进行意图分类
    llm = get_llm()
    prompt = INTENT_CLASSIFICATION_PROMPT.format(user_message=user_message)

    response = await llm.chat([
        Message(role="system", content="你是一个意图分类助手，只返回JSON格式。"),
        Message(role="user", content=prompt),
    ])

    # 解析分类结果
    try:
        content = response.content.strip()
        logger.info("LLM intent raw response", content=content[:500])
        
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        result = json.loads(content.strip())
        logger.info("Parsed intent result", result=result)
    except json.JSONDecodeError as e:
        logger.warning("Failed to parse intent classification", error=str(e), response=response.content)
        result = {"task_type": TaskType.GENERAL_CHAT.value, "extracted_info": {}}
    
    # 验证 task_type 是否有效
    valid_task_types = [t.value for t in TaskType]
    raw_task_type = result.get("task_type", "")
    
    if raw_task_type not in valid_task_types:
        logger.warning("Invalid task_type from LLM", raw_task_type=raw_task_type)
        raw_task_type = TaskType.GENERAL_CHAT.value
    
    # 如果被分类为 general_chat 但消息明显是旅游规划，使用关键词匹配覆盖
    if raw_task_type == TaskType.GENERAL_CHAT.value:
        # 检测重新生成
        frontend_regenerate = state.get("regenerate", False)
        frontend_previous_itinerary = state.get("previous_itinerary")
        has_frontend_context = frontend_regenerate and frontend_previous_itinerary
        
        regenerate_keywords = ["重新生成", "再来一次", "换一个版本", "重新规划", "再生成", "换个方案"]
        existing_preference = state.get("travel_preference") or {}
        has_existing_trip = bool(existing_preference.get("destination"))
        has_keyword = any(kw in user_message for kw in regenerate_keywords)
        
        if has_frontend_context:
            logger.info("Frontend regeneration context detected", 
                       previous_days=len(frontend_previous_itinerary),
                       user_message=user_message[:100])
            raw_task_type = TaskType.TRAVEL_PLANNING.value
            result["task_type"] = raw_task_type
            
            if frontend_previous_itinerary:
                first_day = frontend_previous_itinerary[0] if frontend_previous_itinerary else {}
                day_title = first_day.get("title", "")
                for city in ["北京", "上海", "广州", "深圳", "杭州", "成都", "重庆", "西安", "南京", "苏州", "三亚", "厦门", "青岛", "大理", "丽江", "香格里拉", "西双版纳", "桂林", "张家界", "黄山", "林芝", "甘孜"]:
                    if city in day_title:
                        if "extracted_info" not in result:
                            result["extracted_info"] = {}
                        result["extracted_info"]["destination"] = city
                        result["extracted_info"]["days"] = len(frontend_previous_itinerary)
                        logger.info("Extracted destination from previous itinerary", destination=city, days=len(frontend_previous_itinerary))
                        break
        elif has_existing_trip and has_keyword:
            logger.info("Context-aware regeneration detected from session", 
                       destination=existing_preference.get("destination"),
                       user_message=user_message[:100])
            raw_task_type = TaskType.TRAVEL_PLANNING.value
            result["task_type"] = raw_task_type
        
        # 常规关键词匹配
        elif any(kw in user_message for kw in ["规划", "旅游", "游玩", "行程", "攻略", "去哪", "玩", "天游", "自由行", "亲子游", "情侣游", "天", "晚"]):
            logger.info("Overriding to travel_planning via keyword matching", user_message=user_message[:100])
            raw_task_type = TaskType.TRAVEL_PLANNING.value
            cities = ["北京", "上海", "广州", "深圳", "杭州", "成都", "重庆", "西安", "南京", "苏州", "三亚", "厦门", "青岛", "大理", "丽江", "香格里拉", "西双版纳", "桂林", "张家界", "黄山", "林芝", "甘孜"]
            extracted = result.get("extracted_info", {})
            if not extracted.get("destination"):
                for city in cities:
                    if city in user_message:
                        extracted["destination"] = city
                        break
            if not extracted.get("dates"):
                days_match = re.search(r"(\d+)\s*[天日]", user_message)
                if days_match:
                    extracted["dates"] = f"{days_match.group(1)}天"
            if not extracted.get("travel_style"):
                if "亲子" in user_message:
                    extracted["travel_style"] = "亲子游"
                elif "情侣" in user_message:
                    extracted["travel_style"] = "情侣游"
            result["extracted_info"] = extracted
            result["task_type"] = raw_task_type

    task_type = result.get("task_type", TaskType.GENERAL_CHAT.value)
    extracted_info = result.get("extracted_info", {})

    # 更新状态
    updates: dict[str, Any] = {
        "task_type": task_type,
        "updated_at": datetime.now().isoformat(),
    }

    # 根据任务类型初始化偏好
    if task_type == TaskType.TRAVEL_PLANNING.value:
        travel_pref = state.get("travel_preference") or {}
        
        # 中途改口检测
        old_destination = travel_pref.get("destination")
        new_destination = extracted_info.get("destination")
        
        if old_destination and new_destination and old_destination != new_destination:
            logger.info(
                "Destination changed (mid-conversation correction detected)",
                old=old_destination,
                new=new_destination,
            )
            updates["collected_pois"] = []
            updates["search_results"] = []
            updates["weather_info"] = None
            updates["travel_plan"] = None
            
            preserved_dates = travel_pref.get("dates_raw")
            preserved_days = travel_pref.get("days")
            preserved_style = travel_pref.get("travel_style")
            preserved_budget = travel_pref.get("budget")
            
            travel_pref = {}
            
            if preserved_dates:
                travel_pref["dates_raw"] = preserved_dates
            if preserved_days:
                travel_pref["days"] = preserved_days
            if preserved_style:
                travel_pref["travel_style"] = preserved_style
            if preserved_budget:
                travel_pref["budget"] = preserved_budget
                
            logger.info("Preserved travel preferences during destination change",
                       dates_raw=preserved_dates, days=preserved_days, style=preserved_style)
        
        if extracted_info.get("destination"):
            travel_pref["destination"] = extracted_info["destination"]
        if extracted_info.get("dates"):
            travel_pref["dates_raw"] = extracted_info["dates"]
        if extracted_info.get("budget"):
            travel_pref["budget"] = extracted_info["budget"]
        if extracted_info.get("travel_style"):
            travel_pref["travel_style"] = extracted_info["travel_style"]
        if extracted_info.get("must_visit_places"):
            travel_pref["must_visit_places"] = extracted_info["must_visit_places"]
        updates["travel_preference"] = travel_pref
        updates["planning_phase"] = PlanningPhase.UNDERSTAND.value

    elif task_type == TaskType.RENTAL_SEARCH.value:
        rental_pref = state.get("rental_preference") or {}
        if extracted_info.get("destination"):
            rental_pref["city"] = extracted_info["destination"]
        updates["rental_preference"] = rental_pref

    # 决定下一步动作
    if task_type in [TaskType.TRAVEL_PLANNING.value, TaskType.RENTAL_SEARCH.value]:
        updates["next_action"] = "research"
    else:
        updates["next_action"] = "respond"

    logger.info("Intent understood", task_type=task_type, next_action=updates["next_action"])
    return updates

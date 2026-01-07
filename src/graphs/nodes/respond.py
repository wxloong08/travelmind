"""
响应生成节点

生成最终回复给用户
"""

import json
from datetime import datetime
from typing import Any

import structlog

from src.graphs.state import AgentState, PlanningPhase, TaskType
from src.llm import Message
from src.llm.qwen import get_llm

logger = structlog.get_logger()


async def respond_node(state: AgentState) -> dict[str, Any]:
    """
    响应生成节点

    生成最终回复给用户
    """
    logger.info("Node: respond")

    # 如果有旅游计划，直接返回
    travel_plan = state.get("travel_plan")
    if travel_plan:
        logger.info("Returning existing travel plan")
        return {
            "should_end": True,
            "planning_phase": PlanningPhase.COMPLETE.value,
        }

    # 否则生成通用回复
    llm = get_llm()
    
    messages = state.get("messages", [])
    user_message = ""
    for msg in reversed(messages):
        if hasattr(msg, "content"):
            user_message = msg.content
            break

    task_type = state.get("task_type", TaskType.GENERAL_CHAT.value)
    
    # 构建天气信息摘要
    weather_summary = ""
    if state.get("weather_info"):
        weather = state["weather_info"]
        weather_summary = f"\n当前天气：{weather.get('weather', '未知')}，{weather.get('temperature', '--')}°C"

    system_prompt = f"""你是 TravelMind，一个专业的旅游规划助手。
任务类型：{task_type}
{weather_summary}

请友好地回复用户的问题。如果用户想规划旅行，请引导他们提供更多信息（目的地、天数等）。"""

    try:
        response = await llm.chat([
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_message),
        ])
        
        chat_response = response.content
    except Exception as e:
        logger.error("Failed to generate response", error=str(e))
        chat_response = "抱歉，出了点问题，请重试。"

    return {
        "travel_plan": {"chat_response": chat_response},
        "should_end": True,
        "updated_at": datetime.now().isoformat(),
    }

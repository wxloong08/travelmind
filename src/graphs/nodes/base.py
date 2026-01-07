"""
节点基础模块

公共类型定义、路由函数和共享工具
"""

import json
import re
from datetime import datetime
from typing import Any

import structlog

from src.graphs.state import AgentState, PlanningPhase, TaskType
from src.llm import Message
from src.llm.qwen import get_llm

logger = structlog.get_logger()


# ============================================================
# 路由函数
# ============================================================


def route_after_understand(state: AgentState) -> str:
    """意图理解后的路由"""
    return state.get("next_action", "respond")


def route_after_research(state: AgentState) -> str:
    """研究后的路由"""
    return state.get("next_action", "respond")


def route_after_plan(state: AgentState) -> str:
    """规划后的路由"""
    return state.get("next_action", "respond")


def should_continue(state: AgentState) -> bool:
    """是否继续执行"""
    return not state.get("should_end", False)


# ============================================================
# 通用 Prompt
# ============================================================

SYSTEM_PROMPT = """你是 TravelMind，一个专业的旅游规划助手。

你的能力：
1. 规划中国境内的个性化旅游行程
2. 推荐景点、美食、住宿和交通方式
3. 根据用户偏好（预算、风格、时间）定制行程
4. 使用真实的 POI 数据，确保行程可行

注意事项：
- 所有景点必须从 POI 池中选择，确保有真实坐标
- 同一天的景点距离不超过 50km
- 用中文回复，保持友好专业的语气

## 当前任务类型：{task_type}
## 当前阶段：{phase}
"""

INTENT_CLASSIFICATION_PROMPT = """分析用户消息，判断任务类型并提取关键信息。

用户消息：{user_message}

请返回以下 JSON 格式：
{{
    "task_type": "travel_planning|hotel_search|attraction_info|rental_search|general_chat",
    "confidence": 0.0-1.0,
    "extracted_info": {{
        "destination": "目的地城市",
        "dates_raw": "用户原话中的时间描述（如 4天3晚）",
        "travel_style": "旅行风格（休闲/深度/亲子/情侣等）",
        "budget_level": "预算等级（经济/舒适/豪华）",
        "must_visit": ["必去景点列表"],
        "special_requirements": "特殊要求"
    }},
    "needs_more_info": false,
    "follow_up_question": ""
}}

只返回 JSON，不要其他内容。"""

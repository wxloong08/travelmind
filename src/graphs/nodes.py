"""
LangGraph 节点实现

定义工作流中的各个处理节点
"""

import json
from datetime import datetime
from typing import Any

import structlog
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from src.graphs.state import AgentState, PlanningPhase, TaskType
from src.llm import Message, get_llm
from src.tools import ALL_TOOLS, get_tool_definitions

logger = structlog.get_logger()


# ============================================================
# 系统提示词
# ============================================================

SYSTEM_PROMPT = """你是 TravelMind，一个专业的旅游规划与租房助手。

## 你的能力：
1. **旅游规划**：根据用户的目的地、时间、预算等，制定详细的旅游攻略
2. **景点推荐**：搜索并推荐目的地的景点、餐厅、酒店
3. **行程安排**：合理安排每日行程，考虑景点距离和游览时间
4. **租房咨询**：提供长租房信息搜索和建议（6个月以上）

## 工作原则：
- 主动询问关键信息（目的地、时间、预算、人数、偏好）
- 使用工具获取实时数据，不编造信息
- 给出具体、可执行的建议
- 考虑实际情况（天气、交通、开放时间）
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
        "destination": "目的地城市（如：北京、杭州）",
        "dates": "日期/天数信息（如：4天3晚、下周末）",
        "budget": "预算信息（如：5000元、中等预算）",
        "travel_style": "旅行风格（如：亲子游、情侣游、自由行）",
        "must_visit_places": ["用户特别想去的地点列表，如：环球影城、故宫、长城"],
        "other": "其他关键需求"
    }}
}}

注意：
1. must_visit_places 是一个数组，提取用户明确提到想去的具体景点/地点
2. 如果用户说"想去环球影城"，则 must_visit_places = ["环球影城"]
3. 如果用户没有提到具体地点，则 must_visit_places = []

只返回 JSON，不要其他内容。"""


# ============================================================
# 节点函数
# ============================================================


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
        # 清理可能的 markdown 格式
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        result = json.loads(content)
    except json.JSONDecodeError:
        logger.warning("Failed to parse intent classification", response=response.content)
        result = {"task_type": TaskType.GENERAL_CHAT.value}

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


async def research_node(state: AgentState) -> dict[str, Any]:
    """
    信息收集节点

    使用工具搜索相关信息
    """
    logger.info("Node: research", task_type=state.get("task_type"))

    task_type = state.get("task_type")
    updates: dict[str, Any] = {
        "updated_at": datetime.now().isoformat(),
    }

    llm = get_llm()
    tool_definitions = get_tool_definitions()

    # 构建上下文
    context_parts = []
    if state.get("travel_preference"):
        context_parts.append(f"用户旅游偏好: {json.dumps(state['travel_preference'], ensure_ascii=False)}")
    if state.get("rental_preference"):
        context_parts.append(f"用户租房偏好: {json.dumps(state['rental_preference'], ensure_ascii=False)}")

    context = "\n".join(context_parts) if context_parts else "暂无用户偏好信息"

    # 根据任务类型决定搜索策略
    if task_type == TaskType.TRAVEL_PLANNING.value:
        destination = (state.get("travel_preference") or {}).get("destination", "")
        if destination:
            research_prompt = f"""基于用户偏好，请搜索以下信息：
1. {destination}的热门景点
2. {destination}的天气情况
3. {destination}的旅游攻略和建议

用户偏好：
{context}

请使用工具获取真实数据。"""
        else:
            research_prompt = "用户还没有明确目的地，请先回复询问用户想去哪里旅游。"
            updates["next_action"] = "respond"
            return updates

    elif task_type == TaskType.RENTAL_SEARCH.value:
        city = (state.get("rental_preference") or {}).get("city", "")
        if city:
            research_prompt = f"""搜索{city}的租房相关信息，包括：
1. 热门租房区域
2. 租金价格水平
3. 租房注意事项

用户偏好：
{context}"""
        else:
            updates["next_action"] = "respond"
            return updates
    else:
        updates["next_action"] = "respond"
        return updates

    # 调用 LLM 决定使用哪些工具
    messages = [
        Message(
            role="system",
            content=SYSTEM_PROMPT.format(
                task_type=task_type,
                phase=state.get("planning_phase", "research")
            )
        ),
        Message(role="user", content=research_prompt),
    ]

    response = await llm.chat(messages, tools=tool_definitions)

    # 处理工具调用
    if response.tool_calls:
        tool_results = []
        collected_pois = list(state.get("collected_pois") or [])
        weather_info = state.get("weather_info")
        search_results = list(state.get("search_results") or [])

        for tool_call in response.tool_calls:
            logger.info("Executing tool", tool_name=tool_call.name, args=tool_call.arguments)

            # 查找并执行工具
            tool_func = None
            for t in ALL_TOOLS:
                if t.name == tool_call.name:
                    tool_func = t
                    break

            if tool_func:
                try:
                    result = await tool_func.ainvoke(tool_call.arguments)
                    tool_results.append({
                        "tool": tool_call.name,
                        "result": result,
                    })

                    # 根据工具类型存储结果
                    if tool_call.name in ["search_poi", "search_nearby"]:
                        collected_pois.extend(result.get("results", []))
                    elif tool_call.name == "get_weather":
                        weather_info = result
                    elif tool_call.name in ["web_search", "news_search"]:
                        search_results.extend(result.get("results", []))

                except Exception as e:
                    logger.error("Tool execution failed", tool=tool_call.name, error=str(e))
                    tool_results.append({
                        "tool": tool_call.name,
                        "error": str(e),
                    })

        updates["tool_results"] = tool_results
        updates["collected_pois"] = collected_pois
        updates["weather_info"] = weather_info
        updates["search_results"] = search_results

    updates["planning_phase"] = PlanningPhase.PLANNING.value
    updates["next_action"] = "plan"

    return updates


async def planning_node(state: AgentState) -> dict[str, Any]:
    """
    行程规划节点

    基于收集的信息生成结构化的旅游计划 JSON
    """
    logger.info("Node: planning")

    task_type = state.get("task_type")
    if task_type != TaskType.TRAVEL_PLANNING.value:
        return {"next_action": "respond"}

    llm = get_llm()  # 使用默认的 qwen-max 模型

    # 整理收集的信息
    collected_pois = state.get("collected_pois", [])[:20]
    weather_info = state.get("weather_info")
    search_results = state.get("search_results", [])[:10]

    travel_pref = state.get("travel_preference") or {}
    destination = travel_pref.get("destination", "未知目的地")
    travel_style = travel_pref.get("travel_style", "自由行")
    must_visit_places = travel_pref.get("must_visit_places", [])
    
    # 估算天数（默认3天）
    days_raw = travel_pref.get("dates_raw", "")
    days = 3
    if "天" in days_raw:
        import re
        match = re.search(r"(\d+)\s*天", days_raw)
        if match:
            days = int(match.group(1))
    elif "晚" in days_raw:
        import re
        match = re.search(r"(\d+)\s*晚", days_raw)
        if match:
            days = int(match.group(1)) + 1

    # ===== 新增：使用博查搜索真实攻略 =====
    guide_context = ""
    try:
        from src.tools import web_search
        guide_result = await web_search.ainvoke({
            "query": f"{destination} {days}天旅游攻略 行程推荐 必去景点",
            "count": 5,
        })
        if guide_result.get("results"):
            guide_snippets = [
                f"- {r.get('title', '')}: {r.get('snippet', '')[:150]}"
                for r in guide_result.get("results", [])[:3]
            ]
            guide_context = "\n".join(guide_snippets)
            logger.info("Fetched travel guides", destination=destination, count=len(guide_snippets))
    except Exception as e:
        logger.warning("Failed to fetch travel guides", error=str(e))

    # ===== 新增：使用高德搜索真实酒店 =====
    real_hotels = []
    try:
        from src.tools import search_poi
        hotels_result = await search_poi.ainvoke({
            "keywords": "酒店",
            "city": destination,
            "poi_type": "hotel",
            "page_size": 5,
        })
        for h in hotels_result.get("results", [])[:5]:
            real_hotels.append({
                "name": h.get("name", "酒店"),
                "price": f"¥{int(h.get('cost') or 300)}起",
                "rating": h.get("rating") or 4.5,
                "tags": h.get("type", "酒店").split(";")[:2] or ["热门"],
                "image": h.get("photos", [None])[0],  # 高德真实图片
                "address": h.get("address", ""),
            })
        logger.info("Fetched real hotels", destination=destination, count=len(real_hotels))
    except Exception as e:
        logger.warning("Failed to fetch real hotels", error=str(e))

    # 构建 POI 摘要
    poi_summary = []
    for p in collected_pois[:10]:
        poi_summary.append({
            "name": p.get("name", ""),
            "type": p.get("type", ""),
            "address": p.get("address", ""),
        })

    # 构建必去地点的强调文本
    must_visit_text = ""
    if must_visit_places:
        must_visit_text = f"""
## ⭐ 用户必去地点（必须纳入行程！）
{json.dumps(must_visit_places, ensure_ascii=False)}

**重要**：以上是用户明确提出想去的地点，必须安排在行程中，并作为核心亮点！"""

    planning_prompt = f"""基于收集的信息，为用户制定详细且合理的{days}天{travel_style}行程。

## 目的地
{destination}

## 旅行风格
{travel_style}
{must_visit_text}

## 用户其他偏好
{json.dumps({k: v for k, v in travel_pref.items() if k not in ['destination', 'travel_style', 'must_visit_places']}, ensure_ascii=False, indent=2)}

## 收集的景点信息
{json.dumps(poi_summary, ensure_ascii=False, indent=2)}

## 天气信息
{json.dumps(weather_info, ensure_ascii=False, indent=2) if weather_info else "暂无天气信息"}

## 网络搜索的真实攻略（重要参考！）
{guide_context if guide_context else "暂无攻略信息"}

请返回纯 JSON 格式（不要 markdown 代码块），结构如下：
{{
    "chat_response": "一段友好的回复（200-300字），要点：1. 根据用户需求做的假设（如默认日期、预算等）2. 重点介绍如何安排用户特别想去的{', '.join(must_visit_places) if must_visit_places else '景点'} 3. 行程亮点和特色 4. 简要提及交通和时间安排的合理性",
    "itinerary": [
        {{
            "day": 1,
            "title": "主题标题（如：抵达与中轴线探索）",
            "activities": [
                {{
                    "time": "09:00",
                    "title": "活动名称（如：天安门广场）",
                    "type": "attraction",
                    "desc": "简短描述，30-50字，可包含交通方式"
                }}
            ]
        }}
    ],
    "recommended_hotels": []
}}

## ⚠️ 重要规划原则（必须遵守！）：

### 时间安排逻辑
1. **抵达当天**：如果是第一天抵达，应先安排入住酒店后再游玩，或只安排轻松的活动
2. **全天景点**：主题公园（如环球影城、迪士尼）需要全天时间（09:00-18:00），当天不要安排其他主要景点
3. **酒店入住**：统一安排在傍晚 18:00-20:00 左右，不要放在当天最末
4. **每天景点数**：2-3 个主要景点为宜，不要安排过多导致走马观花

### 特定活动时间（非常重要！）
5. **日落/夕阳观景点**：必须安排在傍晚 17:00-19:00，绝对不能安排在早上！
6. **日出观赏**：必须安排在清晨 05:00-07:00
7. **夜景/灯光秀**：必须安排在晚上 19:00-22:00
8. **早市/早餐体验**：安排在早上 07:00-09:00

### 行程合理性
9. **用户必去地点优先**：{', '.join(must_visit_places) if must_visit_places else '无特殊要求'} 必须安排在行程中！
10. **地理位置优化**：同一天的景点应该在同一区域，避免来回折腾
11. **交通时间**：活动之间预留 30-60 分钟交通时间
12. **用餐时间**：12:00 左右午餐，18:00 左右晚餐

### 类型限制
13. **type 类型**：只能是 attraction（景点）、food（餐饮）、hotel（住宿）、transport（交通）

只返回纯 JSON，不要任何其他文字。"""

    messages = [
        Message(
            role="system",
            content="你是专业的旅游规划师。严格按照用户要求的 JSON 格式输出，不要添加任何额外文字或 markdown 格式。"
        ),
        Message(role="user", content=planning_prompt),
    ]

    response = await llm.chat(messages)

    # 解析结构化响应
    structured_plan = None
    try:
        content = response.content.strip()
        # 清理可能的 markdown 格式
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        structured_plan = json.loads(content)
    except json.JSONDecodeError as e:
        logger.warning("Failed to parse structured plan, falling back to text", error=str(e))
        structured_plan = None

    # 构建旅游计划
    travel_plan = {
        "destination": destination,
        "generated_at": datetime.now().isoformat(),
        "based_on": {
            "poi_count": len(collected_pois),
            "has_weather": bool(weather_info),
            "search_count": len(search_results),
        },
    }

    if structured_plan:
        travel_plan["structured"] = True
        travel_plan["chat_response"] = structured_plan.get("chat_response", "")
        travel_plan["itinerary"] = structured_plan.get("itinerary", [])
        # 优先使用真实酒店数据，若无则使用 LLM 生成的
        travel_plan["recommended_hotels"] = real_hotels if real_hotels else structured_plan.get("recommended_hotels", [])
        travel_plan["content"] = structured_plan.get("chat_response", "")
    else:
        travel_plan["structured"] = False
        travel_plan["content"] = response.content
        # 即使 LLM 无法结构化输出，也使用真实酒店
        travel_plan["recommended_hotels"] = real_hotels

    return {
        "travel_plan": travel_plan,
        "planning_phase": PlanningPhase.COMPLETE.value,
        "next_action": "respond",
        "updated_at": datetime.now().isoformat(),
    }


async def respond_node(state: AgentState) -> dict[str, Any]:
    """
    响应生成节点

    生成最终回复给用户
    如果已有结构化的旅游计划，直接使用其 chat_response
    """
    logger.info("Node: respond")

    task_type = state.get("task_type", TaskType.GENERAL_CHAT.value)
    phase = state.get("planning_phase", PlanningPhase.INIT.value)
    
    # 如果有结构化的旅游计划，直接使用 chat_response
    travel_plan = state.get("travel_plan")
    if travel_plan and travel_plan.get("structured") and travel_plan.get("chat_response"):
        logger.info("Using structured chat_response from planning")
        return {
            "messages": [AIMessage(content=travel_plan["chat_response"])],
            "updated_at": datetime.now().isoformat(),
            "should_end": True,
        }

    # 否则，调用 LLM 生成响应
    llm = get_llm()

    # 构建上下文
    context_parts = []

    if travel_plan:
        context_parts.append(f"## 已生成的旅游计划\n{travel_plan.get('content', '')}")

    if state.get("collected_pois"):
        poi_summary = "\n".join([
            f"- {p['name']}: {p.get('address', '无地址')} (评分: {p.get('rating', '无')})"
            for p in state["collected_pois"][:5]
        ])
        context_parts.append(f"## 找到的地点\n{poi_summary}")

    if state.get("weather_info"):
        weather = state["weather_info"]
        context_parts.append(
            f"## 天气信息\n{weather.get('city', '')}: {weather.get('weather', '')} "
            f"{weather.get('temperature', '')}°C"
        )

    if state.get("tool_results"):
        context_parts.append("## 工具调用结果已整合到上述信息中")

    context = "\n\n".join(context_parts) if context_parts else ""

    # 转换消息格式
    messages = [
        Message(
            role="system",
            content=SYSTEM_PROMPT.format(task_type=task_type, phase=phase)
            + (f"\n\n## 当前上下文\n{context}" if context else "")
        ),
    ]

    for msg in state["messages"]:
        if isinstance(msg, HumanMessage):
            messages.append(Message(role="user", content=msg.content))
        elif isinstance(msg, AIMessage):
            messages.append(Message(role="assistant", content=msg.content))

    response = await llm.chat(messages)

    # 返回 AI 消息
    return {
        "messages": [AIMessage(content=response.content)],
        "updated_at": datetime.now().isoformat(),
        "should_end": True,
    }


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

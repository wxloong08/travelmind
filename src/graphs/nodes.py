"""
LangGraph 节点实现

定义工作流中的各个处理节点
增强版：多轮精准搜索 + 完整攻略抓取
"""

import json
import re
from datetime import datetime
from typing import Any

import structlog
from langchain_core.messages import AIMessage, HumanMessage

from src.graphs.state import AgentState, PlanningPhase, TaskType
from src.llm import Message, get_llm

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
# 工具函数
# ============================================================

async def _search_web(query: str, count: int = 5) -> list[dict]:
    """调用博查搜索"""
    try:
        from src.tools import web_search
        result = await web_search.ainvoke({"query": query, "count": count})
        return result.get("results", [])
    except Exception as e:
        logger.warning("Web search failed", query=query, error=str(e))
        return []


async def _fetch_page_content(url: str, max_length: int = 8000) -> str:
    """抓取网页完整内容"""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
            
            # 简单提取文本内容
            from html import unescape
            
            html = response.text
            # 移除 script 和 style
            html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
            html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
            # 移除 HTML 标签
            text = re.sub(r'<[^>]+>', ' ', html)
            # 清理空白
            text = re.sub(r'\s+', ' ', text).strip()
            text = unescape(text)
            
            return text[:max_length]
    except Exception as e:
        logger.warning("Page fetch failed", url=url, error=str(e))
        return ""


async def _search_and_fetch_guides(
    destination: str,
    days: int,
    travel_style: str,
    must_visit_places: list[str],
) -> dict[str, Any]:
    """
    多轮精准搜索 + 完整攻略抓取
    
    返回结构化的攻略信息
    """
    logger.info("Starting multi-round guide search", 
                destination=destination, days=days, style=travel_style)
    
    guides = {
        "general_guides": [],      # 通用行程攻略
        "place_guides": [],        # 特定景点攻略
        "food_guides": [],         # 美食推荐
        "accommodation_tips": [],  # 住宿建议
        "full_content": [],        # 完整抓取的内容
    }
    
    # ========== 第一轮：通用行程攻略 ==========
    general_queries = [
        f"{destination} {days}天{days-1}晚 {travel_style} 攻略 行程安排 小红书",
        f"{destination} {travel_style} 旅游攻略 详细行程 知乎 马蜂窝",
    ]
    
    high_quality_urls = []  # 收集高质量链接用于后续抓取
    
    for query in general_queries:
        results = await _search_web(query, count=5)
        for r in results:
            title = r.get("title", "")
            snippet = r.get("snippet", "")
            url = r.get("url", "")
            source = r.get("source", "")
            
            guides["general_guides"].append({
                "title": title,
                "snippet": snippet,
                "url": url,
                "source": source,
            })
            
            # 识别高质量来源
            if any(domain in url for domain in [
                "zhihu.com", "mafengwo.cn", "xiaohongshu.com", 
                "ctrip.com", "you.ctrip.com", "travel.qunar.com"
            ]):
                high_quality_urls.append(url)
    
    logger.info("General guides collected", count=len(guides["general_guides"]))
    
    # ========== 第二轮：特定景点攻略 ==========
    if must_visit_places:
        for place in must_visit_places[:3]:  # 最多搜索3个必去景点
            place_queries = [
                f"{destination} {place} 一日游 攻略 游玩时间",
                f"{place} 怎么玩 多长时间 攻略",
            ]
            
            for query in place_queries:
                results = await _search_web(query, count=3)
                for r in results:
                    guides["place_guides"].append({
                        "place": place,
                        "title": r.get("title", ""),
                        "snippet": r.get("snippet", ""),
                        "url": r.get("url", ""),
                    })
                    
                    url = r.get("url", "")
                    if any(domain in url for domain in ["zhihu.com", "mafengwo.cn", "xiaohongshu.com"]):
                        high_quality_urls.append(url)
        
        logger.info("Place guides collected", places=must_visit_places, count=len(guides["place_guides"]))
    
    # ========== 第三轮：美食推荐 ==========
    food_query = f"{destination} {travel_style} 美食推荐 必吃 餐厅"
    food_results = await _search_web(food_query, count=3)
    for r in food_results:
        guides["food_guides"].append({
            "title": r.get("title", ""),
            "snippet": r.get("snippet", ""),
        })
    
    # ========== 第四轮：住宿区域建议 ==========
    accommodation_query = f"{destination} 住宿推荐 住哪个区域方便 {travel_style}"
    acc_results = await _search_web(accommodation_query, count=3)
    for r in acc_results:
        guides["accommodation_tips"].append({
            "title": r.get("title", ""),
            "snippet": r.get("snippet", ""),
        })
    
    # ========== 抓取完整攻略内容 ==========
    # 去重并限制数量
    unique_urls = list(dict.fromkeys(high_quality_urls))[:3]
    
    for url in unique_urls:
        logger.info("Fetching full guide content", url=url)
        content = await _fetch_page_content(url, max_length=6000)
        if content and len(content) > 500:
            guides["full_content"].append({
                "url": url,
                "content": content,
            })
    
    logger.info("Full content fetched", count=len(guides["full_content"]))
    
    return guides


def _build_guide_context(guides: dict[str, Any]) -> str:
    """将搜索结果构建为 LLM 可用的上下文"""
    
    context_parts = []
    
    # 完整攻略内容（最重要）
    if guides.get("full_content"):
        context_parts.append("### 📚 真实攻略详情（请重点参考！）\n")
        for i, item in enumerate(guides["full_content"][:2], 1):
            content = item.get("content", "")[:4000]  # 限制长度
            context_parts.append(f"**攻略 {i}**:\n{content}\n")
    
    # 通用攻略摘要
    if guides.get("general_guides"):
        context_parts.append("\n### 🗺️ 行程参考摘要\n")
        for g in guides["general_guides"][:5]:
            title = g.get("title", "")
            snippet = g.get("snippet", "")
            context_parts.append(f"- **{title}**: {snippet[:200]}\n")
    
    # 特定景点攻略
    if guides.get("place_guides"):
        context_parts.append("\n### 🎯 特定景点攻略\n")
        for g in guides["place_guides"][:5]:
            place = g.get("place", "")
            snippet = g.get("snippet", "")
            context_parts.append(f"- **{place}**: {snippet[:150]}\n")
    
    # 美食推荐
    if guides.get("food_guides"):
        context_parts.append("\n### 🍜 美食推荐\n")
        for g in guides["food_guides"][:3]:
            context_parts.append(f"- {g.get('snippet', '')[:150]}\n")
    
    # 住宿建议
    if guides.get("accommodation_tips"):
        context_parts.append("\n### 🏨 住宿区域建议\n")
        for g in guides["accommodation_tips"][:3]:
            context_parts.append(f"- {g.get('snippet', '')[:150]}\n")
    
    return "".join(context_parts)


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

    执行多轮精准搜索，收集真实 UGC 攻略
    """
    logger.info("Node: research", task_type=state.get("task_type"))

    task_type = state.get("task_type")
    updates: dict[str, Any] = {
        "updated_at": datetime.now().isoformat(),
    }

    if task_type != TaskType.TRAVEL_PLANNING.value:
        updates["next_action"] = "respond"
        return updates

    travel_pref = state.get("travel_preference") or {}
    destination = travel_pref.get("destination", "")
    
    if not destination:
        updates["next_action"] = "respond"
        return updates

    travel_style = travel_pref.get("travel_style", "自由行")
    must_visit_places = travel_pref.get("must_visit_places", [])
    
    # 估算天数
    days_raw = travel_pref.get("dates_raw", "")
    days = 3
    if "天" in days_raw:
        match = re.search(r"(\d+)\s*天", days_raw)
        if match:
            days = int(match.group(1))
    elif "晚" in days_raw:
        match = re.search(r"(\d+)\s*晚", days_raw)
        if match:
            days = int(match.group(1)) + 1

    # ========== 多轮精准搜索 ==========
    guides = await _search_and_fetch_guides(
        destination=destination,
        days=days,
        travel_style=travel_style,
        must_visit_places=must_visit_places,
    )
    
    # 存储搜索结果
    updates["search_results"] = guides.get("general_guides", []) + guides.get("place_guides", [])
    
    # 存储完整攻略上下文（供 planning_node 使用）
    guide_context = _build_guide_context(guides)
    
    # 将攻略上下文存入 travel_preference
    travel_pref["guide_context"] = guide_context
    travel_pref["days"] = days
    updates["travel_preference"] = travel_pref

    # ========== 获取天气信息 ==========
    try:
        from src.tools import get_weather
        weather_result = await get_weather.ainvoke({"city": destination})
        updates["weather_info"] = weather_result
        logger.info("Weather fetched", city=destination)
    except Exception as e:
        logger.warning("Weather fetch failed", error=str(e))

    # ========== 搜索 POI ==========
    try:
        from src.tools import search_poi
        poi_result = await search_poi.ainvoke({
            "keywords": "景点",
            "city": destination,
            "poi_type": "tourism",
            "page_size": 10,
        })
        updates["collected_pois"] = poi_result.get("results", [])
        logger.info("POIs collected", count=len(updates.get("collected_pois", [])))
    except Exception as e:
        logger.warning("POI search failed", error=str(e))

    updates["planning_phase"] = PlanningPhase.PLANNING.value
    updates["next_action"] = "plan"

    return updates


async def planning_node(state: AgentState) -> dict[str, Any]:
    """
    行程规划节点

    基于真实 UGC 攻略生成结构化的旅游计划
    """
    logger.info("Node: planning")

    task_type = state.get("task_type")
    if task_type != TaskType.TRAVEL_PLANNING.value:
        return {"next_action": "respond"}

    llm = get_llm()

    # 获取收集的信息
    collected_pois = state.get("collected_pois", [])[:15]
    weather_info = state.get("weather_info")
    
    travel_pref = state.get("travel_preference") or {}
    destination = travel_pref.get("destination", "未知目的地")
    travel_style = travel_pref.get("travel_style", "自由行")
    must_visit_places = travel_pref.get("must_visit_places", [])
    days = travel_pref.get("days", 3)
    guide_context = travel_pref.get("guide_context", "")

    # ========== 获取真实酒店数据 ==========
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
                "address": h.get("address", ""),
            })
        logger.info("Real hotels fetched", count=len(real_hotels))
    except Exception as e:
        logger.warning("Hotel fetch failed", error=str(e))

    # 构建必去地点强调
    must_visit_text = ""
    if must_visit_places:
        must_visit_text = f"""
## ⭐ 用户必去地点（必须纳入行程！）
{json.dumps(must_visit_places, ensure_ascii=False)}

**重要**：以上是用户明确提出想去的地点，必须安排在行程中，并作为核心亮点！"""

    # ========== 构建规划提示词 ==========
    planning_prompt = f"""你是一个专业的旅行规划师。请基于【真实 UGC 攻略】为用户制定行程。

⚠️ 核心原则：你的规划必须参考下面的真实攻略内容，不要凭空想象！

## 📋 用户需求
- **目的地**: {destination}
- **天数**: {days}天{days-1}晚
- **旅行风格**: {travel_style}
{must_visit_text}

## 🌤️ 天气信息
{json.dumps(weather_info, ensure_ascii=False, indent=2) if weather_info else "暂无"}

## 📚 真实 UGC 攻略（重点参考！！！）
以下是从小红书、知乎、马蜂窝等平台搜索到的真实攻略，请从中提取：
1. 真实可行的景点顺序
2. 合理的时间安排（如故宫需要4小时、环球影城需要全天）
3. 同一区域的景点放在同一天
4. 真实的美食推荐

{guide_context if guide_context else "暂无攻略信息，请根据常识规划"}

## ⏰ 时间安排规则（必须遵守！）
1. **主题公园（环球影城、迪士尼等）**：必须安排全天（09:00-21:00），当天不安排其他主要景点
2. **故宫/颐和园等大型景点**：至少安排半天（4小时）
3. **日落/夕阳观景**：只能在17:00-19:00
4. **夜景/灯光秀**：只能在19:00-22:00
5. **同一天景点**：应在同一区域，避免来回折腾
6. **每天2-3个主要景点**为宜，不要走马观花

## 📍 可参考的景点 POI
{json.dumps([{{"name": p.get("name"), "type": p.get("type"), "address": p.get("address")}} for p in collected_pois[:8]], ensure_ascii=False, indent=2)}

---

请返回纯 JSON 格式（不要 markdown 代码块）：
{{
    "chat_response": "一段友好的回复（200-300字），包含：1. 行程亮点 2. 为什么这样安排 3. 特别提醒",
    "itinerary": [
        {{
            "day": 1,
            "title": "主题标题（如：故宫中轴线深度游）",
            "activities": [
                {{
                    "time": "09:00",
                    "title": "活动名称",
                    "type": "attraction|food|hotel|transport",
                    "desc": "简短描述（30-50字），包含实用信息如门票、交通方式"
                }}
            ]
        }}
    ],
    "recommended_hotels": []
}}

只返回纯 JSON！"""

    messages = [
        Message(
            role="system",
            content="你是专业旅游规划师。严格按照JSON格式输出，基于真实攻略内容规划，不要编造信息。"
        ),
        Message(role="user", content=planning_prompt),
    ]

    response = await llm.chat(messages)

    # 解析结构化响应
    structured_plan = None
    try:
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        structured_plan = json.loads(content)
    except json.JSONDecodeError as e:
        logger.warning("Failed to parse structured plan", error=str(e))
        structured_plan = None

    # 构建旅游计划
    travel_plan = {
        "destination": destination,
        "generated_at": datetime.now().isoformat(),
        "based_on": {
            "poi_count": len(collected_pois),
            "has_weather": bool(weather_info),
            "guide_count": len(state.get("search_results", [])),
            "has_full_guides": bool(guide_context),
        },
    }

    if structured_plan:
        travel_plan["structured"] = True
        travel_plan["chat_response"] = structured_plan.get("chat_response", "")
        travel_plan["itinerary"] = structured_plan.get("itinerary", [])
        travel_plan["recommended_hotels"] = real_hotels if real_hotels else structured_plan.get("recommended_hotels", [])
        travel_plan["content"] = structured_plan.get("chat_response", "")
    else:
        travel_plan["structured"] = False
        travel_plan["content"] = response.content
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

    context_parts = []

    if travel_plan:
        context_parts.append(f"## 已生成的旅游计划\n{travel_plan.get('content', '')}")

    if state.get("collected_pois"):
        poi_summary = "\n".join([
            f"- {p['name']}: {p.get('address', '无地址')}"
            for p in state["collected_pois"][:5]
        ])
        context_parts.append(f"## 找到的地点\n{poi_summary}")

    if state.get("weather_info"):
        weather = state["weather_info"]
        context_parts.append(
            f"## 天气信息\n{weather.get('city', '')}: {weather.get('weather', '')} "
            f"{weather.get('temperature', '')}°C"
        )

    context = "\n\n".join(context_parts) if context_parts else ""

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

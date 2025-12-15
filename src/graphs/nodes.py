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
# 行程时长解析
# ============================================================

def parse_trip_duration(user_input: str) -> dict:
    """
    解析用户输入的行程时长
    
    支持格式：
    - "4天3晚" → 4天游玩 + 1天抵达 = 5天行程，4晚住宿
    - "3天" → 3天游玩 + 1天抵达 = 4天行程，3晚住宿
    - "周末游" → 2天游玩，1晚住宿（当天出发）
    
    Returns:
        {
            "user_days": 4,         # 用户说的天数
            "user_nights": 3,       # 用户说的晚数
            "actual_days": 5,       # 实际行程天数（含抵达日）
            "actual_nights": 4,     # 实际住宿晚数
            "needs_arrival_day": True
        }
    """
    user_input = user_input.strip()
    
    # 匹配 "X天Y晚" 格式
    match = re.search(r'(\d+)\s*天\s*(\d+)\s*晚', user_input)
    if match:
        days = int(match.group(1))
        nights = int(match.group(2))
        return {
            "user_days": days,
            "user_nights": nights,
            "actual_days": days + 1,      # +1 抵达日
            "actual_nights": nights + 1,  # +1 抵达日住宿
            "needs_arrival_day": True,
        }
    
    # 匹配 "X天" 格式
    match = re.search(r'(\d+)\s*天', user_input)
    if match:
        days = int(match.group(1))
        nights = days - 1
        return {
            "user_days": days,
            "user_nights": nights,
            "actual_days": days + 1,
            "actual_nights": days,  # days - 1 + 1 = days
            "needs_arrival_day": True,
        }
    
    # 匹配 "周末" 格式
    if '周末' in user_input:
        return {
            "user_days": 2,
            "user_nights": 1,
            "actual_days": 2,         # 周末不加抵达日（当天早上出发）
            "actual_nights": 1,
            "needs_arrival_day": False,
        }
    
    # 默认 3 天 2 晚
    return {
        "user_days": 3,
        "user_nights": 2,
        "actual_days": 4,
        "actual_nights": 3,
        "needs_arrival_day": True,
    }


# ============================================================
# 工具函数
# ============================================================

async def _search_web(query: str, count: int = 5, destination: str | None = None) -> list[dict]:
    """
    搜索攻略（优先本地 RAG，不足时调用博查 API）
    
    Args:
        query: 搜索查询
        count: 期望结果数量
        destination: 目的地（用于存储和过滤）
    
    Returns:
        搜索结果列表
    """
    try:
        from src.services.knowledge_service import get_knowledge_base
        
        kb = get_knowledge_base()
        results, from_api = await kb.search_with_fallback(
            query=query,
            destination=destination,
            count=count,
            use_api_if_needed=True,
        )
        
        logger.info(
            "Web search completed",
            query=query[:30],
            results=len(results),
            from_api=from_api,
        )
        
        return results
        
    except Exception as e:
        logger.warning("Web search with RAG failed, falling back to direct API", error=str(e))
        
        # 降级：直接调用博查 API
        try:
            from src.tools import web_search
            result = await web_search.ainvoke({"query": query, "count": count})
            if result is None:
                return []
            return result.get("results", [])
        except Exception as e2:
            logger.warning("Direct API search also failed", error=str(e2))
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
    
    优先使用本地 RAG 知识库，不足时调用博查 API 并存储结果
    
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
        results = await _search_web(query, count=5, destination=destination)
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
                "from_cache": r.get("from_cache", False),
            })
            
            # 识别高质量来源（仅对非缓存结果抓取）
            if not r.get("from_cache") and any(domain in url for domain in [
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
                results = await _search_web(query, count=3, destination=destination)
                for r in results:
                    guides["place_guides"].append({
                        "place": place,
                        "title": r.get("title", ""),
                        "snippet": r.get("snippet", ""),
                        "url": r.get("url", ""),
                        "from_cache": r.get("from_cache", False),
                    })
                    
                    url = r.get("url", "")
                    if not r.get("from_cache") and any(domain in url for domain in ["zhihu.com", "mafengwo.cn", "xiaohongshu.com"]):
                        high_quality_urls.append(url)
        
        logger.info("Place guides collected", places=must_visit_places, count=len(guides["place_guides"]))
    
    # ========== 第三轮：美食推荐 ==========
    food_query = f"{destination} {travel_style} 美食推荐 必吃 餐厅"
    food_results = await _search_web(food_query, count=3, destination=destination)
    for r in food_results:
        guides["food_guides"].append({
            "title": r.get("title", ""),
            "snippet": r.get("snippet", ""),
        })
    
    # ========== 第四轮：住宿区域建议 ==========
    accommodation_query = f"{destination} 住宿推荐 住哪个区域方便 {travel_style}"
    acc_results = await _search_web(accommodation_query, count=3, destination=destination)
    for r in acc_results:
        guides["accommodation_tips"].append({
            "title": r.get("title", ""),
            "snippet": r.get("snippet", ""),
        })
    
    # ========== 抓取完整攻略内容 ==========
    # 去重并限制数量
    unique_urls = list(dict.fromkeys(high_quality_urls))[:3]
    
    # 获取知识库用于存储
    try:
        from src.services.knowledge_service import get_knowledge_base
        kb = get_knowledge_base()
    except Exception:
        kb = None
    
    for url in unique_urls:
        logger.info("Fetching full guide content", url=url)
        content = await _fetch_page_content(url, max_length=6000)
        if content and len(content) > 500:
            guides["full_content"].append({
                "url": url,
                "content": content,
            })
            
            # 存储到 RAG 知识库
            if kb:
                try:
                    await kb.store_full_content(
                        url=url,
                        content=content,
                        destination=destination,
                        title=f"{destination}攻略",
                    )
                except Exception as e:
                    logger.warning("Failed to store content to RAG", error=str(e))
    
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
        logger.info("LLM intent raw response", content=content[:500])  # 记录原始响应
        
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        result = json.loads(content.strip())
        logger.info("Parsed intent result", result=result)
    except json.JSONDecodeError as e:
        logger.warning("Failed to parse intent classification", error=str(e), response=response.content)
        result = {"task_type": TaskType.GENERAL_CHAT.value, "extracted_info": {}}
    
    # 验证 task_type 是否有效，如果无效则使用关键词匹配
    valid_task_types = [t.value for t in TaskType]
    raw_task_type = result.get("task_type", "")
    
    if raw_task_type not in valid_task_types:
        logger.warning("Invalid task_type from LLM", raw_task_type=raw_task_type)
        raw_task_type = TaskType.GENERAL_CHAT.value
    
    # 如果被分类为 general_chat 但消息明显是旅游规划，使用关键词匹配覆盖
    if raw_task_type == TaskType.GENERAL_CHAT.value:
        # ========== 方案 B：上下文感知重新生成 ==========
        # 检测方式 1: 前端传入 regenerate=True 和 previous_itinerary
        frontend_regenerate = state.get("regenerate", False)
        frontend_previous_itinerary = state.get("previous_itinerary")
        has_frontend_context = frontend_regenerate and frontend_previous_itinerary
        
        # 检测方式 2: 后端会话状态中有 travel_preference
        regenerate_keywords = ["重新生成", "再来一次", "换一个版本", "重新规划", "再生成", "换个方案"]
        existing_preference = state.get("travel_preference") or {}
        has_existing_trip = bool(existing_preference.get("destination"))
        has_keyword = any(kw in user_message for kw in regenerate_keywords)
        
        if has_frontend_context:
            # 前端传入了重新生成上下文，使用 previous_itinerary 中的信息
            logger.info("Frontend regeneration context detected", 
                       previous_days=len(frontend_previous_itinerary),
                       user_message=user_message[:100])
            raw_task_type = TaskType.TRAVEL_PLANNING.value
            result["task_type"] = raw_task_type
            
            # 从 previous_itinerary 中提取目的地信息，写入 extracted_info
            # 这样后续的逻辑会将其合并到 travel_preference
            if frontend_previous_itinerary:
                first_day = frontend_previous_itinerary[0] if frontend_previous_itinerary else {}
                # 尝试从第一天标题中提取目的地
                day_title = first_day.get("title", "")
                for city in ["北京", "上海", "广州", "深圳", "杭州", "成都", "重庆", "西安", "南京", "苏州", "三亚", "厦门", "青岛", "大理", "丽江", "香格里拉", "西双版纳", "桂林", "张家界", "黄山"]:
                    if city in day_title:
                        # 确保 extracted_info 存在
                        if "extracted_info" not in result:
                            result["extracted_info"] = {}
                        result["extracted_info"]["destination"] = city
                        result["extracted_info"]["days"] = len(frontend_previous_itinerary)
                        logger.info("Extracted destination from previous itinerary", destination=city, days=len(frontend_previous_itinerary))
                        break
        elif has_existing_trip and has_keyword:
            # 后端会话状态有行程信息且用户说了重新生成
            logger.info("Context-aware regeneration detected from session", 
                       destination=existing_preference.get("destination"),
                       user_message=user_message[:100])
            raw_task_type = TaskType.TRAVEL_PLANNING.value
            result["task_type"] = raw_task_type
        # ========== 上下文感知检测结束 ==========
        
        # 常规关键词匹配
        elif any(kw in user_message for kw in ["规划", "旅游", "游玩", "行程", "攻略", "去哪", "玩", "天游", "自由行", "亲子游", "情侣游", "天", "晚"]):
            logger.info("Overriding to travel_planning via keyword matching", user_message=user_message[:100])
            raw_task_type = TaskType.TRAVEL_PLANNING.value
            # 尝试提取目的地
            cities = ["北京", "上海", "广州", "深圳", "杭州", "成都", "重庆", "西安", "南京", "苏州", "三亚", "厦门", "青岛", "大理", "丽江", "香格里拉", "西双版纳", "桂林", "张家界", "黄山"]
            extracted = result.get("extracted_info", {})
            if not extracted.get("destination"):
                for city in cities:
                    if city in user_message:
                        extracted["destination"] = city
                        break
            # 尝试提取天数
            if not extracted.get("dates"):
                days_match = re.search(r"(\d+)\s*[天日]", user_message)
                if days_match:
                    extracted["dates"] = f"{days_match.group(1)}天"
            # 提取旅行风格
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
        
        # ========== 中途改口检测 ==========
        # 检测目的地是否变化，如果变化则清空旧数据
        old_destination = travel_pref.get("destination")
        new_destination = extracted_info.get("destination")
        
        if old_destination and new_destination and old_destination != new_destination:
            logger.info(
                "Destination changed (mid-conversation correction detected)",
                old=old_destination,
                new=new_destination,
            )
            # 清空旧数据，强制重新收集
            updates["collected_pois"] = []          # 清空 POI
            updates["search_results"] = []          # 清空搜索结果
            updates["weather_info"] = None          # 清空天气
            updates["travel_plan"] = None           # 清空已生成的行程
            
            # 保留天数、旅行风格等非目的地相关信息
            preserved_dates = travel_pref.get("dates_raw")
            preserved_days = travel_pref.get("days")
            preserved_style = travel_pref.get("travel_style")
            preserved_budget = travel_pref.get("budget")
            
            # 重置旅行偏好（只清空目的地相关数据）
            travel_pref = {}
            
            # 恢复保留的信息
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
        # ========== 中途改口检测结束 ==========
        
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
    import traceback
    
    logger.info("Node: research", task_type=state.get("task_type"))

    try:
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
        
    except Exception as e:
        # 全局异常处理：确保搜索失败时工作流能继续
        logger.error(
            "research_node failed",
            error=str(e),
            traceback=traceback.format_exc(),
        )
        # 返回安全的默认值，让工作流继续到 respond 节点
        return {
            "next_action": "respond",
            "updated_at": datetime.now().isoformat(),
            "errors": [f"信息收集失败: {str(e)}"],
        }


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

    # ========== 预算等级判断 ==========
    def get_budget_level(user_input: str, travel_style: str) -> tuple[str, int, int]:
        """
        判断住宿预算等级
        
        Returns: (等级名称, 最低价, 最高价)
        """
        user_lower = (user_input or "").lower()
        style_lower = (travel_style or "").lower()
        
        # 经济型关键词
        if any(kw in user_lower or kw in style_lower for kw in ["经济", "省钱", "穷游", "背包", "青旅"]):
            return ("economy", 100, 200)
        # 豪华型关键词
        if any(kw in user_lower or kw in style_lower for kw in ["豪华", "高端", "五星", "奢华", "度假"]):
            return ("luxury", 800, 2000)
        # 舒适型关键词
        if any(kw in user_lower or kw in style_lower for kw in ["舒适", "商务", "品质"]):
            return ("comfortable", 400, 800)
        # 默认中等预算
        return ("moderate", 200, 400)

    user_message = state.get("messages", [])[-1].content if state.get("messages") else ""
    budget_level, min_price, max_price = get_budget_level(user_message, travel_style)
    logger.info("Budget level determined", level=budget_level, min=min_price, max=max_price)
    
    # ========== 解析行程时长（抵达日规则）==========
    trip_duration = parse_trip_duration(user_message)
    user_days = trip_duration["user_days"]
    user_nights = trip_duration["user_nights"]
    actual_days = trip_duration["actual_days"]
    actual_nights = trip_duration["actual_nights"]
    needs_arrival_day = trip_duration["needs_arrival_day"]
    
    logger.info(
        "Trip duration parsed",
        user_request=f"{user_days}天{user_nights}晚",
        actual=f"{actual_days}天{actual_nights}晚",
        needs_arrival_day=needs_arrival_day
    )

    # ========== 从攻略中提取住宿推荐 ==========
    guide_hotels = []
    if guide_context:
        import re
        
        # 住宿提取正则模式
        hotel_patterns = [
            r"住在[了的]?(.{2,15}(?:酒店|民宿|客栈|旅馆|公寓|青旅|驿站))",
            r"推荐(.{2,15}(?:酒店|民宿|客栈|旅馆|公寓|青旅))",
            r"入住[了的]?(.{2,15}(?:酒店|民宿|客栈|旅馆))",
            r"住宿[：:]\s*(.{2,20})",
            r"酒店推荐[：:]\s*(.{2,20})",
            r"(?:选择|预订)[了的]?(.{2,15}(?:酒店|民宿|客栈))",
        ]
        
        hotel_mentions = []
        for pattern in hotel_patterns:
            matches = re.findall(pattern, guide_context)
            hotel_mentions.extend(matches)
        
        # 去重
        unique_hotels = list(set(h.strip() for h in hotel_mentions if h.strip()))
        logger.info("Hotels extracted from guides", count=len(unique_hotels), names=unique_hotels[:3])
        
        # 通过 POI 搜索验证并获取详细信息
        if unique_hotels:
            from src.tools import search_poi
            
            for hotel_name in unique_hotels[:2]:  # 最多验证2个，减少 API 调用
                try:
                    import asyncio
                    await asyncio.sleep(0.5)  # API 限流
                    
                    result = await search_poi.ainvoke({
                        "keywords": hotel_name,
                        "city": destination,
                        "poi_type": "hotel",
                        "page_size": 1,
                    })
                    
                    if result and result.get("results"):
                        h = result["results"][0]
                        poi_cost = h.get("cost")
                        estimated_price = int(poi_cost) if poi_cost else (min_price + max_price) // 2
                        
                        guide_hotels.append({
                            "name": h.get("name", hotel_name),
                            "price": f"¥{estimated_price}起",
                            "price_num": estimated_price,
                            "rating": h.get("rating") or 4.5,
                            "tags": ["攻略推荐"] + (h.get("type", "酒店").split(";")[:1] or []),
                            "address": h.get("address", ""),
                            "location": h.get("location"),
                            "source": "guide",  # 标记来源
                        })
                except Exception as e:
                    logger.warning(f"Failed to verify guide hotel: {hotel_name}, error: {e}")
        
        logger.info("Guide hotels verified", count=len(guide_hotels))

    # ========== 获取真实酒店数据（按预算筛选）==========
    real_hotels = []
    
    # 优先使用攻略推荐的酒店
    if guide_hotels:
        real_hotels.extend(guide_hotels)
    
    try:
        from src.tools import search_poi
        
        # 根据预算等级选择搜索关键词
        hotel_keywords = {
            "economy": "如家 汉庭 7天 快捷酒店",
            "moderate": "全季 亚朵 维也纳 酒店",
            "comfortable": "希尔顿 万豪 洲际 酒店",
            "luxury": "四季 半岛 安缦 丽思卡尔顿",
        }
        
        import asyncio
        await asyncio.sleep(0.5)  # API 限流
        
        hotels_result = await search_poi.ainvoke({
            "keywords": hotel_keywords.get(budget_level, "酒店"),
            "city": destination,
            "poi_type": "hotel",
            "page_size": 6,  # 减少请求数量
        })
        
        for h in hotels_result.get("results", [])[:6]:
            # 估算价格（高德 POI 可能没有价格，根据类型估算）
            poi_cost = h.get("cost")
            if poi_cost:
                estimated_price = int(poi_cost)
            else:
                # 根据酒店名称估算价格
                hotel_name = h.get("name", "")
                if any(kw in hotel_name for kw in ["如家", "汉庭", "7天", "锦江之星"]):
                    estimated_price = 180
                elif any(kw in hotel_name for kw in ["全季", "亚朵", "维也纳"]):
                    estimated_price = 320
                elif any(kw in hotel_name for kw in ["希尔顿", "万豪", "洲际", "喜来登"]):
                    estimated_price = 600
                else:
                    estimated_price = (min_price + max_price) // 2
            
            real_hotels.append({
                "name": h.get("name", "酒店"),
                "price": f"¥{estimated_price}起",
                "price_num": estimated_price,
                "rating": h.get("rating") or 4.5,
                "tags": h.get("type", "酒店").split(";")[:2] or ["热门"],
                "address": h.get("address", ""),
                "location": h.get("location"),  # 用于交通计算
            })
        
        # 按价格排序，筛选符合预算的酒店
        real_hotels.sort(key=lambda x: x.get("price_num", 999))
        logger.info("Real hotels fetched", count=len(real_hotels), budget=budget_level)
    except Exception as e:
        logger.warning("Hotel fetch failed", error=str(e))

    # 构建必去地点强调
    must_visit_text = ""
    if must_visit_places:
        must_visit_text = f"""
## ⭐ 用户必去地点（必须纳入行程！）
{json.dumps(must_visit_places, ensure_ascii=False)}

**重要**：以上是用户明确提出想去的地点，必须安排在行程中，并作为核心亮点！"""

    # 预构建 POI JSON 字符串（避免在 f-string 中使用双花括号导致 set 语法错误）
    pois_for_prompt = [
        {"name": p.get("name"), "type": p.get("type"), "address": p.get("address")} 
        for p in collected_pois[:8]
    ]
    pois_json = json.dumps(pois_for_prompt, ensure_ascii=False, indent=2)

    # ========== 构建规划提示词（含抵达日规则）==========
    planning_prompt = f"""你是一个专业的旅行规划师。请基于【真实 UGC 攻略】为用户制定行程。

⚠️ 核心原则：你的规划必须参考下面的真实攻略内容，不要凭空想象！

## 📋 用户需求
- **目的地**: {destination}
- **用户表述**: {user_days}天{user_nights}晚
- **实际规划**: {actual_days}天{actual_nights}晚（含抵达日）
- **旅行风格**: {travel_style}
{must_visit_text}

## 🛬 抵达日规则（极其重要！！！）

**用户说"{user_days}天{user_nights}晚"，但如果 Day 1 早上就有行程，需要前一天到达！**

实际行程应该是：
- **Day 0 (抵达日)**: 下午抵达{destination}，入住酒店，晚上简单逛逛
- **Day 1 - Day {user_days}**: 正式游玩
- **最后一天**: 返程，无住宿

实际住宿：{actual_nights} 晚（比用户说的多 1 晚，因为抵达日也要住）

### 抵达日（Day 0）必须包含：
1. 14:00-16:00 抵达目的地
2. 16:00-17:00 入住酒店
3. 18:00-21:00 酒店周边轻度探索/晚餐

### 抵达日住宿位置选择原则：
1. **主题公园行程**：抵达日住在公园附近（如环球影城→住通州区）
2. **市区景点行程**：抵达日住在交通枢纽/市中心附近

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
1. **抵达日（Day 0）**：轻松安排，主要是入住和周边简单逛逛
2. **主题公园（环球影城、迪士尼等）**：必须安排全天（09:00-21:00），当天不安排其他主要景点
3. **故宫/颐和园等大型景点**：至少安排半天（4小时）
4. **日落/夕阳观景**：只能在17:00-19:00
5. **夜景/灯光秀**：只能在19:00-22:00
6. **同一天景点**：应在同一区域，避免来回折腾
7. **每天2-3个主要景点**为宜，不要走马观花
8. **返程日**：根据航班时间灵活安排，可去机场附近购物

## 📍 可参考的景点 POI
{pois_json}

---

请返回纯 JSON 格式（不要 markdown 代码块）：
{{
    "chat_response": "一段友好的回复（200-300字），包含：1. 行程亮点 2. 为什么这样安排 3. 特别提醒",
    "trip_summary": {{
        "user_request": "{user_days}天{user_nights}晚",
        "actual_days": {actual_days},
        "actual_nights": {actual_nights},
        "includes_arrival_day": true
    }},
    "itinerary": [
        {{
            "day": 0,
            "day_type": "arrival",
            "title": "抵达{destination} & 入住休整",
            "activities": [
                {{
                    "time": "14:00",
                    "title": "抵达{destination}",
                    "type": "transport",
                    "desc": "根据航班/高铁时间抵达"
                }},
                {{
                    "time": "16:00",
                    "title": "入住酒店",
                    "type": "hotel",
                    "desc": "办理入住，稍作休息"
                }},
                {{
                    "time": "18:00",
                    "title": "酒店周边晚餐",
                    "type": "food",
                    "desc": "品尝当地美食"
                }}
            ],
            "accommodation": {{
                "name": "XXX酒店（靠近明日行程起点）",
                "reason": "📍 靠近明日行程起点",
                "price_range": "¥XXX-XXX",
                "stay_same_tomorrow": true
            }}
        }},
        {{
            "day": 1,
            "day_type": "play",
            "title": "正式游玩第一天（如：故宫中轴线深度游）",
            "activities": [
                {{
                    "time": "09:00",
                    "title": "活动名称",
                    "type": "attraction|food|hotel|transport",
                    "desc": "简短描述（30-50字），包含实用信息如门票、交通方式",
                    "transport_from_prev": {{
                        "from": "酒店",
                        "method": "地铁/公交/步行/打车",
                        "duration": "约30分钟",
                        "detail": "具体路线，如'地铁1号线→换乘2号线'"
                    }}
                }}
            ],
            "accommodation": {{
                "name": "推荐入住的酒店名称",
                "reason": "方便明天前往XX景点",
                "check_in_note": "入住提示",
                "stay_same_tomorrow": true,
                "next_day_first_spot": "第二天第一个景点"
            }}
        }},
        ... 中间天数按此格式继续 ...,
        {{
            "day": {user_days},
            "day_type": "departure",
            "title": "返程 & 再见{destination}",
            "activities": [
                {{
                    "time": "09:00",
                    "title": "酒店周边最后逛逛",
                    "type": "attraction",
                    "desc": "最后的自由时间，可以补充购物或打卡遗漏景点"
                }},
                {{
                    "time": "12:00",
                    "title": "前往机场/车站",
                    "type": "transport",
                    "desc": "建议提前2-3小时抵达，预留安检时间"
                }}
            ],
            "accommodation": null
        }}
    ],
    "accommodation_strategy": {{
        "type": "same_hotel|change_hotel|smart",
        "reason": "住宿策略说明"
    }},
    "recommended_hotels": []
}}

## 🏨 住宿安排规则（非常重要！）
1. **住宿是为了方便第二天的行程**，不是当天的！
2. **推荐理由必须基于第二天的行程**：例如"靠近明日行程起点XX"或"方便前往长城/环球影城"
3. **最后一天不需要住宿**（返程日）
4. **stay_same_tomorrow**：如果第二天景点在同一区域（距离 < 15km），设为 true
5. **主题公园**（环球影城、迪士尼等）：建议前一晚换到就近酒店，方便早起入园
6. **预算等级**：用户预算为「{budget_level}」级别（¥{min_price}-{max_price}/晚）

⚠️ 特别注意：
- Day1 的住宿推荐理由应该说"方便 Day2 前往XX"
- Day2 的住宿推荐理由应该说"方便 Day3 前往XX"
- 以此类推...

## 🚗 交通安排规则（非常重要！）
1. **每个活动必须包含 transport_from_prev**：说明从上一个地点如何到达
2. **第一个活动的 from**：填写"酒店"或"火车站/机场"（取决于当天是否换酒店）
3. **交通时间要合理**：
   - 地铁/公交一般 15-40 分钟
   - 打车一般 10-30 分钟
   - 步行一般 5-15 分钟
   - 跨城区可能需要 1 小时以上
4. **在北京**：故宫→长城需要约 1.5-2 小时（地铁+大巴），不能低估
5. **在上海**：外滩→迪士尼需要约 1 小时（地铁2号线→11号线）
6. **交通信息要具体**：不要只说"地铁"，要说"地铁X号线XX站上车"

只返回纯 JSON！"""

    # ========== 重新生成不同版本 ==========
    regenerate = state.get("regenerate", False)
    previous_itinerary = state.get("previous_itinerary")
    
    if regenerate and previous_itinerary:
        # 构建上一版行程摘要
        prev_summary = []
        for day in previous_itinerary[:5]:  # 最多展示5天
            day_num = day.get("day", "?")
            title = day.get("title", "")
            activities = day.get("activities", [])
            activity_names = [a.get("title", "") for a in activities[:3]]
            prev_summary.append(f"Day {day_num}: {title} - {', '.join(activity_names)}")
        
        prev_itinerary_text = "\n".join(prev_summary)
        
        regenerate_prompt = f"""

## 🔄 重新生成要求（非常重要！）

用户请求重新生成一个**不同版本**的行程。以下是上一版行程，请避免生成类似的安排：

### 上一版行程摘要（请避免重复）：
{prev_itinerary_text}

### 生成不同版本的策略：
1. **景点顺序调整**：如果上一版先去故宫再去颐和园，这次可以先去颐和园
2. **替换部分景点**：保留核心必去景点，但替换 1-2 个次要景点
3. **住宿区域变化**：尝试选择不同区域的酒店
4. **时间安排调整**：如果上一版某天安排较紧凑，这次可以更轻松
5. **美食推荐变化**：推荐不同的餐厅或美食

⚠️ 重要：用户明确要求不同版本，如果生成的行程与上一版过于相似，用户会不满意！
"""
        planning_prompt += regenerate_prompt
        logger.info("Added regeneration context to prompt", previous_days=len(previous_itinerary))

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
        "budget_info": {
            "level": budget_level,
            "min_price": min_price,
            "max_price": max_price,
        },
    }

    if structured_plan:
        travel_plan["structured"] = True
        travel_plan["chat_response"] = structured_plan.get("chat_response", "")
        itinerary_from_plan = structured_plan.get("itinerary", [])
        travel_plan["itinerary"] = itinerary_from_plan
        
        logger.info("Structured plan parsed",
                   has_itinerary=bool(itinerary_from_plan),
                   itinerary_len=len(itinerary_from_plan) if itinerary_from_plan else 0,
                   first_day_activities=len(itinerary_from_plan[0].get("activities", [])) if itinerary_from_plan else 0)
        travel_plan["accommodation_strategy"] = structured_plan.get("accommodation_strategy", {
            "type": "smart",
            "reason": "智能推荐，根据行程自动判断"
        })
        travel_plan["content"] = structured_plan.get("chat_response", "")
        
        # ========== 后处理：填充真实酒店数据到每日住宿 ==========
        if real_hotels:
            itinerary = travel_plan.get("itinerary", [])
            total_days = len(itinerary)
            
            for i, day_plan in enumerate(itinerary):
                # 最后一天不需要住宿
                if i >= total_days - 1:
                    day_plan["accommodation"] = None
                    continue
                
                # 获取 LLM 建议的住宿信息
                llm_accommodation = day_plan.get("accommodation", {})
                
                # 选择合适的酒店（轮换使用，或根据 stay_same_tomorrow 判断）
                if i == 0 or not llm_accommodation.get("stay_same_tomorrow", True):
                    # 第一天或需要换酒店：选择新酒店
                    hotel_index = min(i, len(real_hotels) - 1)
                    selected_hotel = real_hotels[hotel_index] if real_hotels else None
                else:
                    # 继续住同一家：使用前一天的酒店
                    prev_accommodation = itinerary[i - 1].get("accommodation", {})
                    selected_hotel = prev_accommodation.get("hotel_data")
                    if not selected_hotel and real_hotels:
                        selected_hotel = real_hotels[0]
                
                if selected_hotel:
                    # 获取酒店位置 - 从 hotel 数据中获取正确的坐标
                    hotel_location = selected_hotel.get("location")
                    location_dict = None
                    
                    if hotel_location:
                        # location 可能是多种格式：
                        # 1. tuple/list: (lng, lat)
                        # 2. dict: {"lat": x, "lng": y}  
                        # 3. string: "lng,lat"
                        if isinstance(hotel_location, (list, tuple)) and len(hotel_location) >= 2:
                            location_dict = {"lng": float(hotel_location[0]), "lat": float(hotel_location[1])}
                        elif isinstance(hotel_location, dict):
                            location_dict = hotel_location
                        elif isinstance(hotel_location, str) and "," in hotel_location:
                            parts = hotel_location.split(",")
                            if len(parts) >= 2:
                                try:
                                    location_dict = {"lng": float(parts[0]), "lat": float(parts[1])}
                                except ValueError:
                                    pass
                    
                    day_plan["accommodation"] = {
                        "name": selected_hotel.get("name"),
                        "price": selected_hotel.get("price"),
                        "address": selected_hotel.get("address", ""),
                        "rating": selected_hotel.get("rating"),
                        "tags": selected_hotel.get("tags", []),
                        "location": location_dict,  # 使用酒店自带的正确坐标
                        "reason": llm_accommodation.get("reason", "位置便利，性价比高"),
                        "check_in_note": llm_accommodation.get("check_in_note", "建议下午3点后入住"),
                        "stay_same_tomorrow": llm_accommodation.get("stay_same_tomorrow", True),
                        "hotel_data": selected_hotel,  # 保存完整数据用于后续日复用
                    }
                else:
                    # 无真实酒店数据，使用 LLM 生成的推荐
                    day_plan["accommodation"] = llm_accommodation
            
            logger.info("Accommodation data filled", 
                       days_with_hotel=sum(1 for d in itinerary if d.get("accommodation")))
        
        # ========== 后处理：为活动匹配 POI 坐标（使用高德 Geocoding API）==========
        itinerary = travel_plan.get("itinerary", [])
        
        # 构建 POI 名称到坐标的映射（从 collected_pois 中提取）
        poi_location_map = {}
        for poi in collected_pois:
            poi_name = poi.get("name", "")
            poi_location = poi.get("location", {})
            if poi_name and poi_location.get("lat") and poi_location.get("lng"):
                poi_location_map[poi_name] = poi_location
                # 同时用简短名称匹配（如 "故宫博物院" -> "故宫"）
                for short_name in [poi_name[:2], poi_name[:3], poi_name[:4]]:
                    if len(short_name) >= 2:
                        poi_location_map.setdefault(short_name, poi_location)
        
        # 收集所有需要地理编码的活动（未有坐标且未能从 POI 映射中匹配到的）
        activities_needing_geocode = []
        activities_with_location = 0
        
        # 酒店相关关键词（这些活动应使用酒店坐标）
        hotel_keywords = ["入住酒店", "入住", "酒店周边", "酒店附近", "住宿", "逛逛", "最后"]
        
        # 记录上一天的酒店位置，用于返程日
        prev_day_hotel_location = None
        
        for day_idx, day_plan in enumerate(itinerary):
            # 获取当天住宿的坐标
            accommodation = day_plan.get("accommodation", {})
            hotel_location = accommodation.get("location") if accommodation else None
            
            # 如果当天没有住宿（如返程日），使用前一天的酒店位置
            if not hotel_location and prev_day_hotel_location:
                hotel_location = prev_day_hotel_location
            
            # 更新前一天酒店位置，供下一天使用
            if accommodation and accommodation.get("location"):
                prev_day_hotel_location = accommodation.get("location")
            
            # 处理活动
            for activity in day_plan.get("activities", []):
                if activity.get("location"):
                    activities_with_location += 1
                    continue
                
                title = activity.get("title", "")
                act_type = activity.get("type", "")
                
                # 优先检查：如果是酒店相关的活动，使用 accommodation 的坐标
                is_hotel_activity = (
                    act_type == "hotel" or 
                    any(kw in title for kw in hotel_keywords)
                )
                
                if is_hotel_activity and hotel_location:
                    activity["location"] = hotel_location
                    activities_with_location += 1
                    logger.debug("Hotel activity matched to accommodation", title=title)
                    continue
                
                # 尝试从 POI 映射匹配
                matched_location = None
                for poi_name, location in poi_location_map.items():
                    if poi_name in title or title in poi_name:
                        matched_location = location
                        break
                
                if matched_location:
                    activity["location"] = matched_location
                    activities_with_location += 1
                else:
                    # 需要通过 geocoding API 获取
                    activities_needing_geocode.append(activity)
            
            # 处理住宿（酒店也需要坐标）
            accommodation = day_plan.get("accommodation")
            if accommodation and not accommodation.get("location"):
                hotel_name = accommodation.get("name", "")
                # 尝试从 POI 映射匹配
                matched_location = None
                for poi_name, location in poi_location_map.items():
                    if poi_name in hotel_name or hotel_name in poi_name:
                        matched_location = location
                        break
                
                if matched_location:
                    accommodation["location"] = matched_location
                elif hotel_name:
                    activities_needing_geocode.append(accommodation)
        
        # 使用高德 POI 搜索获取缺失的坐标（比 geocode 更准确）
        if activities_needing_geocode:
            try:
                import asyncio
                from src.tools.amap import get_amap_client
                
                amap_client = get_amap_client()
                max_search_calls = min(len(activities_needing_geocode), 10)  # 限制最多 10 个 API 调用
                
                logger.info("Starting POI search for activities", 
                           total_needing=len(activities_needing_geocode),
                           will_process=max_search_calls)
                
                for i, item in enumerate(activities_needing_geocode[:max_search_calls]):
                    title = item.get("title") or item.get("name", "")
                    if not title:
                        continue
                    
                    try:
                        # Rate limiting: 高德 QPS 限制
                        if i > 0:
                            await asyncio.sleep(0.35)  # 约 3 QPS
                        
                        # 使用 POI 搜索而不是 geocode（更准确）
                        pois = await amap_client.search_poi(title, destination, page_size=1)
                        if pois and len(pois) > 0:
                            poi = pois[0]
                            # POI.location 是 (lng, lat) 格式
                            item["location"] = {"lat": poi.location[1], "lng": poi.location[0]}
                            activities_with_location += 1
                            logger.debug("POI search success", title=title, poi_name=poi.name, location=poi.location)
                    except Exception as e:
                        logger.warning("POI search failed", title=title, error=str(e))
                        continue
                
            except Exception as e:
                logger.warning("POI search batch failed", error=str(e))
        
        logger.info("POI location matching completed", 
                   total_pois=len(poi_location_map),
                   activities_with_location=activities_with_location,
                   geocoded_count=min(len(activities_needing_geocode), 10) if activities_needing_geocode else 0)
        
        
        # ================ 真实交通计算后处理（可选，失败不影响返回）================
        try:
            # 注意：高德 API QPS 限制为 3，需要限流
            import asyncio
            from src.tools.amap import get_amap_client
            
            logger.info("Starting real transportation calculation (rate-limited)...")
            
            amap_client = get_amap_client()
            
            # 限制只对前 2 天进行详细交通计算，避免 API 超限
            max_days_for_transport = min(len(itinerary), 2)
            
            for day_idx, day_plan in enumerate(itinerary):
                # 只处理前几天，避免 API 超限
                if day_idx >= max_days_for_transport:
                    logger.info(f"Skipping day {day_idx + 1} transport calculation (rate limit)")
                    break
                    
                activities = day_plan.get("activities", [])
                if not activities:
                    continue
                
                # 每天只处理前 3 个活动的交通
                max_activities = min(len(activities), 3)
                    
                # 第一个活动的交通：从酒店出发
                prev_hotel = None
                if day_idx > 0:
                    prev_accommodation = itinerary[day_idx - 1].get("accommodation", {})
                    if prev_accommodation and prev_accommodation.get("location"):
                        # 直接使用已保存的坐标，避免额外 API 调用
                        prev_hotel = {
                            "name": prev_accommodation.get("name", "酒店"),
                            "location": (
                                prev_accommodation["location"].get("lng"),
                                prev_accommodation["location"].get("lat")
                            )
                        }
                
                prev_location = None
                prev_name = prev_hotel.get("name", "酒店") if prev_hotel else "酒店"
                
                if prev_hotel and prev_hotel.get("location") and prev_hotel["location"][0]:
                    prev_location = prev_hotel["location"]
                
                for act_idx, activity in enumerate(activities):
                    # 只处理前几个活动
                    if act_idx >= max_activities:
                        break
                        
                    activity_title = activity.get("title", "")
                    
                    # 搜索活动 POI 获取坐标
                    try:
                        # API 限流：每次调用前等待
                        await asyncio.sleep(0.5)
                        
                        pois = await amap_client.search_poi(
                            keywords=activity_title,
                            city=destination,
                            page_size=1
                        )
                        
                        if pois:
                            poi = pois[0]
                            current_location = poi.location
                            
                            # 保存位置信息
                            activity["location"] = {
                                "lng": current_location[0],
                                "lat": current_location[1]
                            }
                            activity["poi_name"] = poi.name
                            activity["poi_address"] = poi.address
                            
                            # 计算交通（如果有前一个位置）
                            if prev_location:
                                try:
                                    # API 限流
                                    await asyncio.sleep(0.5)
                                    
                                    route_result = await amap_client.route_planning(
                                        origin=prev_location,
                                        destination=current_location,
                                        mode="transit"  # 公共交通
                                    )
                                    
                                    if route_result:
                                        distance_km = round(route_result.distance / 1000, 1)
                                        duration_min = round(route_result.duration / 60)
                                        
                                        # 判断交通方式
                                        if distance_km < 1:
                                            method = "步行"
                                        elif distance_km < 3:
                                            method = "步行/公交"
                                        else:
                                            method = "地铁/公交"
                                        
                                        activity["transport_from_prev"] = {
                                            "from": prev_name,
                                            "method": method,
                                            "duration": f"约{duration_min}分钟",
                                            "distance": f"{distance_km}km",
                                            "detail": route_result.steps[0].get("instruction", "") if route_result.steps else "",
                                            "real_data": True  # 标记为真实数据
                                        }
                                    else:
                                        # 路线规划失败，使用 LLM 数据或默认值
                                        if "transport_from_prev" not in activity:
                                            activity["transport_from_prev"] = {
                                                "from": prev_name,
                                                "method": "公交/地铁",
                                                "duration": "约30分钟",
                                                "detail": "",
                                                "real_data": False
                                            }
                                except Exception as e:
                                    logger.warning(f"Route planning failed: {e}")
                            
                            # 更新前一个位置
                            prev_location = current_location
                            prev_name = activity_title
                        else:
                            # POI 搜索无结果，跳过
                            prev_name = activity_title
                            
                    except Exception as e:
                        logger.warning(f"POI search failed for {activity_title}: {e}")
                        prev_name = activity_title
                
            logger.info("Real transportation calculation completed")
        except Exception as transport_error:
            # 交通计算失败不影响返回，记录警告并继续
            logger.warning(f"Real transportation calculation failed (non-critical): {transport_error}")
        
        travel_plan["recommended_hotels"] = real_hotels if real_hotels else structured_plan.get("recommended_hotels", [])
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

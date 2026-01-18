"""
信息收集节点

增强版：多轮精准搜索 + 完整攻略抓取 + POI 结构保留
"""

import asyncio
import re
from datetime import datetime
from typing import Any

import structlog

from src.graphs.state import AgentState, PlanningPhase, TaskType
from src.graphs.poi.models import EnhancedPOI, POIDistanceMatrix
from src.tools.rate_limiter import with_rate_limit

logger = structlog.get_logger()


# ============================================================
# 多轮搜索工具函数（从 nodes.py 恢复）
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
            from src.tools.search import get_bocha_client
            
            client = get_bocha_client()
            results, _ = await client.search(query, count=count, freshness=None)
            
            # 转换为 dict 格式
            return [
                {
                    "title": r.title,
                    "snippet": r.snippet,
                    "url": r.url,
                    "source": r.source,
                }
                for r in results
            ] if results else []
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
                destination=destination, days=days, style=travel_style,
                must_visit=must_visit_places)
    
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
            if not r.get("from_cache") and url and any(domain in url for domain in [
                "zhihu.com", "mafengwo.cn", "xiaohongshu.com", 
                "ctrip.com", "you.ctrip.com", "travel.qunar.com"
            ]):
                high_quality_urls.append(url)
    
    logger.info("General guides collected", count=len(guides["general_guides"]))
    
    # ========== 第二轮：特定景点攻略（关键！）==========
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
                    if not r.get("from_cache") and url and any(domain in url for domain in ["zhihu.com", "mafengwo.cn", "xiaohongshu.com"]):
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
# POI 搜索函数（保留原有逻辑）
# ============================================================


async def _search_attractions(destination: str, count: int = 15) -> list[EnhancedPOI]:
    """搜索景点 POI（带坐标）"""
    pois = []
    try:
        from src.tools import search_poi
        
        # 搜索多种类型的景点
        keywords_list = ["景点", "公园", "博物馆", "古迹"]
        
        for keywords in keywords_list:
            # 使用全局限流器
            result = await with_rate_limit(
                search_poi.ainvoke,
                {
                    "keywords": keywords,
                    "city": destination,
                    "poi_type": "tourism",
                    "page_size": 5,
                }
            )
            
            for p in result.get("results", []):
                # 确保有坐标
                location = p.get("location")
                if not location:
                    continue
                
                # 解析坐标
                if isinstance(location, str) and "," in location:
                    lng, lat = map(float, location.split(","))
                elif isinstance(location, dict):
                    lat = float(location.get("lat", 0))
                    lng = float(location.get("lng", 0))
                else:
                    continue
                
                if lat == 0 or lng == 0:
                    continue
                
                pois.append(EnhancedPOI(
                    id=p.get("id", p.get("name", "")),
                    name=p.get("name", ""),
                    category="景点",
                    lat=lat,
                    lng=lng,
                    city=destination,
                    district=p.get("adname"),
                    address=p.get("address", ""),
                    rating=float(p.get("rating", 0)) if p.get("rating") else None,
                    duration_minutes=180,  # 景点默认 3 小时
                    tags=p.get("type", "").split(";") if p.get("type") else [],
                ))
            
            if len(pois) >= count:
                break
        
        logger.info("Attractions fetched", count=len(pois), city=destination)
    except Exception as e:
        logger.warning("Attraction search failed", error=str(e))
    
    return pois[:count]


async def _search_hotels(
    destination: str,
    budget_level: str = "moderate",
    count: int = 8,
) -> list[EnhancedPOI]:
    """搜索酒店 POI（带坐标）"""
    pois = []
    
    # 根据预算等级选择关键词
    keywords_map = {
        "economy": "如家 汉庭 7天",
        "moderate": "全季 亚朵 维也纳",
        "comfortable": "希尔顿花园 智选假日",
        "luxury": "丽思卡尔顿 安缦 四季",
    }
    
    try:
        from src.tools import search_poi
        
        # 使用全局限流器
        result = await with_rate_limit(
            search_poi.ainvoke,
            {
                "keywords": keywords_map.get(budget_level, "酒店"),
                "city": destination,
                "poi_type": "hotel",
                "page_size": count,
            }
        )
        
        for p in result.get("results", []):
            location = p.get("location")
            if not location:
                continue
            
            if isinstance(location, str) and "," in location:
                lng, lat = map(float, location.split(","))
            elif isinstance(location, dict):
                lat = float(location.get("lat", 0))
                lng = float(location.get("lng", 0))
            else:
                continue
            
            if lat == 0 or lng == 0:
                continue
            
            # 估算价格
            price = None
            if p.get("cost"):
                price = int(p.get("cost"))
            else:
                name = p.get("name", "")
                if any(kw in name for kw in ["如家", "汉庭", "7天"]):
                    price = 180
                elif any(kw in name for kw in ["全季", "亚朵"]):
                    price = 320
                elif any(kw in name for kw in ["希尔顿", "万豪"]):
                    price = 600
            
            pois.append(EnhancedPOI(
                id=p.get("id", p.get("name", "")),
                name=p.get("name", ""),
                category="酒店",
                lat=lat,
                lng=lng,
                city=destination,
                district=p.get("adname"),
                address=p.get("address", ""),
                rating=float(p.get("rating", 0)) if p.get("rating") else None,
                price=price,
                duration_minutes=0,
                tags=p.get("type", "").split(";") if p.get("type") else [],
            ))
        
        logger.info("Hotels fetched", count=len(pois), city=destination, budget=budget_level)
    except Exception as e:
        logger.warning("Hotel search failed", error=str(e))
    
    return pois[:count]


async def _search_restaurants(destination: str, count: int = 10) -> list[EnhancedPOI]:
    """搜索餐厅 POI（带坐标）"""
    pois = []
    
    try:
        from src.tools import search_poi
        
        # 使用全局限流器
        result = await with_rate_limit(
            search_poi.ainvoke,
            {
                "keywords": "餐厅 美食",
                "city": destination,
                "poi_type": "food",
                "page_size": count,
            }
        )
        
        for p in result.get("results", []):
            location = p.get("location")
            if not location:
                continue
            
            if isinstance(location, str) and "," in location:
                lng, lat = map(float, location.split(","))
            elif isinstance(location, dict):
                lat = float(location.get("lat", 0))
                lng = float(location.get("lng", 0))
            else:
                continue
            
            if lat == 0 or lng == 0:
                continue
            
            pois.append(EnhancedPOI(
                id=p.get("id", p.get("name", "")),
                name=p.get("name", ""),
                category="餐厅",
                lat=lat,
                lng=lng,
                city=destination,
                district=p.get("adname"),
                address=p.get("address", ""),
                rating=float(p.get("rating", 0)) if p.get("rating") else None,
                price=int(p.get("cost")) if p.get("cost") else None,
                duration_minutes=60,
                tags=p.get("type", "").split(";") if p.get("type") else [],
            ))
        
        logger.info("Restaurants fetched", count=len(pois), city=destination)
    except Exception as e:
        logger.warning("Restaurant search failed", error=str(e))
    
    return pois[:count]


async def _get_transport_hub(destination: str) -> EnhancedPOI | None:
    """获取交通枢纽（机场/火车站）作为抵达点"""
    try:
        from src.tools import search_poi
        
        # 先搜机场（使用全局限流器）
        result = await with_rate_limit(
            search_poi.ainvoke,
            {
                "keywords": "机场",
                "city": destination,
                "poi_type": "transport",
                "page_size": 1,
            }
        )
        
        if result.get("results"):
            p = result["results"][0]
            location = p.get("location")
            if location:
                if isinstance(location, str) and "," in location:
                    lng, lat = map(float, location.split(","))
                else:
                    lat = float(location.get("lat", 0))
                    lng = float(location.get("lng", 0))
                
                if lat and lng:
                    return EnhancedPOI(
                        id="arrival_hub",
                        name=p.get("name", f"{destination}机场"),
                        category="交通枢纽",
                        lat=lat,
                        lng=lng,
                        city=destination,
                        address=p.get("address", ""),
                        duration_minutes=0,
                    )
        
        # 没有机场，搜火车站
        result = await with_rate_limit(
            search_poi.ainvoke,
            {
                "keywords": "火车站",
                "city": destination,
                "poi_type": "transport",
                "page_size": 1,
            }
        )
        
        if result.get("results"):
            p = result["results"][0]
            location = p.get("location")
            if location:
                if isinstance(location, str) and "," in location:
                    lng, lat = map(float, location.split(","))
                else:
                    lat = float(location.get("lat", 0))
                    lng = float(location.get("lng", 0))
                
                if lat and lng:
                    return EnhancedPOI(
                        id="arrival_hub",
                        name=p.get("name", f"{destination}站"),
                        category="交通枢纽",
                        lat=lat,
                        lng=lng,
                        city=destination,
                        address=p.get("address", ""),
                        duration_minutes=0,
                    )
        
        logger.warning("No transport hub found", city=destination)
    except Exception as e:
        logger.warning("Transport hub search failed", error=str(e))
    
    return None


async def _get_weather(destination: str) -> dict | None:
    """获取天气信息"""
    try:
        from src.tools import get_weather
        return await get_weather.ainvoke({"city": destination})
    except Exception as e:
        logger.warning("Weather fetch failed", error=str(e))
        return None


# ============================================================
# 节点函数
# ============================================================


async def research_node(state: AgentState) -> dict[str, Any]:
    """
    信息收集节点（增强版）

    1. 多轮精准搜索：通用攻略 → 必去景点 → 美食 → 住宿
    2. 完整内容抓取：高质量源内容存入 RAG
    3. POI 搜索：景点/酒店/餐厅带坐标
    """
    logger.info("Node: research (enhanced with multi-round search)", task_type=state.get("task_type"))

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

        # 确定预算等级
        user_message = state.get("messages", [])[-1].content if state.get("messages") else ""
        budget_level = "moderate"
        if any(kw in user_message or kw in travel_style for kw in ["经济", "省钱", "穷游"]):
            budget_level = "economy"
        elif any(kw in user_message or kw in travel_style for kw in ["豪华", "高端", "五星"]):
            budget_level = "luxury"
        elif any(kw in user_message or kw in travel_style for kw in ["舒适", "商务"]):
            budget_level = "comfortable"

        # ========== 关键修复：多轮精准搜索 ==========
        logger.info("Starting multi-round guide search", 
                    city=destination, 
                    days=days,
                    must_visit=must_visit_places)
        
        guides = await _search_and_fetch_guides(
            destination=destination,
            days=days,
            travel_style=travel_style,
            must_visit_places=must_visit_places,
        )
        
        # 构建丰富的攻略上下文
        guide_context = _build_guide_context(guides)
        
        logger.info("Guide context built", 
                    context_length=len(guide_context),
                    full_content_count=len(guides.get("full_content", [])),
                    place_guides_count=len(guides.get("place_guides", [])))
        
        # ========== POI 搜索（串行，尊重 QPS 限制）==========
        logger.info("Starting sequential POI search (Amap QPS=3)", city=destination)
        
        # 1. 先获取天气（天气 API 不影响 POI 搜索的 QPS）
        weather_info = await _get_weather(destination)
        
        # 2. 串行获取 POI，每次调用之间会有内置延迟
        attractions = await _search_attractions(destination, count=10)
        hotels = await _search_hotels(destination, budget_level, count=5)
        restaurants = await _search_restaurants(destination, count=5)
        transport_hub = await _get_transport_hub(destination)
        
        # ========== 构建 POI 池和距离矩阵 ==========
        all_pois = []
        if transport_hub:
            all_pois.append(transport_hub)
        all_pois.extend(attractions)
        all_pois.extend(hotels)
        all_pois.extend(restaurants)
        
        # 创建距离矩阵
        distance_matrix = POIDistanceMatrix(all_pois)
        
        logger.info(
            "POI pool built",
            total=len(all_pois),
            attractions=len(attractions),
            hotels=len(hotels),
            restaurants=len(restaurants),
            has_transport_hub=transport_hub is not None,
        )
        
        # ========== 更新状态 ==========
        updates["weather_info"] = weather_info
        
        # 保存搜索结果摘要
        updates["search_results"] = guides.get("general_guides", []) + guides.get("place_guides", [])
        
        # 将 EnhancedPOI 转换为原始 dict 格式（兼容现有 planning_node）
        updates["collected_pois"] = [p.to_dict() for p in attractions]
        
        # 新增：存储完整 POI 池和距离矩阵
        updates["poi_pool"] = {p.id: p.to_dict() for p in all_pois}
        updates["distance_matrix"] = distance_matrix.to_dict()
        updates["arrival_hub"] = transport_hub.to_dict() if transport_hub else None
        
        # 更新 travel_preference（关键：guide_context）
        travel_pref["days"] = days
        travel_pref["budget_level"] = budget_level
        travel_pref["guide_context"] = guide_context  # 丰富的攻略上下文
        travel_pref["must_visit_places"] = must_visit_places  # 确保传递
        updates["travel_preference"] = travel_pref

        updates["planning_phase"] = PlanningPhase.PLANNING.value
        updates["next_action"] = "plan"

        return updates
        
    except Exception as e:
        import traceback
        logger.error(
            "research_node failed",
            error=str(e),
            traceback=traceback.format_exc(),
        )
        return {
            "next_action": "respond",
            "updated_at": datetime.now().isoformat(),
            "errors": [f"信息收集失败: {str(e)}"],
        }


__all__ = ["research_node"]

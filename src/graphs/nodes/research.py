"""
信息收集节点

串行 POI 搜索，使用全局限流器尊重高德 QPS=3
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
# 并行搜索函数
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

    并行执行 POI 搜索，确保每个 POI 都有坐标
    """
    logger.info("Node: research (enhanced)", task_type=state.get("task_type"))

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

        # ========== 串行搜索 POI（尊重高德 QPS=3 限制）==========
        # 不能用 asyncio.gather 并行，否则会同时发送多个请求触发 QPS 限制
        logger.info("Starting sequential POI search (Amap QPS=3)", city=destination)
        
        # 1. 先获取天气（天气 API 不影响 POI 搜索的 QPS）
        weather_info = await _get_weather(destination)
        
        # 2. 串行获取 POI，每次调用之间会有内置延迟
        attractions = await _search_attractions(destination, count=10)  # 减少数量
        hotels = await _search_hotels(destination, budget_level, count=5)  # 减少数量
        restaurants = await _search_restaurants(destination, count=5)  # 减少数量
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
        
        # 将 EnhancedPOI 转换为原始 dict 格式（兼容现有 planning_node）
        updates["collected_pois"] = [p.to_dict() for p in attractions]
        
        # 新增：存储完整 POI 池和距离矩阵
        updates["poi_pool"] = {p.id: p.to_dict() for p in all_pois}
        updates["distance_matrix"] = distance_matrix.to_dict()
        updates["arrival_hub"] = transport_hub.to_dict() if transport_hub else None
        
        # 更新 travel_preference
        travel_pref["days"] = days
        travel_pref["budget_level"] = budget_level
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

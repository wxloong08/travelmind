"""
LangGraph 工具定义

将各种 API 封装为 LangGraph 可用的工具
"""

from typing import Annotated, Any

import structlog
from langchain_core.tools import tool

from src.tools.amap import POIType, get_amap_client
from src.tools.search import get_bocha_client

logger = structlog.get_logger()


@tool
async def search_poi(
    keywords: Annotated[str, "搜索关键词，如'西湖'、'火锅店'"],
    city: Annotated[str, "城市名称，如'杭州'、'北京'"],
    poi_type: Annotated[
        str | None,
        "POI类型: scenic(景点), hotel(酒店), restaurant(餐厅), shopping(购物)"
    ] = None,
    page_size: Annotated[int, "返回数量，默认10"] = 10,
) -> dict[str, Any]:
    """
    搜索地点/景点/酒店/餐厅等 POI 信息。

    使用此工具来查找特定城市中的地点信息，包括景点、酒店、餐厅等。
    返回包含名称、地址、评分、人均消费等详细信息。
    """
    type_map = {
        "scenic": POIType.SCENIC.value,
        "hotel": POIType.HOTEL.value,
        "restaurant": POIType.RESTAURANT.value,
        "shopping": POIType.SHOPPING.value,
        "transport": POIType.TRANSPORT.value,
        "entertainment": POIType.ENTERTAINMENT.value,
    }

    types = type_map.get(poi_type) if poi_type else None

    client = get_amap_client()
    pois = await client.search_poi(
        keywords=keywords,
        city=city,
        types=types,
        page_size=min(page_size, 20),
    )

    # 转换为可序列化格式
    results = []
    for poi in pois:
        results.append({
            "name": poi.name,
            "address": poi.address,
            "type": poi.type,
            "rating": poi.rating,
            "cost": poi.cost,
            "tel": poi.tel,
            "city": poi.city,
            "district": poi.district,
            "location": {"lng": poi.location[0], "lat": poi.location[1]},
            "photos": poi.photos or [],  # 高德 POI 图片 URL 列表
        })

    return {
        "query": {"keywords": keywords, "city": city},
        "count": len(results),
        "results": results,
    }


@tool
async def search_nearby(
    lng: Annotated[float, "中心点经度"],
    lat: Annotated[float, "中心点纬度"],
    keywords: Annotated[str | None, "搜索关键词"] = None,
    radius: Annotated[int, "搜索半径（米），默认1000"] = 1000,
    poi_type: Annotated[str | None, "POI类型"] = None,
) -> dict[str, Any]:
    """
    搜索指定坐标附近的 POI。

    用于查找某个地点周边的景点、餐厅、酒店等。
    适合规划行程时查找附近可游玩/用餐的地点。
    """
    type_map = {
        "scenic": POIType.SCENIC.value,
        "hotel": POIType.HOTEL.value,
        "restaurant": POIType.RESTAURANT.value,
        "shopping": POIType.SHOPPING.value,
    }

    types = type_map.get(poi_type) if poi_type else None

    client = get_amap_client()
    pois = await client.search_around(
        location=(lng, lat),
        keywords=keywords,
        types=types,
        radius=min(radius, 5000),
    )

    results = []
    for poi in pois:
        results.append({
            "name": poi.name,
            "address": poi.address,
            "type": poi.type,
            "rating": poi.rating,
            "cost": poi.cost,
            "location": {"lng": poi.location[0], "lat": poi.location[1]},
            "photos": poi.photos or [],  # 高德 POI 图片 URL 列表
        })

    return {
        "center": {"lng": lng, "lat": lat},
        "radius": radius,
        "count": len(results),
        "results": results,
    }


@tool
async def get_route(
    origin_lng: Annotated[float, "起点经度"],
    origin_lat: Annotated[float, "起点纬度"],
    dest_lng: Annotated[float, "终点经度"],
    dest_lat: Annotated[float, "终点纬度"],
    mode: Annotated[str, "出行方式: driving(驾车), walking(步行), transit(公交)"] = "driving",
) -> dict[str, Any]:
    """
    获取两点之间的路线规划。

    用于计算景点之间的交通方式和预计时间，帮助合理安排行程。
    """
    client = get_amap_client()
    route = await client.route_planning(
        origin=(origin_lng, origin_lat),
        destination=(dest_lng, dest_lat),
        mode=mode,
    )

    if not route:
        return {"error": "无法规划路线"}

    return {
        "origin": {"lng": origin_lng, "lat": origin_lat},
        "destination": {"lng": dest_lng, "lat": dest_lat},
        "mode": mode,
        "distance_km": round(route.distance / 1000, 1),
        "duration_min": round(route.duration / 60),
        "steps": route.steps[:5],  # 只返回前5步
    }


@tool
async def get_weather(
    city: Annotated[str, "城市名称，如'杭州'、'北京'"],
    forecast: Annotated[bool, "是否获取天气预报，默认只获取实时天气"] = False,
) -> dict[str, Any]:
    """
    获取城市天气信息。

    用于为用户提供目的地的天气情况，帮助决定出行时间和穿着建议。
    """
    client = get_amap_client()
    weather = await client.weather(
        city=city,
        extensions="all" if forecast else "base",
    )

    if not weather:
        return {"error": "无法获取天气信息"}

    if forecast:
        # 预报数据
        return {
            "city": weather.get("city"),
            "forecasts": [
                {
                    "date": f.get("date"),
                    "week": f.get("week"),
                    "dayweather": f.get("dayweather"),
                    "nightweather": f.get("nightweather"),
                    "daytemp": f.get("daytemp"),
                    "nighttemp": f.get("nighttemp"),
                }
                for f in weather.get("casts", [])
            ],
        }
    else:
        # 实时数据
        return {
            "city": weather.get("city"),
            "weather": weather.get("weather"),
            "temperature": weather.get("temperature"),
            "winddirection": weather.get("winddirection"),
            "windpower": weather.get("windpower"),
            "humidity": weather.get("humidity"),
            "reporttime": weather.get("reporttime"),
        }


@tool
async def web_search(
    query: Annotated[str, "搜索关键词"],
    count: Annotated[int, "返回结果数量，默认5"] = 5,
    freshness: Annotated[
        str | None,
        "时效性过滤: day(24小时), week(一周), month(一个月)"
    ] = None,
) -> dict[str, Any]:
    """
    网络搜索最新信息。

    用于搜索旅游攻略、景点评价、最新活动、租房信息等实时内容。
    当需要获取最新资讯或用户询问特定话题时使用。
    """
    client = get_bocha_client()
    results, images = await client.search(
        query=query,
        count=min(count, 10),
        freshness=freshness,
    )

    return {
        "query": query,
        "count": len(results),
        "results": [
            {
                "title": r.title,
                "url": r.url,
                "snippet": r.snippet,
                "source": r.source,
                "date": r.published_date,
                "thumbnail": r.thumbnail,  # 新增：缩略图
            }
            for r in results
        ],
        "images": images,  # 新增：图片列表
    }


@tool
async def news_search(
    query: Annotated[str, "搜索关键词"],
    count: Annotated[int, "返回结果数量，默认5"] = 5,
) -> dict[str, Any]:
    """
    搜索最新新闻。

    用于获取与旅游目的地相关的最新新闻，如景区政策变化、活动信息等。
    """
    client = get_bocha_client()
    results = await client.news_search(
        query=query,
        count=min(count, 10),
    )

    return {
        "query": query,
        "count": len(results),
        "results": [
            {
                "title": r.title,
                "url": r.url,
                "snippet": r.snippet,
                "source": r.source,
                "date": r.published_date,
            }
            for r in results
        ],
    }


# 导出所有工具
ALL_TOOLS = [
    search_poi,
    search_nearby,
    get_route,
    get_weather,
    web_search,
    news_search,
]


def get_tool_definitions() -> list[dict[str, Any]]:
    """获取工具定义列表（OpenAI Function Calling 格式）"""
    definitions = []
    for tool_func in ALL_TOOLS:
        definitions.append({
            "type": "function",
            "function": {
                "name": tool_func.name,
                "description": tool_func.description,
                "parameters": tool_func.args_schema.model_json_schema() if tool_func.args_schema else {},
            },
        })
    return definitions

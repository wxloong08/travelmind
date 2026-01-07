"""
行程距离验证器

使用本地 Haversine 计算验证行程距离合理性
"""

from typing import Any

from src.graphs.poi.models import EnhancedPOI, POIDistanceMatrix
from src.graphs.utils.haversine import haversine


# 距离阈值（公里）
MAX_SAME_DAY_DISTANCE = 50.0  # 同天景点最大距离


def validate_itinerary_distances(
    itinerary: list[dict[str, Any]],
    poi_pool: dict[str, EnhancedPOI] | None = None,
    max_distance_km: float = MAX_SAME_DAY_DISTANCE,
) -> list[dict[str, Any]]:
    """
    本地验证行程距离，不调用外部 API
    
    Args:
        itinerary: 行程列表，每天包含 activities
        poi_pool: POI 池，key 为 POI ID
        max_distance_km: 最大允许距离（公里）
    
    Returns:
        违规列表: [{"day": 0, "from": "故宫", "to": "长城", "distance_km": 65.2}, ...]
    """
    violations = []
    
    for day in itinerary:
        day_idx = day.get("day", 0)
        activities = day.get("activities", [])
        
        if len(activities) < 2:
            continue
        
        # 获取每个活动的坐标
        coords = []
        for act in activities:
            lat, lng = None, None
            
            # 方式 1: 从 POI 池获取
            if poi_pool:
                poi_id = act.get("poi_id")
                if poi_id and poi_id in poi_pool:
                    poi = poi_pool[poi_id]
                    lat, lng = poi.lat, poi.lng
            
            # 方式 2: 从活动本身的 location 获取
            if not lat or not lng:
                location = act.get("location", {})
                if location:
                    lat = location.get("lat")
                    lng = location.get("lng")
            
            if lat and lng:
                coords.append({
                    "title": act.get("title", "未知"),
                    "lat": float(lat),
                    "lng": float(lng),
                })
        
        # 检查相邻活动距离
        for i in range(len(coords) - 1):
            c1 = coords[i]
            c2 = coords[i + 1]
            
            dist = haversine(c1["lat"], c1["lng"], c2["lat"], c2["lng"])
            
            if dist > max_distance_km:
                violations.append({
                    "day": day_idx,
                    "from": c1["title"],
                    "to": c2["title"],
                    "distance_km": round(dist, 1),
                    "threshold_km": max_distance_km,
                })
    
    return violations


def calculate_day_total_distance(
    activities: list[dict[str, Any]],
    poi_pool: dict[str, EnhancedPOI] | None = None,
) -> float:
    """
    计算一天内所有活动的总移动距离
    
    Returns:
        总距离（公里）
    """
    total = 0.0
    coords = []
    
    for act in activities:
        lat, lng = None, None
        
        if poi_pool:
            poi_id = act.get("poi_id")
            if poi_id and poi_id in poi_pool:
                poi = poi_pool[poi_id]
                lat, lng = poi.lat, poi.lng
        
        if not lat or not lng:
            location = act.get("location", {})
            if location:
                lat = location.get("lat")
                lng = location.get("lng")
        
        if lat and lng:
            coords.append((float(lat), float(lng)))
    
    for i in range(len(coords) - 1):
        total += haversine(coords[i][0], coords[i][1], coords[i+1][0], coords[i+1][1])
    
    return round(total, 1)

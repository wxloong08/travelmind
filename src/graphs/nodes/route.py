"""
路线增强节点（简化版）

在 POI-based 架构中，坐标已在 planning 阶段填充。
此节点负责计算活动间的交通方式和时间（基于本地距离计算）。
"""

from datetime import datetime
from typing import Any

import structlog

from src.graphs.state import AgentState
from src.graphs.utils.haversine import haversine

logger = structlog.get_logger()


def _estimate_transport(distance_km: float) -> dict:
    """
    基于距离估算交通方式和时长
    
    距离阈值：
    - < 1km: 步行
    - 1-5km: 地铁/公交
    - > 5km: 打车
    """
    if distance_km < 1:
        method = "步行"
        # 步行速度约 5km/h
        duration_min = int(distance_km / 5 * 60)
        duration_min = max(5, duration_min)  # 最少 5 分钟
    elif distance_km <= 5:
        method = "地铁/公交"
        # 公交平均速度约 15km/h（含等车）
        duration_min = int(distance_km / 15 * 60)
        duration_min = max(10, duration_min)  # 最少 10 分钟
    else:
        method = "打车/网约车"
        # 打车速度约 25km/h（市区均速）
        duration_min = int(distance_km / 25 * 60)
        duration_min = max(15, duration_min)  # 最少 15 分钟
    
    return {
        "method": method,
        "duration": f"约{duration_min}分钟",
        "distance_km": round(distance_km, 1),
    }


async def route_enrichment_node(state: AgentState) -> dict[str, Any]:
    """
    路线增强节点（简化版）
    
    在 POI-based 架构中：
    - 验证坐标已存在
    - 基于本地距离计算交通时间（无需 API 调用）
    """
    logger.info("Node: route_enrichment (simplified)")
    
    travel_plan = state.get("travel_plan")
    if not travel_plan or not travel_plan.get("itinerary"):
        logger.info("No itinerary to enrich, skipping")
        return {"next_action": "rule_check"}
    
    # 如果已经增强过，跳过
    if state.get("route_enriched"):
        logger.info("Routes already enriched, skipping")
        return {"next_action": "rule_check"}
    
    itinerary = travel_plan.get("itinerary", [])
    
    # 统计已有坐标的活动并计算交通
    total_activities = 0
    activities_with_location = 0
    transport_added = 0
    
    for day in itinerary:
        activities = day.get("activities", [])
        prev_location = None
        
        for activity in activities:
            total_activities += 1
            location = activity.get("location")
            
            if location and location.get("lat") and location.get("lng"):
                activities_with_location += 1
                
                # 计算与上一个活动的交通
                if prev_location:
                    distance = haversine(
                        prev_location["lat"], prev_location["lng"],
                        location["lat"], location["lng"]
                    )
                    transport_info = _estimate_transport(distance)
                    activity["transport_from_prev"] = transport_info
                    transport_added += 1
                
                prev_location = location
    
    # 更新 travel_plan
    updated_plan = {**travel_plan, "itinerary": itinerary}
    
    logger.info(
        "Route enrichment completed",
        total=total_activities,
        with_location=activities_with_location,
        coverage=f"{activities_with_location/max(1,total_activities)*100:.0f}%",
        transport_added=transport_added,
    )
    
    return {
        "travel_plan": updated_plan,
        "route_enriched": True,
        "next_action": "rule_check",
        "updated_at": datetime.now().isoformat(),
    }


__all__ = ["route_enrichment_node"]


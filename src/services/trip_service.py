"""
行程保存服务

在行程生成后保存到数据库
注意：预算计算由前端调用 /sidebar/budget API，住宿逻辑在前端处理
"""

import re
from typing import Any

import structlog

from src.config import settings

logger = structlog.get_logger()


async def save_trip_from_stream_event(
    event_data: dict[str, Any],
    session_id: str | None = None,
    user_id: str | None = None,
    guest_id: str | None = None,
) -> str | None:
    """
    从流式响应的 end 事件保存行程
    
    Args:
        event_data: SSE end 事件数据，包含 itinerary, destination_detected 等
        session_id: 会话 ID（用于关联对话）
        user_id: 用户 ID（登录用户）
        guest_id: 游客 ID
    
    Returns:
        保存的行程 ID 或 None
    """
    if not settings.database_enabled:
        logger.debug("Database not configured, skipping trip save")
        return None
    
    itinerary = event_data.get("itinerary")
    if not itinerary:
        logger.debug("No itinerary in event, skipping save")
        return None
    
    destination = event_data.get("destination_detected")
    if not destination:
        logger.debug("No destination in event, skipping save")
        return None
    
    try:
        from src.db.database import get_db_context
        from src.db.repositories import TripRepository
        
        async with get_db_context() as db:
            trip_repo = TripRepository(db)
            
            # 计算天数
            days = len(itinerary)
            
            # 生成标题
            title = f"{destination}{days}天之旅"
            
            # 创建行程
            trip = await trip_repo.create(
                title=title,
                destination=destination,
                days=days,
                itinerary_data={"days": itinerary},
                user_id=user_id,
                guest_id=guest_id,
                weather_snapshot=event_data.get("weather_forecast"),
                pois_snapshot=event_data.get("pois", [])[:20],
            )
            
            logger.info(
                "Trip saved from stream",
                trip_id=trip.id,
                destination=destination,
                days=days,
            )
            
            return trip.id
            
    except Exception as e:
        logger.error("Failed to save trip", error=str(e))
        return None


async def get_user_latest_trip(
    user_id: str | None = None,
    guest_id: str | None = None,
) -> dict | None:
    """
    获取用户最新的行程
    
    用于刷新页面后恢复状态
    """
    if not settings.database_enabled:
        return None
    
    if not user_id and not guest_id:
        return None
    
    try:
        from src.db.database import get_db_context
        from src.db.repositories import TripRepository
        
        async with get_db_context() as db:
            trip_repo = TripRepository(db)
            
            if user_id:
                trips = await trip_repo.get_by_user(user_id, limit=1)
            else:
                trips = await trip_repo.get_by_guest(guest_id, limit=1)
            
            if not trips:
                return None
            
            trip = trips[0]
            
            return {
                "id": trip.id,
                "title": trip.title,
                "destination": trip.destination,
                "days": trip.days,
                "itinerary": trip.itinerary_data.get("days", []),
                "weather": trip.weather_snapshot,
                "pois": trip.pois_snapshot,
                "created_at": trip.created_at.isoformat(),
            }
            
    except Exception as e:
        logger.error("Failed to get latest trip", error=str(e))
        return None

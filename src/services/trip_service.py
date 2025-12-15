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
    user_message: str | None = None,  # 用户输入的消息
    ai_response: str | None = None,   # AI 响应消息
) -> str | None:
    """
    从流式响应的 end 事件保存行程
    
    Args:
        event_data: SSE end 事件数据，包含 itinerary, destination_detected 等
        session_id: 会话 ID（用于关联对话）
        user_id: 用户 ID（登录用户）
        guest_id: 游客 ID
        user_message: 用户发送的消息内容
        ai_response: AI 的响应内容
    
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
        from src.db.repositories.conversation_repo import ConversationRepository
        
        async with get_db_context() as db:
            trip_repo = TripRepository(db)
            conv_repo = ConversationRepository(db)
            
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
            
            # 调试日志
            logger.debug(
                "Saving conversation",
                session_id=session_id,
                has_user_message=bool(user_message),
                has_ai_response=bool(ai_response),
                trip_id=str(trip.id),
            )
            
            # 创建或获取对话并保存消息
            if session_id:
                # 尝试获取现有对话，不存在则创建
                conversation = await conv_repo.get_conversation_by_session(session_id)
                if not conversation:
                    conversation = await conv_repo.create_conversation(
                        session_id=session_id,
                        user_id=user_id,
                        guest_id=guest_id,
                        title=f"{destination}行程规划",
                    )
                    logger.info("Created new conversation", conversation_id=conversation.id)
                
                # 保存用户消息
                if user_message:
                    await conv_repo.add_message(
                        conversation=conversation,
                        role="user",
                        content=user_message,
                    )
                
                # 保存 AI 响应
                if ai_response:
                    await conv_repo.add_message(
                        conversation=conversation,
                        role="assistant",
                        content=ai_response,
                    )
                
                # 关联对话到行程
                await conv_repo.link_trip(conversation, trip.id)
                logger.debug(
                    "Linked conversation to trip with messages",
                    conversation_id=conversation.id,
                    trip_id=trip.id,
                    user_msg_saved=bool(user_message),
                    ai_msg_saved=bool(ai_response),
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

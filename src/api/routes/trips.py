"""
行程管理 API 路由

提供:
- 获取用户行程列表
- 获取行程详情
- 删除行程
"""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel

from src.auth.deps import get_current_identity, require_auth, CurrentIdentity
from src.db.database import get_db, is_db_configured
from src.db.repositories import TripRepository
from src.db.repositories.conversation_repo import ConversationRepository

logger = structlog.get_logger()

router = APIRouter(prefix="/trips", tags=["Trips"])


# ============================================================
# 响应模型
# ============================================================

class TripSummary(BaseModel):
    """行程摘要"""
    id: str
    title: str
    destination: str
    days: int
    travel_date: str | None
    estimated_budget: int | None
    created_at: str
    
    class Config:
        from_attributes = True


class TripListResponse(BaseModel):
    """行程列表响应"""
    trips: list[TripSummary]
    total: int
    has_more: bool


class ConversationMessage(BaseModel):
    """对话消息"""
    role: str  # 'user' 或 'ai'
    content: str


class ConversationData(BaseModel):
    """对话数据"""
    id: str
    session_id: str | None
    messages: list[ConversationMessage]


class TripDetailResponse(BaseModel):
    """行程详情响应"""
    id: str
    title: str
    destination: str
    days: int
    travel_date: str | None
    user_budget: int | None
    estimated_budget: int | None
    itinerary_data: dict
    weather_snapshot: dict | None
    pois_snapshot: list | None = None
    created_at: str
    updated_at: str
    # 可选：关联的对话数据（用于恢复聊天记录）
    conversation: ConversationData | None = None
    
    class Config:
        from_attributes = True


# ============================================================
# 行程列表
# ============================================================

@router.get(
    "",
    response_model=TripListResponse,
    summary="获取行程列表",
)
async def get_trips(
    identity: Annotated[CurrentIdentity, Depends(require_auth)],
    db=Depends(get_db),
    limit: int = Query(default=20, ge=1, le=50, description="每页数量"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
):
    """
    获取当前用户/游客的行程列表
    
    - 登录用户：返回所有行程
    - 游客：返回最近 10 个行程
    """
    trip_repo = TripRepository(db)
    
    if identity.is_registered:
        trips = await trip_repo.get_by_user(
            user_id=identity.user.id,
            limit=limit + 1,  # 多取一个判断是否有更多
            offset=offset,
        )
    else:
        trips = await trip_repo.get_by_guest(
            guest_id=identity.guest.id,
            limit=min(limit, 10) + 1,
        )
    
    has_more = len(trips) > limit
    if has_more:
        trips = trips[:limit]
    
    return TripListResponse(
        trips=[
            TripSummary(
                id=trip.id,
                title=trip.title,
                destination=trip.destination,
                days=trip.days,
                travel_date=trip.travel_date.isoformat() if trip.travel_date else None,
                estimated_budget=trip.estimated_budget,
                created_at=trip.created_at.isoformat(),
            )
            for trip in trips
        ],
        total=len(trips),
        has_more=has_more,
    )


# ============================================================
# 恢复最新行程（刷新页面后）- 必须在 /{trip_id} 之前定义
# ============================================================

@router.get(
    "/latest",
    response_model=TripDetailResponse,
    summary="获取最新行程（用于刷新恢复）",
)
async def get_latest_trip(
    identity: Annotated[CurrentIdentity, Depends(require_auth)],
    db=Depends(get_db),
):
    """
    获取用户最新的行程
    
    用于刷新页面后恢复状态（包含对话历史）
    """
    trip_repo = TripRepository(db)
    
    if identity.is_registered:
        trips = await trip_repo.get_by_user(identity.user.id, limit=1)
    else:
        trips = await trip_repo.get_by_guest(identity.guest.id, limit=1)
    
    if not trips:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="暂无行程记录",
        )
    
    trip = trips[0]
    
    # 获取关联的对话和消息
    conversation_data = None
    try:
        conv_repo = ConversationRepository(db)
        # Trip 模型有 conversations 关系，获取最新的对话
        if trip.conversations:
            conversation = trip.conversations[0]  # 取第一个（最新的）
            messages = await conv_repo.get_messages(conversation.id, limit=100)
            conversation_data = ConversationData(
                id=conversation.id,
                session_id=conversation.session_id if hasattr(conversation, 'session_id') else None,
                messages=[
                    ConversationMessage(role=msg.role, content=msg.content)
                    for msg in messages
                ],
            )
            logger.debug("Loaded conversation", 
                        conversation_id=conversation.id, 
                        message_count=len(messages))
    except Exception as e:
        logger.warning("Failed to load conversation", error=str(e))
    
    return TripDetailResponse(
        id=trip.id,
        title=trip.title,
        destination=trip.destination,
        days=trip.days,
        travel_date=trip.travel_date.isoformat() if trip.travel_date else None,
        user_budget=trip.user_budget,
        estimated_budget=trip.estimated_budget,
        itinerary_data=trip.itinerary_data,
        weather_snapshot=trip.weather_snapshot,
        pois_snapshot=trip.pois_snapshot,
        created_at=trip.created_at.isoformat(),
        updated_at=trip.updated_at.isoformat(),
        conversation=conversation_data,
    )


# ============================================================
# 检查匹配的行程（重复检测）
# ============================================================

class MatchRequest(BaseModel):
    """行程匹配请求"""
    destination: str
    days: int


class MatchResponse(BaseModel):
    """行程匹配响应"""
    matched: bool
    trip: TripDetailResponse | None = None


@router.post(
    "/match",
    response_model=MatchResponse,
    summary="检查是否有匹配的历史行程",
)
async def match_trip(
    request: MatchRequest,
    identity: Annotated[CurrentIdentity, Depends(require_auth)],
    db=Depends(get_db),
):
    """
    检查用户是否有相同目的地+天数的历史行程
    
    用于重复检测：如果有匹配，前端可直接加载而非重新生成
    """
    trip_repo = TripRepository(db)
    conv_repo = ConversationRepository(db)
    
    # 获取用户/游客的行程列表
    if identity.is_registered:
        trips = await trip_repo.get_by_user(identity.user.id, limit=50)
    else:
        trips = await trip_repo.get_by_guest(identity.guest.id, limit=20)
    
    # 查找匹配的行程
    matched_trip = None
    for trip in trips:
        if trip.destination == request.destination and trip.days == request.days:
            matched_trip = trip
            break
    
    if not matched_trip:
        return MatchResponse(matched=False, trip=None)
    
    # 获取对话历史
    conversation_data = None
    try:
        # 使用 Trip 模型的 conversations 关系（和 get_latest_trip 一致）
        if matched_trip.conversations:
            conversation = matched_trip.conversations[0]  # 取第一个（最新的）
            messages = await conv_repo.get_messages(conversation.id, limit=100)
            conversation_data = ConversationData(
                id=conversation.id,
                session_id=conversation.session_id if hasattr(conversation, 'session_id') else None,
                messages=[
                    ConversationMessage(role=m.role, content=m.content)
                    for m in messages
                ]
            )
    except Exception as e:
        logger.warning("Failed to load conversation for matched trip", error=str(e))
    
    return MatchResponse(
        matched=True,
        trip=TripDetailResponse(
            id=matched_trip.id,
            title=matched_trip.title,
            destination=matched_trip.destination,
            days=matched_trip.days,
            travel_date=matched_trip.travel_date.isoformat() if matched_trip.travel_date else None,
            user_budget=matched_trip.user_budget,
            estimated_budget=matched_trip.estimated_budget,
            itinerary_data=matched_trip.itinerary_data,
            weather_snapshot=matched_trip.weather_snapshot,
            pois_snapshot=matched_trip.pois_snapshot,
            created_at=matched_trip.created_at.isoformat(),
            updated_at=matched_trip.updated_at.isoformat(),
            conversation=conversation_data,
        )
    )


# ============================================================
# 行程详情
# ============================================================

@router.get(
    "/{trip_id}",
    response_model=TripDetailResponse,
    summary="获取行程详情",
)
async def get_trip_detail(
    trip_id: str,
    identity: Annotated[CurrentIdentity, Depends(require_auth)],
    db=Depends(get_db),
):
    """
    获取行程详情
    
    只能获取自己的行程
    """
    trip_repo = TripRepository(db)
    trip = await trip_repo.get_by_id(trip_id)
    
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="行程不存在",
        )
    
    # 检查权限
    is_owner = (
        (identity.is_registered and trip.user_id == identity.user.id) or
        (identity.is_guest and trip.guest_id == identity.guest.id)
    )
    
    if not is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此行程",
        )
    
    # 获取关联的对话和消息
    conversation_data = None
    try:
        conv_repo = ConversationRepository(db)
        # Trip 模型有 conversations 关系，获取最新的对话
        if trip.conversations:
            conversation = trip.conversations[0]  # 取第一个（最新的）
            messages = await conv_repo.get_messages(conversation.id, limit=100)
            conversation_data = ConversationData(
                id=conversation.id,
                session_id=conversation.session_id if hasattr(conversation, 'session_id') else None,
                messages=[
                    ConversationMessage(role=msg.role, content=msg.content)
                    for msg in messages
                ],
            )
            logger.debug("Loaded conversation for trip detail", 
                        conversation_id=conversation.id, 
                        message_count=len(messages))
    except Exception as e:
        logger.warning("Failed to load conversation for trip detail", error=str(e))
    
    return TripDetailResponse(
        id=trip.id,
        title=trip.title,
        destination=trip.destination,
        days=trip.days,
        travel_date=trip.travel_date.isoformat() if trip.travel_date else None,
        user_budget=trip.user_budget,
        estimated_budget=trip.estimated_budget,
        itinerary_data=trip.itinerary_data,
        weather_snapshot=trip.weather_snapshot,
        pois_snapshot=trip.pois_snapshot,
        created_at=trip.created_at.isoformat(),
        updated_at=trip.updated_at.isoformat(),
        conversation=conversation_data,
    )


# ============================================================
# 删除行程
# ============================================================

@router.delete(
    "/{trip_id}",
    summary="删除行程",
)
async def delete_trip(
    trip_id: str,
    identity: Annotated[CurrentIdentity, Depends(require_auth)],
    db=Depends(get_db),
):
    """
    删除行程
    
    只能删除自己的行程
    """
    trip_repo = TripRepository(db)
    trip = await trip_repo.get_by_id(trip_id)
    
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="行程不存在",
        )
    
    # 检查权限
    is_owner = (
        (identity.is_registered and trip.user_id == identity.user.id) or
        (identity.is_guest and trip.guest_id == identity.guest.id)
    )
    
    if not is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权删除此行程",
        )
    
    await trip_repo.delete(trip)
    logger.info("Trip deleted", trip_id=trip_id, user_id=identity.id)
    
    return {"message": "行程已删除"}


# ============================================================
# 按目的地查询（可选功能）
# ============================================================

@router.get(
    "/search/destination",
    response_model=TripListResponse,
    summary="按目的地搜索行程",
)
async def search_trips_by_destination(
    destination: str = Query(..., min_length=1, description="目的地"),
    identity: Annotated[CurrentIdentity, Depends(require_auth)] = None,
    db=Depends(get_db),
    limit: int = Query(default=10, ge=1, le=20),
):
    """
    按目的地搜索自己的行程
    """
    trip_repo = TripRepository(db)
    
    user_id = identity.user.id if identity.is_registered else None
    
    if not user_id:
        # 游客不支持搜索
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="游客不支持搜索功能",
        )
    
    trips = await trip_repo.get_by_destination(
        destination=destination,
        user_id=user_id,
        limit=limit,
    )
    
    return TripListResponse(
        trips=[
            TripSummary(
                id=trip.id,
                title=trip.title,
                destination=trip.destination,
                days=trip.days,
                travel_date=trip.travel_date.isoformat() if trip.travel_date else None,
                estimated_budget=trip.estimated_budget,
                created_at=trip.created_at.isoformat(),
            )
            for trip in trips
        ],
        total=len(trips),
        has_more=False,
    )

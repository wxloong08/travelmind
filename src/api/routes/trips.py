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
    created_at: str
    updated_at: str
    
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
        created_at=trip.created_at.isoformat(),
        updated_at=trip.updated_at.isoformat(),
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


# ============================================================
# 恢复最新行程（刷新页面后）
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
    
    用于刷新页面后恢复状态
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
        created_at=trip.created_at.isoformat(),
        updated_at=trip.updated_at.isoformat(),
    )

"""
行程数据访问层
"""

from datetime import date

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.trip import Trip


class TripRepository:
    """行程数据访问"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self,
        title: str,
        destination: str,
        days: int,
        itinerary_data: dict,
        user_id: str | None = None,
        guest_id: str | None = None,
        travel_date: date | None = None,
        user_budget: int | None = None,
        estimated_budget: int | None = None,
        raw_response: str | None = None,
        weather_snapshot: dict | None = None,
        pois_snapshot: list | None = None,
    ) -> Trip:
        """创建行程"""
        trip = Trip(
            user_id=user_id,
            guest_id=guest_id,
            title=title,
            destination=destination,
            days=days,
            travel_date=travel_date,
            user_budget=user_budget,
            estimated_budget=estimated_budget,
            itinerary_data=itinerary_data,
            raw_response=raw_response,
            weather_snapshot=weather_snapshot,
            pois_snapshot=pois_snapshot,
        )
        self.session.add(trip)
        await self.session.flush()
        return trip
    
    async def get_by_id(self, trip_id: str) -> Trip | None:
        """根据 ID 获取行程"""
        result = await self.session.execute(
            select(Trip).where(Trip.id == trip_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_user(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Trip]:
        """获取用户的所有行程"""
        result = await self.session.execute(
            select(Trip)
            .where(Trip.user_id == user_id)
            .order_by(desc(Trip.created_at))
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
    
    async def get_by_guest(
        self,
        guest_id: str,
        limit: int = 10,
        offset: int = 0,
    ) -> list[Trip]:
        """获取游客的所有行程"""
        result = await self.session.execute(
            select(Trip)
            .where(Trip.guest_id == guest_id)
            .order_by(desc(Trip.created_at))
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
    
    async def get_by_destination(
        self,
        destination: str,
        user_id: str | None = None,
        limit: int = 10,
    ) -> list[Trip]:
        """根据目的地查询行程"""
        query = select(Trip).where(Trip.destination == destination)
        
        if user_id:
            query = query.where(Trip.user_id == user_id)
        
        query = query.order_by(desc(Trip.created_at)).limit(limit)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def delete(self, trip: Trip) -> None:
        """删除行程"""
        await self.session.delete(trip)
    
    async def update_budget(
        self,
        trip: Trip,
        user_budget: int | None = None,
        estimated_budget: int | None = None,
    ) -> None:
        """更新预算信息"""
        if user_budget is not None:
            trip.user_budget = user_budget
        if estimated_budget is not None:
            trip.estimated_budget = estimated_budget
    
    async def count_by_user(self, user_id: str) -> int:
        """统计用户行程数量"""
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.count(Trip.id)).where(Trip.user_id == user_id)
        )
        return result.scalar_one()

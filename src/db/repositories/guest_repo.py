"""
游客数据访问层
"""

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.guest import Guest


class GuestRepository:
    """游客数据访问"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, device_fingerprint: str) -> Guest:
        """创建游客"""
        guest = Guest(
            device_fingerprint=device_fingerprint,
            last_usage_date=date.today(),
        )
        self.session.add(guest)
        await self.session.flush()
        return guest
    
    async def get_by_id(self, guest_id: str) -> Guest | None:
        """根据 ID 获取游客"""
        result = await self.session.execute(
            select(Guest).where(Guest.id == guest_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_fingerprint(self, fingerprint: str) -> Guest | None:
        """根据设备指纹获取游客"""
        result = await self.session.execute(
            select(Guest).where(Guest.device_fingerprint == fingerprint)
        )
        return result.scalar_one_or_none()
    
    async def get_or_create(self, device_fingerprint: str) -> tuple[Guest, bool]:
        """
        根据设备指纹获取或创建游客
        
        Returns:
            (guest, created): 游客对象和是否新创建
        """
        guest = await self.get_by_fingerprint(device_fingerprint)
        if guest:
            return guest, False
        
        guest = await self.create(device_fingerprint)
        return guest, True
    
    async def check_and_increment_usage(self, guest: Guest) -> bool:
        """
        检查并增加使用次数
        
        Returns:
            是否允许使用（未超过每日限制）
        """
        today = date.today()
        
        # 新的一天，重置计数
        if guest.last_usage_date != today:
            guest.daily_usage_count = 0
            guest.last_usage_date = today
        
        # 检查限制
        if guest.daily_usage_count >= Guest.DAILY_LIMIT:
            return False
        
        # 增加计数
        guest.daily_usage_count += 1
        guest.total_usage_count += 1
        
        return True
    
    async def get_remaining_usage(self, guest: Guest) -> int:
        """获取今日剩余使用次数"""
        today = date.today()
        
        if guest.last_usage_date != today:
            return Guest.DAILY_LIMIT
        
        return max(0, Guest.DAILY_LIMIT - guest.daily_usage_count)

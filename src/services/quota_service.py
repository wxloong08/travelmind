"""
配额服务

管理用户/游客的使用次数
"""

from datetime import date, datetime, timezone
from typing import Any

import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import (
    User, Guest, UserRole, DEFAULT_QUOTAS,
    ActivationCode, CodeType,
    UsageRecord, DailyUsageSummary,
)

logger = structlog.get_logger()


# 游客每日配额
GUEST_DAILY_QUOTA = 1


class QuotaService:
    """配额管理服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ============================================================
    # 配额查询
    # ============================================================
    
    async def get_user_quota_info(self, user: User) -> dict[str, Any]:
        """
        获取用户配额信息
        
        Returns:
            {
                "daily_quota": 3,      # 每日配额
                "bonus_quota": 5,      # 额外次数
                "used_today": 1,       # 今日已用
                "remaining_today": 7,  # 今日剩余（daily + bonus - used）
                "role": "free",
            }
        """
        today = date.today()
        
        # 获取每日配额
        daily_quota = user.get_effective_daily_quota()
        
        # 获取今日已用次数
        used_today = await self._get_daily_usage_count(user_id=user.id, usage_date=today)
        
        # 计算剩余次数
        # 优先消耗每日配额，超出部分消耗 bonus
        if used_today <= daily_quota:
            remaining_daily = daily_quota - used_today
            remaining_bonus = user.bonus_quota
        else:
            remaining_daily = 0
            bonus_used = used_today - daily_quota
            remaining_bonus = max(0, user.bonus_quota - bonus_used)
        
        remaining_today = remaining_daily + remaining_bonus
        
        return {
            "daily_quota": daily_quota,
            "bonus_quota": user.bonus_quota,
            "used_today": used_today,
            "remaining_today": remaining_today,
            "remaining_daily": remaining_daily,
            "remaining_bonus": remaining_bonus,
            "role": user.role,
            "is_unlimited": user.role == UserRole.ADMIN.value,
        }
    
    async def get_guest_quota_info(self, guest: Guest) -> dict[str, Any]:
        """
        获取游客配额信息
        """
        today = date.today()
        
        # 获取今日已用次数
        used_today = await self._get_daily_usage_count(guest_id=guest.id, usage_date=today)
        
        remaining_today = max(0, GUEST_DAILY_QUOTA - used_today)
        
        return {
            "daily_quota": GUEST_DAILY_QUOTA,
            "bonus_quota": 0,
            "used_today": used_today,
            "remaining_today": remaining_today,
            "is_guest": True,
        }
    
    async def _get_daily_usage_count(
        self,
        user_id: str | None = None,
        guest_id: str | None = None,
        usage_date: date | None = None,
    ) -> int:
        """获取指定日期的使用次数"""
        usage_date = usage_date or date.today()
        
        # 先尝试从汇总表获取
        query = select(DailyUsageSummary).where(
            DailyUsageSummary.usage_date == usage_date
        )
        
        if user_id:
            query = query.where(DailyUsageSummary.user_id == user_id)
        elif guest_id:
            query = query.where(DailyUsageSummary.guest_id == guest_id)
        else:
            return 0
        
        result = await self.db.execute(query)
        summary = result.scalar_one_or_none()
        
        if summary:
            return summary.usage_count
        
        # 如果汇总表没有，从明细表统计
        count_query = select(func.count()).select_from(UsageRecord).where(
            UsageRecord.usage_date == usage_date
        )
        
        if user_id:
            count_query = count_query.where(UsageRecord.user_id == user_id)
        elif guest_id:
            count_query = count_query.where(UsageRecord.guest_id == guest_id)
        
        result = await self.db.execute(count_query)
        return result.scalar() or 0
    
    # ============================================================
    # 配额检查和消耗
    # ============================================================
    
    async def check_and_consume(
        self,
        user_id: str | None = None,
        guest_id: str | None = None,
        destination: str | None = None,
        days: int | None = None,
        session_id: str | None = None,
    ) -> tuple[bool, str, dict]:
        """
        检查配额并消耗一次
        
        Returns:
            (success, message, quota_info)
        """
        today = date.today()
        now = datetime.now(timezone.utc)
        
        if user_id:
            # 用户
            user = await self.db.get(User, user_id)
            if not user:
                return False, "用户不存在", {}
            
            if not user.is_active:
                return False, "账号已被禁用", {}
            
            # 管理员无限制
            if user.role == UserRole.ADMIN.value:
                await self._record_usage(user_id=user_id, destination=destination, 
                                        days=days, session_id=session_id)
                return True, "管理员无限制", await self.get_user_quota_info(user)
            
            quota_info = await self.get_user_quota_info(user)
            
            if quota_info["remaining_today"] <= 0:
                return False, "今日使用次数已用完", quota_info
            
            # 记录使用
            await self._record_usage(user_id=user_id, destination=destination,
                                    days=days, session_id=session_id)
            
            # 如果超出每日配额，扣减 bonus
            if quota_info["used_today"] >= quota_info["daily_quota"]:
                user.bonus_quota = max(0, user.bonus_quota - 1)
                await self.db.commit()
            
            # 返回更新后的配额信息
            quota_info = await self.get_user_quota_info(user)
            return True, "ok", quota_info
            
        elif guest_id:
            # 游客
            guest = await self.db.get(Guest, guest_id)
            if not guest:
                return False, "游客不存在", {}
            
            quota_info = await self.get_guest_quota_info(guest)
            
            if quota_info["remaining_today"] <= 0:
                return False, "今日使用次数已用完，请登录获取更多次数", quota_info
            
            # 记录使用
            await self._record_usage(guest_id=guest_id, destination=destination,
                                    days=days, session_id=session_id)
            
            quota_info = await self.get_guest_quota_info(guest)
            return True, "ok", quota_info
        
        else:
            return False, "未提供身份信息", {}
    
    async def _record_usage(
        self,
        user_id: str | None = None,
        guest_id: str | None = None,
        destination: str | None = None,
        days: int | None = None,
        session_id: str | None = None,
    ):
        """记录使用"""
        today = date.today()
        now = datetime.now(timezone.utc)
        
        # 添加使用记录
        record = UsageRecord(
            user_id=user_id,
            guest_id=guest_id,
            usage_date=today,
            used_at=now,
            destination=destination,
            days=days,
            session_id=session_id,
        )
        self.db.add(record)
        
        # 更新汇总表
        query = select(DailyUsageSummary).where(
            DailyUsageSummary.usage_date == today
        )
        if user_id:
            query = query.where(DailyUsageSummary.user_id == user_id)
        elif guest_id:
            query = query.where(DailyUsageSummary.guest_id == guest_id)
        
        result = await self.db.execute(query)
        summary = result.scalar_one_or_none()
        
        if summary:
            summary.usage_count += 1
            summary.updated_at = now
        else:
            summary = DailyUsageSummary(
                user_id=user_id,
                guest_id=guest_id,
                usage_date=today,
                usage_count=1,
                updated_at=now,
            )
            self.db.add(summary)
        
        await self.db.commit()
        
        logger.info(
            "Usage recorded",
            user_id=user_id,
            guest_id=guest_id,
            destination=destination,
        )
    
    # ============================================================
    # 激活码
    # ============================================================
    
    async def use_activation_code(
        self,
        user_id: str,
        code: str,
    ) -> tuple[bool, str]:
        """
        使用激活码
        
        Returns:
            (success, message)
        """
        # 查找激活码
        query = select(ActivationCode).where(ActivationCode.code == code.upper())
        result = await self.db.execute(query)
        activation_code = result.scalar_one_or_none()
        
        if not activation_code:
            return False, "激活码不存在"
        
        if not activation_code.is_valid:
            if activation_code.is_used:
                return False, "激活码已被使用"
            return False, "激活码已过期"
        
        # 获取用户
        user = await self.db.get(User, user_id)
        if not user:
            return False, "用户不存在"
        
        # 根据类型处理
        if activation_code.code_type == CodeType.UPGRADE_PAID.value:
            # 升级为付费用户
            user.role = UserRole.PAID.value
            user.daily_quota = DEFAULT_QUOTAS[UserRole.PAID]
            message = "恭喜！已升级为付费用户，每日可规划 20 次行程"
            
        elif activation_code.code_type == CodeType.ADD_QUOTA.value:
            # 增加额外次数
            user.bonus_quota += activation_code.quota_value
            message = f"成功增加 {activation_code.quota_value} 次使用机会"
            
        else:
            return False, "未知的激活码类型"
        
        # 标记激活码为已使用
        activation_code.is_used = True
        activation_code.used_at = datetime.now(timezone.utc)
        activation_code.used_by_id = user_id
        
        await self.db.commit()
        
        logger.info(
            "Activation code used",
            code=code,
            user_id=user_id,
            code_type=activation_code.code_type,
        )
        
        return True, message
    
    # ============================================================
    # 管理员操作
    # ============================================================
    
    async def admin_add_bonus(
        self,
        admin_id: str,
        target_user_id: str,
        amount: int,
    ) -> tuple[bool, str]:
        """
        管理员为用户增加临时次数
        """
        # 验证管理员身份
        admin = await self.db.get(User, admin_id)
        if not admin or admin.role != UserRole.ADMIN.value:
            return False, "无权限操作"
        
        # 获取目标用户
        target = await self.db.get(User, target_user_id)
        if not target:
            return False, "目标用户不存在"
        
        # 增加 bonus
        target.bonus_quota += amount
        await self.db.commit()
        
        logger.info(
            "Admin added bonus quota",
            admin_id=admin_id,
            target_user_id=target_user_id,
            amount=amount,
            new_bonus=target.bonus_quota,
        )
        
        return True, f"已为用户增加 {amount} 次额外使用机会"
    
    async def admin_set_daily_quota(
        self,
        admin_id: str,
        target_user_id: str,
        quota: int,
    ) -> tuple[bool, str]:
        """
        管理员修改用户每日配额
        """
        # 验证管理员身份
        admin = await self.db.get(User, admin_id)
        if not admin or admin.role != UserRole.ADMIN.value:
            return False, "无权限操作"
        
        # 获取目标用户
        target = await self.db.get(User, target_user_id)
        if not target:
            return False, "目标用户不存在"
        
        old_quota = target.daily_quota
        target.daily_quota = quota
        await self.db.commit()
        
        logger.info(
            "Admin set daily quota",
            admin_id=admin_id,
            target_user_id=target_user_id,
            old_quota=old_quota,
            new_quota=quota,
        )
        
        return True, f"已将用户每日配额从 {old_quota} 改为 {quota}"
    
    async def admin_set_role(
        self,
        admin_id: str,
        target_user_id: str,
        role: str,
    ) -> tuple[bool, str]:
        """
        管理员修改用户角色
        """
        # 验证管理员身份
        admin = await self.db.get(User, admin_id)
        if not admin or admin.role != UserRole.ADMIN.value:
            return False, "无权限操作"
        
        # 验证角色值
        if role not in [r.value for r in UserRole]:
            return False, f"无效的角色: {role}"
        
        # 获取目标用户
        target = await self.db.get(User, target_user_id)
        if not target:
            return False, "目标用户不存在"
        
        old_role = target.role
        target.role = role
        
        # 同时更新默认配额
        target.daily_quota = DEFAULT_QUOTAS.get(UserRole(role), 3)
        
        await self.db.commit()
        
        logger.info(
            "Admin set user role",
            admin_id=admin_id,
            target_user_id=target_user_id,
            old_role=old_role,
            new_role=role,
        )
        
        return True, f"已将用户角色从 {old_role} 改为 {role}"

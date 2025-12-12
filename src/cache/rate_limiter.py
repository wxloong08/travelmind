"""
API 限流器

支持:
- 用户级限流：防止单用户滥用
- 全局限流：保护第三方 API（如高德 3 QPS）
"""

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field

import structlog

from src.cache.redis_client import cache, is_redis_available

logger = structlog.get_logger()


@dataclass
class RateLimitConfig:
    """限流配置"""
    requests: int      # 最大请求数
    window: int        # 时间窗口（秒）
    
    @property
    def key_suffix(self) -> str:
        return f"{self.requests}_{self.window}"


class RateLimiter:
    """
    限流器
    
    使用滑动窗口算法
    """
    
    # 用户级限流配置
    USER_LIMITS = {
        "guest": RateLimitConfig(requests=10, window=60),       # 游客：10次/分钟
        "registered": RateLimitConfig(requests=30, window=60),  # 注册用户：30次/分钟
    }
    
    # 全局限流配置（保护第三方 API）
    GLOBAL_LIMITS = {
        "amap": RateLimitConfig(requests=3, window=1),          # 高德：3 QPS
        "bocha": RateLimitConfig(requests=10, window=1),        # 博查：10 QPS
    }
    
    def __init__(self):
        # 内存计数器（降级时使用）
        self._memory_counters: dict[str, list[float]] = defaultdict(list)
        # 全局锁（用于高德 API）
        self._global_locks: dict[str, asyncio.Semaphore] = {}
    
    async def check_user_limit(
        self,
        user_id: str,
        user_type: str = "registered",
    ) -> tuple[bool, dict]:
        """
        检查用户限流
        
        Args:
            user_id: 用户/游客 ID
            user_type: 用户类型 (guest/registered)
        
        Returns:
            (allowed, info): 是否允许，限流信息
        """
        config = self.USER_LIMITS.get(user_type, self.USER_LIMITS["registered"])
        key = f"user_limit:{user_id}:{config.key_suffix}"
        
        return await self._check_limit(key, config)
    
    async def check_global_limit(self, api_name: str) -> tuple[bool, dict]:
        """
        检查全局限流（保护第三方 API）
        
        Args:
            api_name: API 名称 (amap/bocha)
        
        Returns:
            (allowed, info): 是否允许，限流信息
        """
        config = self.GLOBAL_LIMITS.get(api_name)
        if not config:
            return True, {"allowed": True}
        
        key = f"global_limit:{api_name}"
        return await self._check_limit(key, config)
    
    async def acquire_global_lock(self, api_name: str, timeout: float = 5.0) -> bool:
        """
        获取全局锁（用于严格限制并发）
        
        Args:
            api_name: API 名称
            timeout: 超时时间（秒）
        
        Returns:
            是否获取成功
        """
        config = self.GLOBAL_LIMITS.get(api_name)
        if not config:
            return True
        
        # 获取或创建信号量
        if api_name not in self._global_locks:
            self._global_locks[api_name] = asyncio.Semaphore(config.requests)
        
        semaphore = self._global_locks[api_name]
        
        try:
            await asyncio.wait_for(semaphore.acquire(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            logger.warning("Global lock timeout", api=api_name)
            return False
    
    def release_global_lock(self, api_name: str) -> None:
        """释放全局锁"""
        if api_name in self._global_locks:
            self._global_locks[api_name].release()
    
    async def _check_limit(
        self,
        key: str,
        config: RateLimitConfig,
    ) -> tuple[bool, dict]:
        """
        检查限流（滑动窗口）
        
        使用 Redis 或内存实现
        """
        now = time.time()
        window_start = now - config.window
        
        if is_redis_available():
            return await self._check_limit_redis(key, config, now, window_start)
        else:
            return self._check_limit_memory(key, config, now, window_start)
    
    async def _check_limit_redis(
        self,
        key: str,
        config: RateLimitConfig,
        now: float,
        window_start: float,
    ) -> tuple[bool, dict]:
        """Redis 实现的滑动窗口"""
        try:
            from src.cache.redis_client import get_redis_client
            
            client = get_redis_client()
            if not client:
                return self._check_limit_memory(key, config, now, window_start)
            
            full_key = f"travelmind:rate:{key}"
            
            # 使用 Redis 事务
            async with client.pipeline(transaction=True) as pipe:
                # 删除窗口外的记录
                await pipe.zremrangebyscore(full_key, 0, window_start)
                # 获取当前窗口内的请求数
                await pipe.zcard(full_key)
                # 添加当前请求
                await pipe.zadd(full_key, {str(now): now})
                # 设置过期时间
                await pipe.expire(full_key, config.window * 2)
                
                results = await pipe.execute()
            
            current_count = results[1]  # zcard 结果
            
            allowed = current_count < config.requests
            remaining = max(0, config.requests - current_count - 1)
            
            return allowed, {
                "allowed": allowed,
                "limit": config.requests,
                "remaining": remaining,
                "reset_in": config.window,
            }
            
        except Exception as e:
            logger.warning("Redis rate limit check failed", error=str(e))
            return self._check_limit_memory(key, config, now, window_start)
    
    def _check_limit_memory(
        self,
        key: str,
        config: RateLimitConfig,
        now: float,
        window_start: float,
    ) -> tuple[bool, dict]:
        """内存实现的滑动窗口"""
        # 清理窗口外的记录
        self._memory_counters[key] = [
            t for t in self._memory_counters[key]
            if t > window_start
        ]
        
        current_count = len(self._memory_counters[key])
        
        if current_count >= config.requests:
            return False, {
                "allowed": False,
                "limit": config.requests,
                "remaining": 0,
                "reset_in": config.window,
            }
        
        # 记录当前请求
        self._memory_counters[key].append(now)
        
        return True, {
            "allowed": True,
            "limit": config.requests,
            "remaining": config.requests - current_count - 1,
            "reset_in": config.window,
        }
    
    def clear_memory(self) -> None:
        """清空内存计数器"""
        self._memory_counters.clear()


# 全局实例
rate_limiter = RateLimiter()

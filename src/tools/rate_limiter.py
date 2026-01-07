"""
高德地图 API 全局限流器

QPS=3 限制适用于所有用户的并发请求
"""

import asyncio
import time
from typing import Any, Callable, TypeVar

import structlog

logger = structlog.get_logger()

T = TypeVar("T")


class AmapRateLimiter:
    """
    全局限流器：确保高德 API 请求不超过 QPS=3
    
    使用令牌桶算法：
    - 每秒最多 3 个请求
    - 请求之间至少间隔 350ms
    """
    
    _instance = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._qps = 3
        self._min_interval = 1.0 / self._qps  # 0.333 秒
        self._last_request_time = 0.0
        self._semaphore = asyncio.Semaphore(self._qps)
        self._request_lock = asyncio.Lock()
        self._initialized = True
        
        logger.info("Amap rate limiter initialized", qps=self._qps)
    
    async def acquire(self):
        """
        获取请求许可
        
        确保：
        1. 同时进行的请求不超过 QPS
        2. 请求之间有足够的间隔
        """
        async with self._semaphore:
            async with self._request_lock:
                now = time.monotonic()
                elapsed = now - self._last_request_time
                
                if elapsed < self._min_interval:
                    wait_time = self._min_interval - elapsed
                    logger.debug("Rate limiting", wait_seconds=round(wait_time, 3))
                    await asyncio.sleep(wait_time)
                
                self._last_request_time = time.monotonic()
    
    async def execute(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """
        在限流控制下执行函数
        
        使用示例：
            limiter = get_amap_limiter()
            result = await limiter.execute(search_poi.ainvoke, {...})
        """
        await self.acquire()
        return await func(*args, **kwargs)


# 全局单例
_limiter: AmapRateLimiter | None = None


def get_amap_limiter() -> AmapRateLimiter:
    """获取全局限流器实例"""
    global _limiter
    if _limiter is None:
        _limiter = AmapRateLimiter()
    return _limiter


async def with_rate_limit(func: Callable[..., Any], *args, **kwargs) -> Any:
    """
    便捷函数：在限流控制下执行
    
    使用示例：
        result = await with_rate_limit(search_poi.ainvoke, {"keywords": "景点", ...})
    """
    limiter = get_amap_limiter()
    return await limiter.execute(func, *args, **kwargs)

"""
TravelMind 缓存模块

提供:
- Redis 连接管理
- 内存缓存降级
- API 限流器
"""

from src.cache.redis_client import (
    get_redis_client,
    init_redis,
    close_redis,
    is_redis_available,
)
from src.cache.rate_limiter import RateLimiter, rate_limiter
from src.cache.api_cache import APICache, api_cache

__all__ = [
    "get_redis_client",
    "init_redis",
    "close_redis",
    "is_redis_available",
    "RateLimiter",
    "rate_limiter",
    "APICache",
    "api_cache",
]

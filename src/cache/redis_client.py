"""
Redis 连接管理

支持优雅降级：无 Redis 时使用内存缓存
"""

from typing import Any

import structlog

from src.config import settings

logger = structlog.get_logger()

# 全局 Redis 客户端
_redis_client = None
_redis_available = False


async def init_redis() -> bool:
    """
    初始化 Redis 连接
    
    Returns:
        是否成功连接
    """
    global _redis_client, _redis_available
    
    if not settings.redis_url:
        logger.info("Redis not configured, using in-memory cache")
        _redis_available = False
        return False
    
    try:
        import redis.asyncio as redis
        
        _redis_client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5,
        )
        
        # 测试连接
        await _redis_client.ping()
        
        _redis_available = True
        logger.info("Redis connected", url=settings.redis_url.split("@")[-1])
        return True
        
    except ImportError:
        logger.warning("redis package not installed")
        _redis_available = False
        return False
    except Exception as e:
        logger.warning("Redis connection failed, using in-memory cache", error=str(e))
        _redis_available = False
        return False


async def close_redis() -> None:
    """关闭 Redis 连接"""
    global _redis_client, _redis_available
    
    if _redis_client:
        await _redis_client.close()
        logger.info("Redis connection closed")
    
    _redis_client = None
    _redis_available = False


def get_redis_client():
    """
    获取 Redis 客户端
    
    Returns:
        Redis 客户端或 None（未配置/连接失败时）
    """
    return _redis_client if _redis_available else None


def is_redis_available() -> bool:
    """检查 Redis 是否可用"""
    return _redis_available


class RedisOrMemory:
    """
    Redis 或内存缓存封装
    
    自动选择可用的存储后端
    """
    
    def __init__(self, prefix: str = "travelmind"):
        self.prefix = prefix
        self._memory_cache: dict[str, tuple[Any, float | None]] = {}
    
    def _key(self, key: str) -> str:
        """生成完整的 key"""
        return f"{self.prefix}:{key}"
    
    async def get(self, key: str) -> Any | None:
        """获取值"""
        full_key = self._key(key)
        
        if _redis_available and _redis_client:
            try:
                import json
                value = await _redis_client.get(full_key)
                if value:
                    return json.loads(value)
                return None
            except Exception as e:
                logger.warning("Redis get failed", key=key, error=str(e))
        
        # 内存回退
        import time
        cached = self._memory_cache.get(full_key)
        if cached:
            value, expire_at = cached
            if expire_at is None or time.time() < expire_at:
                return value
            # 已过期，删除
            del self._memory_cache[full_key]
        
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int | None = None,
    ) -> bool:
        """设置值"""
        full_key = self._key(key)
        
        if _redis_available and _redis_client:
            try:
                import json
                serialized = json.dumps(value, ensure_ascii=False)
                if ttl_seconds:
                    await _redis_client.setex(full_key, ttl_seconds, serialized)
                else:
                    await _redis_client.set(full_key, serialized)
                return True
            except Exception as e:
                logger.warning("Redis set failed", key=key, error=str(e))
        
        # 内存回退
        import time
        expire_at = time.time() + ttl_seconds if ttl_seconds else None
        self._memory_cache[full_key] = (value, expire_at)
        return True
    
    async def delete(self, key: str) -> bool:
        """删除值"""
        full_key = self._key(key)
        
        if _redis_available and _redis_client:
            try:
                await _redis_client.delete(full_key)
                return True
            except Exception as e:
                logger.warning("Redis delete failed", key=key, error=str(e))
        
        # 内存回退
        self._memory_cache.pop(full_key, None)
        return True
    
    async def incr(self, key: str, amount: int = 1) -> int:
        """增加计数"""
        full_key = self._key(key)
        
        if _redis_available and _redis_client:
            try:
                return await _redis_client.incrby(full_key, amount)
            except Exception as e:
                logger.warning("Redis incr failed", key=key, error=str(e))
        
        # 内存回退
        cached = self._memory_cache.get(full_key)
        if cached:
            value, expire_at = cached
            new_value = int(value or 0) + amount
        else:
            new_value = amount
            expire_at = None
        
        self._memory_cache[full_key] = (new_value, expire_at)
        return new_value
    
    async def expire(self, key: str, ttl_seconds: int) -> bool:
        """设置过期时间"""
        full_key = self._key(key)
        
        if _redis_available and _redis_client:
            try:
                await _redis_client.expire(full_key, ttl_seconds)
                return True
            except Exception as e:
                logger.warning("Redis expire failed", key=key, error=str(e))
        
        # 内存回退
        import time
        cached = self._memory_cache.get(full_key)
        if cached:
            value, _ = cached
            self._memory_cache[full_key] = (value, time.time() + ttl_seconds)
        return True
    
    def clear_memory_cache(self) -> None:
        """清空内存缓存"""
        self._memory_cache.clear()


# 全局实例
cache = RedisOrMemory()

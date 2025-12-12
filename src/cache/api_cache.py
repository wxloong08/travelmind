"""
API 结果缓存

缓存外部 API 调用结果，减少重复请求
"""

import hashlib
import json
from typing import Any

import structlog

from src.cache.redis_client import cache

logger = structlog.get_logger()


class APICache:
    """
    API 结果缓存
    
    支持缓存:
    - POI 搜索结果
    - 天气数据
    - 路线规划
    - 网络搜索结果
    """
    
    # 缓存 TTL 配置（秒）
    TTL_CONFIG = {
        "poi": 3600,           # POI 搜索：1 小时
        "weather": 1800,       # 天气：30 分钟
        "route": 7200,         # 路线：2 小时
        "search": 3600,        # 网络搜索：1 小时
        "default": 1800,       # 默认：30 分钟
    }
    
    @staticmethod
    def _generate_key(api_type: str, params: dict) -> str:
        """
        生成缓存 key
        
        基于参数生成唯一的 hash
        """
        # 排序参数保证一致性
        sorted_params = json.dumps(params, sort_keys=True, ensure_ascii=False)
        param_hash = hashlib.md5(sorted_params.encode()).hexdigest()[:16]
        return f"api_cache:{api_type}:{param_hash}"
    
    async def get(self, api_type: str, params: dict) -> Any | None:
        """
        获取缓存
        
        Args:
            api_type: API 类型 (poi/weather/route/search)
            params: 请求参数
        
        Returns:
            缓存的结果或 None
        """
        key = self._generate_key(api_type, params)
        
        try:
            result = await cache.get(key)
            if result:
                logger.debug("Cache hit", api_type=api_type, key=key[:30])
            return result
        except Exception as e:
            logger.warning("Cache get failed", error=str(e))
            return None
    
    async def set(
        self,
        api_type: str,
        params: dict,
        result: Any,
        ttl: int | None = None,
    ) -> bool:
        """
        设置缓存
        
        Args:
            api_type: API 类型
            params: 请求参数
            result: 响应结果
            ttl: 自定义 TTL（秒）
        
        Returns:
            是否成功
        """
        key = self._generate_key(api_type, params)
        ttl = ttl or self.TTL_CONFIG.get(api_type, self.TTL_CONFIG["default"])
        
        try:
            await cache.set(key, result, ttl_seconds=ttl)
            logger.debug("Cache set", api_type=api_type, key=key[:30], ttl=ttl)
            return True
        except Exception as e:
            logger.warning("Cache set failed", error=str(e))
            return False
    
    async def invalidate(self, api_type: str, params: dict) -> bool:
        """
        使缓存失效
        
        Args:
            api_type: API 类型
            params: 请求参数
        
        Returns:
            是否成功
        """
        key = self._generate_key(api_type, params)
        
        try:
            await cache.delete(key)
            logger.debug("Cache invalidated", api_type=api_type, key=key[:30])
            return True
        except Exception as e:
            logger.warning("Cache invalidate failed", error=str(e))
            return False
    
    async def get_or_fetch(
        self,
        api_type: str,
        params: dict,
        fetch_func,
        ttl: int | None = None,
    ) -> Any:
        """
        获取缓存或执行查询
        
        如果缓存存在则返回缓存，否则执行 fetch_func 并缓存结果
        
        Args:
            api_type: API 类型
            params: 请求参数
            fetch_func: 查询函数（异步）
            ttl: 自定义 TTL
        
        Returns:
            查询结果
        """
        # 尝试获取缓存
        cached = await self.get(api_type, params)
        if cached is not None:
            return cached
        
        # 执行查询
        result = await fetch_func()
        
        # 缓存结果（忽略空结果）
        if result:
            await self.set(api_type, params, result, ttl)
        
        return result


# 全局实例
api_cache = APICache()

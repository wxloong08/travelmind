"""
MCP (Model Context Protocol) 客户端配置

连接高德地图 MCP Server 和博查搜索 MCP Server
使用 langchain-mcp-adapters 将 MCP 工具转换为 LangChain 工具
"""

import os
import asyncio
from typing import Any
import structlog

logger = structlog.get_logger()

# MCP 服务器配置
def get_mcp_config() -> dict[str, dict[str, Any]]:
    """获取 MCP 服务器配置"""
    config = {}
    
    # 高德地图 MCP
    amap_key = os.getenv("AMAP_API_KEY")
    if amap_key:
        config["amap"] = {
            "command": "npx",
            "args": ["-y", "@amap/amap-maps-mcp-server"],
            "env": {"AMAP_MAPS_API_KEY": amap_key},
            "transport": "stdio",
        }
        logger.info("Configured Amap MCP Server")
    else:
        logger.warning("AMAP_API_KEY not set, Amap MCP disabled")
    
    # 博查搜索 MCP
    bocha_key = os.getenv("BOCHA_API_KEY")
    if bocha_key:
        config["bocha"] = {
            "command": "npx",
            "args": ["-y", "bocha-search-mcp"],
            "env": {"BOCHA_API_KEY": bocha_key},
            "transport": "stdio",
        }
        logger.info("Configured Bocha MCP Server")
    else:
        logger.warning("BOCHA_API_KEY not set, Bocha MCP disabled")
    
    return config


async def get_mcp_tools() -> list:
    """
    获取所有已配置的 MCP 工具
    
    返回 LangChain 兼容的工具列表，可直接绑定到 LLM
    """
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
    except ImportError:
        logger.error("langchain-mcp-adapters not installed")
        return []
    
    config = get_mcp_config()
    if not config:
        logger.warning("No MCP servers configured")
        return []
    
    try:
        client = MultiServerMCPClient(config)
        tools = await client.get_tools()
        logger.info(f"Loaded {len(tools)} MCP tools", 
                   tool_names=[t.name for t in tools])
        return tools
    except Exception as e:
        logger.error(f"Failed to get MCP tools: {e}")
        return []


# 单例模式缓存 MCP 工具
_mcp_tools_cache: list | None = None
_mcp_tools_lock = asyncio.Lock()


async def get_cached_mcp_tools() -> list:
    """获取缓存的 MCP 工具（避免重复初始化）"""
    global _mcp_tools_cache
    
    async with _mcp_tools_lock:
        if _mcp_tools_cache is None:
            _mcp_tools_cache = await get_mcp_tools()
        return _mcp_tools_cache


def reset_mcp_cache():
    """重置 MCP 工具缓存（用于配置变更后）"""
    global _mcp_tools_cache
    _mcp_tools_cache = None
    logger.info("MCP tools cache reset")

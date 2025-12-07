"""API 模块"""

from src.api.routes import router
from src.api.schemas import (
    BaseResponse,
    ChatRequest,
    ChatResponse,
    ErrorResponse,
    HealthResponse,
    POIItem,
    POISearchRequest,
    POISearchResponse,
    RouteRequest,
    RouteResponse,
    SearchResultItem,
    WeatherRequest,
    WeatherResponse,
    WebSearchRequest,
    WebSearchResponse,
)

__all__ = [
    # 路由
    "router",
    # Schema
    "BaseResponse",
    "ErrorResponse",
    "ChatRequest",
    "ChatResponse",
    "POISearchRequest",
    "POISearchResponse",
    "POIItem",
    "WeatherRequest",
    "WeatherResponse",
    "RouteRequest",
    "RouteResponse",
    "WebSearchRequest",
    "WebSearchResponse",
    "SearchResultItem",
    "HealthResponse",
]

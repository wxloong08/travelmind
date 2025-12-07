"""
配置和 Schema 测试
"""

import pytest
from pydantic import ValidationError


class TestSettings:
    """配置类测试"""

    def test_default_settings(self, mock_settings):
        """测试默认配置值"""
        assert mock_settings.environment == "development"
        assert mock_settings.debug is True
        assert mock_settings.api_port == 8000

    def test_is_production(self, mock_settings):
        """测试生产环境判断"""
        assert mock_settings.is_production is False

    def test_langfuse_enabled(self, mock_settings):
        """测试 Langfuse 启用状态"""
        assert mock_settings.langfuse_enabled is False


class TestChatRequest:
    """聊天请求 Schema 测试"""

    def test_valid_chat_request(self):
        """测试有效的聊天请求"""
        from src.api.schemas import ChatRequest

        request = ChatRequest(message="你好")
        assert request.message == "你好"
        assert request.session_id is None

    def test_chat_request_with_session(self):
        """测试带会话 ID 的聊天请求"""
        from src.api.schemas import ChatRequest

        request = ChatRequest(message="你好", session_id="session_123")
        assert request.session_id == "session_123"

    def test_empty_message_invalid(self):
        """测试空消息无效"""
        from src.api.schemas import ChatRequest

        with pytest.raises(ValidationError):
            ChatRequest(message="")


class TestPOISearchRequest:
    """POI 搜索请求 Schema 测试"""

    def test_valid_poi_request(self):
        """测试有效的 POI 搜索请求"""
        from src.api.schemas import POISearchRequest

        request = POISearchRequest(keywords="西湖", city="杭州")
        assert request.keywords == "西湖"
        assert request.city == "杭州"
        assert request.page_size == 10

    def test_poi_type_optional(self):
        """测试 POI 类型可选"""
        from src.api.schemas import POISearchRequest

        request = POISearchRequest(
            keywords="火锅",
            city="成都",
            poi_type="restaurant",
        )
        assert request.poi_type == "restaurant"

    def test_page_size_range(self):
        """测试页面大小范围"""
        from src.api.schemas import POISearchRequest

        with pytest.raises(ValidationError):
            POISearchRequest(keywords="test", city="test", page_size=0)

        with pytest.raises(ValidationError):
            POISearchRequest(keywords="test", city="test", page_size=100)


class TestWeatherRequest:
    """天气请求 Schema 测试"""

    def test_valid_weather_request(self):
        """测试有效的天气请求"""
        from src.api.schemas import WeatherRequest

        request = WeatherRequest(city="杭州")
        assert request.city == "杭州"
        assert request.forecast is False

    def test_forecast_flag(self):
        """测试预报标志"""
        from src.api.schemas import WeatherRequest

        request = WeatherRequest(city="北京", forecast=True)
        assert request.forecast is True


class TestRouteRequest:
    """路线请求 Schema 测试"""

    def test_valid_route_request(self):
        """测试有效的路线请求"""
        from src.api.schemas import RouteRequest

        request = RouteRequest(
            origin_lng=120.15,
            origin_lat=30.25,
            dest_lng=120.20,
            dest_lat=30.30,
        )
        assert request.mode == "driving"

    def test_route_modes(self):
        """测试出行方式"""
        from src.api.schemas import RouteRequest

        for mode in ["driving", "walking", "transit"]:
            request = RouteRequest(
                origin_lng=120.15,
                origin_lat=30.25,
                dest_lng=120.20,
                dest_lat=30.30,
                mode=mode,
            )
            assert request.mode == mode


class TestResponseModels:
    """响应模型测试"""

    def test_base_response(self):
        """测试基础响应"""
        from src.api.schemas import BaseResponse

        response = BaseResponse()
        assert response.success is True
        assert response.message == "OK"

    def test_error_response(self):
        """测试错误响应"""
        from src.api.schemas import ErrorResponse

        response = ErrorResponse(
            message="Something went wrong",
            error_code="E001",
            detail="Detailed error info",
        )
        assert response.success is False
        assert response.error_code == "E001"

    def test_health_response(self):
        """测试健康检查响应"""
        from src.api.schemas import HealthResponse

        response = HealthResponse(
            environment="development",
            services={"llm": "configured"},
        )
        assert response.status == "healthy"
        assert response.services["llm"] == "configured"

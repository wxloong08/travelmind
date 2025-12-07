"""
API 端点测试

测试 FastAPI 路由和响应
"""

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """健康检查端点测试"""

    def test_health_check(self, client: TestClient):
        """测试健康检查返回正确状态"""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "environment" in data
        assert "services" in data

    def test_health_check_services(self, client: TestClient):
        """测试健康检查包含服务状态"""
        response = client.get("/api/v1/health")
        data = response.json()

        services = data["services"]
        assert "llm" in services
        assert "amap" in services
        assert "search" in services


class TestRootEndpoint:
    """根路径端点测试"""

    def test_root_returns_api_info(self, client: TestClient):
        """测试根路径返回 API 信息"""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "TravelMind API"
        assert "version" in data
        assert "docs" in data


class TestChatEndpoint:
    """聊天端点测试"""

    def test_chat_requires_message(self, client: TestClient):
        """测试聊天需要消息字段"""
        response = client.post("/api/v1/chat", json={})
        assert response.status_code == 422  # Validation error

    def test_chat_message_min_length(self, client: TestClient):
        """测试消息最小长度验证"""
        response = client.post("/api/v1/chat", json={"message": ""})
        assert response.status_code == 422


class TestPOISearchEndpoint:
    """POI 搜索端点测试"""

    def test_poi_search_requires_keywords(self, client: TestClient):
        """测试 POI 搜索需要关键词"""
        response = client.post(
            "/api/v1/tools/poi/search",
            json={"city": "杭州"},
        )
        assert response.status_code == 422

    def test_poi_search_requires_city(self, client: TestClient):
        """测试 POI 搜索需要城市"""
        response = client.post(
            "/api/v1/tools/poi/search",
            json={"keywords": "西湖"},
        )
        assert response.status_code == 422

    def test_poi_search_page_size_validation(self, client: TestClient):
        """测试页面大小验证"""
        response = client.post(
            "/api/v1/tools/poi/search",
            json={"keywords": "西湖", "city": "杭州", "page_size": 100},
        )
        assert response.status_code == 422


class TestWeatherEndpoint:
    """天气端点测试"""

    def test_weather_requires_city(self, client: TestClient):
        """测试天气查询需要城市"""
        response = client.post("/api/v1/tools/weather", json={})
        assert response.status_code == 422


class TestRouteEndpoint:
    """路线规划端点测试"""

    def test_route_requires_coordinates(self, client: TestClient):
        """测试路线规划需要坐标"""
        response = client.post("/api/v1/tools/route", json={})
        assert response.status_code == 422

    def test_route_validates_mode(self, client: TestClient):
        """测试出行方式验证"""
        response = client.post(
            "/api/v1/tools/route",
            json={
                "origin_lng": 120.15,
                "origin_lat": 30.25,
                "dest_lng": 120.20,
                "dest_lat": 30.30,
                "mode": "driving",
            },
        )
        # 应该通过验证（但可能因为没有真实 API 而失败）
        assert response.status_code in [200, 500]


class TestWebSearchEndpoint:
    """网络搜索端点测试"""

    def test_search_requires_query(self, client: TestClient):
        """测试搜索需要查询词"""
        response = client.post("/api/v1/tools/search", json={})
        assert response.status_code == 422

    def test_search_count_validation(self, client: TestClient):
        """测试结果数量验证"""
        response = client.post(
            "/api/v1/tools/search",
            json={"query": "杭州旅游", "count": 100},
        )
        assert response.status_code == 422

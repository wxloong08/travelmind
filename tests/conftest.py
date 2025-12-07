"""
Pytest 配置和 Fixtures

提供测试所需的共享配置和模拟对象
"""

import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

# 设置测试环境变量
import os

os.environ["ENVIRONMENT"] = "development"
os.environ["DEBUG"] = "true"
os.environ["DASHSCOPE_API_KEY"] = "test-api-key"
os.environ["AMAP_API_KEY"] = "test-amap-key"
os.environ["BOCHA_API_KEY"] = "test-bocha-key"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings():
    """模拟配置"""
    from src.config import Settings

    return Settings(
        environment="development",
        debug=True,
        dashscope_api_key="test-api-key",
        amap_api_key="test-amap-key",
        bocha_api_key="test-bocha-key",
    )


@pytest.fixture
def app():
    """创建测试应用"""
    from src.main import app

    return app


@pytest.fixture
def client(app) -> Generator[TestClient, None, None]:
    """同步测试客户端"""
    with TestClient(app) as c:
        yield c


@pytest.fixture
async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
    """异步测试客户端"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_llm_response():
    """模拟 LLM 响应"""
    from src.llm import LLMResponse

    return LLMResponse(
        content="这是一个测试响应",
        tool_calls=None,
        usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        model="qwen-turbo",
    )


@pytest.fixture
def mock_qwen_provider(mock_llm_response):
    """模拟通义千问 Provider"""
    with patch("src.llm.qwen.QwenProvider") as mock:
        instance = mock.return_value
        instance.chat = AsyncMock(return_value=mock_llm_response)
        instance.embed = AsyncMock(return_value=[[0.1] * 1536])
        yield instance


@pytest.fixture
def mock_amap_client():
    """模拟高德地图客户端"""
    with patch("src.tools.amap.AmapClient") as mock:
        instance = mock.return_value
        instance.search_poi = AsyncMock(
            return_value=[
                MagicMock(
                    id="poi_1",
                    name="西湖",
                    type="风景名胜",
                    type_code="110000",
                    address="杭州市西湖区",
                    location=(120.15, 30.25),
                    rating=4.8,
                    cost=None,
                    tel="0571-12345678",
                    city="杭州",
                    district="西湖区",
                )
            ]
        )
        instance.weather = AsyncMock(
            return_value={
                "city": "杭州",
                "weather": "晴",
                "temperature": "25",
                "humidity": "60",
            }
        )
        yield instance


@pytest.fixture
def mock_bocha_client():
    """模拟博查搜索客户端"""
    with patch("src.tools.search.BochaClient") as mock:
        instance = mock.return_value
        instance.search = AsyncMock(
            return_value=[
                MagicMock(
                    title="杭州旅游攻略",
                    url="https://example.com/hangzhou",
                    snippet="杭州是一座美丽的城市...",
                    source="旅游网",
                    published_date="2024-01-01",
                )
            ]
        )
        yield instance


@pytest.fixture
def sample_travel_preference():
    """示例旅游偏好"""
    return {
        "destination": "杭州",
        "start_date": "2024-05-01",
        "end_date": "2024-05-03",
        "budget": "3000",
        "travel_style": "休闲",
        "interests": ["自然风光", "历史文化"],
        "party_size": 2,
    }


@pytest.fixture
def sample_poi_data():
    """示例 POI 数据"""
    return [
        {
            "name": "西湖",
            "address": "杭州市西湖区",
            "type": "风景名胜",
            "rating": 4.8,
            "cost": None,
            "location": {"lng": 120.15, "lat": 30.25},
        },
        {
            "name": "灵隐寺",
            "address": "杭州市西湖区灵隐路",
            "type": "风景名胜",
            "rating": 4.7,
            "cost": 75.0,
            "location": {"lng": 120.10, "lat": 30.24},
        },
    ]

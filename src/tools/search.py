"""
博查搜索 API 工具

专为 AI 应用设计的中文搜索 API
文档: https://open.bochaai.com/
"""

from dataclasses import dataclass
from typing import Any

import httpx
import structlog

from src.config import settings

logger = structlog.get_logger()

# API 基础 URL
BOCHA_BASE_URL = "https://api.bochaai.com/v1"


@dataclass
class SearchResult:
    """搜索结果数据类"""

    title: str
    url: str
    snippet: str
    source: str | None = None
    published_date: str | None = None
    site_icon: str | None = None    # 网站图标
    thumbnail: str | None = None    # 缩略图


class BochaClient:
    """博查搜索 API 客户端"""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.bocha_api_key
        if not self.api_key:
            raise ValueError(
                "Bocha API key is required. Set BOCHA_API_KEY environment variable."
            )
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

    async def close(self) -> None:
        """关闭客户端"""
        await self.client.aclose()

    async def __aenter__(self) -> "BochaClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def search(
        self,
        query: str,
        count: int = 10,
        freshness: str | None = None,
        summary: bool = True,
    ) -> list[SearchResult]:
        """
        网页搜索

        Args:
            query: 搜索关键词
            count: 返回结果数量，最大 50
            freshness: 时效性过滤 (day/week/month/year)
            summary: 是否返回 AI 摘要

        Returns:
            搜索结果列表
        """
        logger.debug("Bocha search request", query=query, count=count)

        payload: dict[str, Any] = {
            "query": query,
            "count": min(count, 50),
            "summary": summary,
        }

        if freshness:
            payload["freshness"] = freshness

        try:
            response = await self.client.post(
                f"{BOCHA_BASE_URL}/web-search",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        except httpx.HTTPStatusError as e:
            logger.error(
                "Bocha API HTTP error",
                status_code=e.response.status_code,
                detail=e.response.text,
            )
            raise
        except Exception as e:
            logger.error("Bocha API error", error=str(e))
            raise

        results = []
        web_pages = data.get("data", {}).get("webPages")
        if web_pages and "value" in web_pages:
            for item in web_pages.get("value", []):
                results.append(
                    SearchResult(
                        title=item.get("name", ""),
                        url=item.get("url", ""),
                        snippet=item.get("snippet", ""),
                        source=item.get("siteName"),
                        published_date=item.get("datePublished"),
                        site_icon=item.get("siteIcon"),
                        thumbnail=item.get("thumbnailUrl"),
                    )
                )

        # 解析图片结果
        images = []
        images_data = data.get("data", {}).get("images")
        if images_data and "value" in images_data:
            for img in images_data.get("value", []):
                images.append({
                    "url": img.get("contentUrl"),
                    "thumbnail": img.get("thumbnailUrl"),
                    "name": img.get("name"),
                })

        logger.info("Bocha search response", query=query, result_count=len(results), image_count=len(images))
        return results, images

    async def news_search(
        self,
        query: str,
        count: int = 10,
        freshness: str = "week",
    ) -> list[SearchResult]:
        """
        新闻搜索

        Args:
            query: 搜索关键词
            count: 返回结果数量
            freshness: 时效性过滤

        Returns:
            新闻结果列表
        """
        logger.debug("Bocha news search", query=query)

        payload = {
            "query": query,
            "count": min(count, 50),
            "freshness": freshness,
        }

        try:
            response = await self.client.post(
                f"{BOCHA_BASE_URL}/web-news",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        except httpx.HTTPStatusError as e:
            logger.error("Bocha news API error", status_code=e.response.status_code)
            raise

        results = []
        for item in data.get("data", {}).get("news", {}).get("value", []):
            results.append(
                SearchResult(
                    title=item.get("name", ""),
                    url=item.get("url", ""),
                    snippet=item.get("description", ""),
                    source=item.get("provider", [{}])[0].get("name"),
                    published_date=item.get("datePublished"),
                )
            )

        logger.info("Bocha news search response", query=query, result_count=len(results))
        return results


# 创建全局客户端实例（懒加载）
_bocha_client: BochaClient | None = None


def get_bocha_client() -> BochaClient:
    """获取博查搜索客户端单例"""
    global _bocha_client
    if _bocha_client is None:
        _bocha_client = BochaClient()
    return _bocha_client

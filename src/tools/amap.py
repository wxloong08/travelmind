"""
高德地图 API 工具

提供 POI 搜索、路线规划、地理编码等功能
文档: https://lbs.amap.com/api/webservice/summary
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any

import httpx
import structlog

from src.config import settings

logger = structlog.get_logger()

# API 基础 URL
AMAP_BASE_URL = "https://restapi.amap.com/v3"


class POIType(str, Enum):
    """POI 类型枚举"""

    SCENIC = "110000"  # 风景名胜
    HOTEL = "100100"  # 宾馆酒店（星级酒店、连锁酒店等，不含公寓民宿）
    RESTAURANT = "050000"  # 餐饮服务
    SHOPPING = "060000"  # 购物服务
    TRANSPORT = "150000"  # 交通设施
    ENTERTAINMENT = "080000"  # 体育休闲


@dataclass
class POI:
    """POI 数据类"""

    id: str
    name: str
    type: str
    type_code: str
    address: str
    location: tuple[float, float]  # (经度, 纬度)
    tel: str | None = None
    rating: float | None = None
    cost: float | None = None  # 人均消费
    photos: list[str] | None = None
    business_area: str | None = None
    city: str | None = None
    district: str | None = None


@dataclass
class RouteInfo:
    """路线信息数据类"""

    distance: int  # 距离（米）
    duration: int  # 时间（秒）
    steps: list[dict[str, Any]]
    polyline: str | None = None


class AmapClient:
    """高德地图 API 客户端"""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.amap_api_key
        if not self.api_key:
            raise ValueError(
                "Amap API key is required. Set AMAP_API_KEY environment variable."
            )
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self) -> None:
        """关闭客户端"""
        await self.client.aclose()

    async def __aenter__(self) -> "AmapClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def _request(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        """发送 API 请求"""
        params["key"] = self.api_key
        params["output"] = "json"

        url = f"{AMAP_BASE_URL}/{endpoint}"

        logger.debug("Amap API request", endpoint=endpoint, params={k: v for k, v in params.items() if k != "key"})

        response = await self.client.get(url, params=params)
        response.raise_for_status()

        data = response.json()

        if data.get("status") != "1":
            error_info = data.get("info", "Unknown error")
            logger.error("Amap API error", info=error_info, infocode=data.get("infocode"))
            raise Exception(f"Amap API error: {error_info}")

        return data

    async def search_poi(
        self,
        keywords: str,
        city: str,
        types: str | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_rule: str = "distance",
    ) -> list[POI]:
        """
        POI 关键字搜索

        Args:
            keywords: 搜索关键字
            city: 城市名称或城市编码
            types: POI 类型代码，多个用 | 分隔
            page: 页码，从 1 开始
            page_size: 每页数量，最大 25
            sort_rule: 排序规则 (distance/weight)

        Returns:
            POI 列表
        """
        params: dict[str, Any] = {
            "keywords": keywords,
            "city": city,
            "citylimit": "true",
            "page": page,
            "offset": min(page_size, 25),
            "sortrule": sort_rule,
            "extensions": "all",
        }

        if types:
            params["types"] = types

        data = await self._request("place/text", params)

        pois = []
        for poi_data in data.get("pois", []):
            location = poi_data.get("location", "0,0").split(",")
            pois.append(
                POI(
                    id=poi_data.get("id", ""),
                    name=poi_data.get("name", ""),
                    type=poi_data.get("type", ""),
                    type_code=poi_data.get("typecode", ""),
                    address=poi_data.get("address", "") or "",
                    location=(float(location[0]), float(location[1])),
                    tel=poi_data.get("tel") or None,
                    rating=float(poi_data["biz_ext"]["rating"])
                    if poi_data.get("biz_ext", {}).get("rating")
                    else None,
                    cost=float(poi_data["biz_ext"]["cost"])
                    if poi_data.get("biz_ext", {}).get("cost")
                    else None,
                    photos=[p["url"] for p in poi_data.get("photos", [])][:3],
                    business_area=poi_data.get("business_area") or None,
                    city=poi_data.get("cityname") or None,
                    district=poi_data.get("adname") or None,
                )
            )

        logger.info("Amap POI search", keywords=keywords, city=city, result_count=len(pois))
        return pois

    async def search_around(
        self,
        location: tuple[float, float],
        keywords: str | None = None,
        types: str | None = None,
        radius: int = 1000,
        page: int = 1,
        page_size: int = 20,
    ) -> list[POI]:
        """
        周边 POI 搜索

        Args:
            location: 中心点坐标 (经度, 纬度)
            keywords: 搜索关键字
            types: POI 类型代码
            radius: 搜索半径（米），最大 50000
            page: 页码
            page_size: 每页数量

        Returns:
            POI 列表
        """
        params: dict[str, Any] = {
            "location": f"{location[0]},{location[1]}",
            "radius": min(radius, 50000),
            "page": page,
            "offset": min(page_size, 25),
            "extensions": "all",
        }

        if keywords:
            params["keywords"] = keywords
        if types:
            params["types"] = types

        data = await self._request("place/around", params)

        pois = []
        for poi_data in data.get("pois", []):
            loc = poi_data.get("location", "0,0").split(",")
            pois.append(
                POI(
                    id=poi_data.get("id", ""),
                    name=poi_data.get("name", ""),
                    type=poi_data.get("type", ""),
                    type_code=poi_data.get("typecode", ""),
                    address=poi_data.get("address", "") or "",
                    location=(float(loc[0]), float(loc[1])),
                    tel=poi_data.get("tel") or None,
                    rating=float(poi_data["biz_ext"]["rating"])
                    if poi_data.get("biz_ext", {}).get("rating")
                    else None,
                    cost=float(poi_data["biz_ext"]["cost"])
                    if poi_data.get("biz_ext", {}).get("cost")
                    else None,
                    city=poi_data.get("cityname") or None,
                    district=poi_data.get("adname") or None,
                )
            )

        logger.info("Amap around search", location=location, result_count=len(pois))
        return pois

    async def geocode(self, address: str, city: str | None = None) -> tuple[float, float] | None:
        """
        地理编码 - 地址转坐标

        Args:
            address: 地址字符串
            city: 城市名称

        Returns:
            坐标元组 (经度, 纬度) 或 None
        """
        params: dict[str, Any] = {"address": address}
        if city:
            params["city"] = city

        data = await self._request("geocode/geo", params)

        geocodes = data.get("geocodes", [])
        if not geocodes:
            return None

        location = geocodes[0].get("location", "").split(",")
        if len(location) != 2:
            return None

        return (float(location[0]), float(location[1]))

    async def reverse_geocode(
        self, location: tuple[float, float]
    ) -> dict[str, Any] | None:
        """
        逆地理编码 - 坐标转地址

        Args:
            location: 坐标 (经度, 纬度)

        Returns:
            地址信息字典
        """
        params = {
            "location": f"{location[0]},{location[1]}",
            "extensions": "all",
        }

        data = await self._request("geocode/regeo", params)

        regeocode = data.get("regeocode")
        if not regeocode:
            return None

        return {
            "formatted_address": regeocode.get("formatted_address"),
            "province": regeocode.get("addressComponent", {}).get("province"),
            "city": regeocode.get("addressComponent", {}).get("city"),
            "district": regeocode.get("addressComponent", {}).get("district"),
            "township": regeocode.get("addressComponent", {}).get("township"),
        }

    async def route_planning(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
        mode: str = "driving",
    ) -> RouteInfo | None:
        """
        路线规划

        Args:
            origin: 起点坐标 (经度, 纬度)
            destination: 终点坐标 (经度, 纬度)
            mode: 出行方式 (driving/walking/transit)

        Returns:
            路线信息
        """
        endpoint_map = {
            "driving": "direction/driving",
            "walking": "direction/walking",
            "transit": "direction/transit/integrated",
        }

        endpoint = endpoint_map.get(mode, "direction/driving")

        params = {
            "origin": f"{origin[0]},{origin[1]}",
            "destination": f"{destination[0]},{destination[1]}",
            "extensions": "all",
        }

        if mode == "transit":
            # 公交需要指定城市
            params["city"] = "全国"

        data = await self._request(endpoint, params)

        route = data.get("route")
        if not route:
            return None

        if mode == "transit":
            # 公交路线解析
            transits = route.get("transits", [])
            if not transits:
                return None
            first_route = transits[0]
            return RouteInfo(
                distance=int(first_route.get("distance", 0)),
                duration=int(first_route.get("duration", 0)),
                steps=[
                    {"instruction": seg.get("instruction", "")}
                    for seg in first_route.get("segments", [])
                ],
            )
        else:
            # 驾车/步行路线解析
            paths = route.get("paths", [])
            if not paths:
                return None
            first_path = paths[0]
            return RouteInfo(
                distance=int(first_path.get("distance", 0)),
                duration=int(first_path.get("duration", 0)),
                steps=[
                    {"instruction": step.get("instruction", "")}
                    for step in first_path.get("steps", [])
                ],
                polyline=first_path.get("polyline"),
            )

    async def weather(self, city: str, extensions: str = "base") -> dict[str, Any]:
        """
        天气查询

        Args:
            city: 城市名称或 adcode
            extensions: base(实况)/all(预报)

        Returns:
            天气信息
        """
        params = {
            "city": city,
            "extensions": extensions,
        }

        data = await self._request("weather/weatherInfo", params)

        if extensions == "base":
            lives = data.get("lives", [])
            if lives:
                return lives[0]
        else:
            forecasts = data.get("forecasts", [])
            if forecasts:
                return forecasts[0]

        return {}


# 创建全局客户端实例（懒加载）
_amap_client: AmapClient | None = None


def get_amap_client() -> AmapClient:
    """获取高德地图客户端单例"""
    global _amap_client
    if _amap_client is None:
        _amap_client = AmapClient()
    return _amap_client

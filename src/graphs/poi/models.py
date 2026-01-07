"""
POI 数据模型

定义增强版 POI 结构和距离矩阵
"""

from dataclasses import dataclass, field
from typing import Any

from src.graphs.utils.haversine import haversine


@dataclass
class EnhancedPOI:
    """
    增强版 POI，包含坐标和距离信息
    
    用于 POI-based 行程规划，确保每个地点都有真实坐标
    """
    id: str                           # 唯一标识
    name: str                         # POI 名称
    category: str                     # "景点" | "酒店" | "餐厅" | "交通枢纽"
    lat: float                        # 纬度
    lng: float                        # 经度
    city: str                         # 所属城市
    district: str | None = None       # 所属区
    address: str | None = None        # 详细地址
    rating: float | None = None       # 评分
    price: int | None = None          # 价格（酒店/餐厅）
    duration_minutes: int = 120       # 建议游览时长（分钟）
    opening_hours: str | None = None  # 开放时间
    tags: list[str] = field(default_factory=list)  # 标签
    
    def distance_to(self, other: "EnhancedPOI") -> float:
        """计算到另一个 POI 的距离（km）"""
        return haversine(self.lat, self.lng, other.lat, other.lng)
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "lat": self.lat,
            "lng": self.lng,
            "city": self.city,
            "district": self.district,
            "address": self.address,
            "rating": self.rating,
            "price": self.price,
            "duration_minutes": self.duration_minutes,
            "opening_hours": self.opening_hours,
            "tags": self.tags,
        }
    
    @classmethod
    def from_amap_poi(cls, poi: dict, category: str = "景点") -> "EnhancedPOI":
        """从高德 POI 数据创建"""
        location = poi.get("location", {})
        if isinstance(location, str) and "," in location:
            lng, lat = location.split(",")
            lat, lng = float(lat), float(lng)
        elif isinstance(location, dict):
            lat = float(location.get("lat", 0))
            lng = float(location.get("lng", 0))
        else:
            lat, lng = 0.0, 0.0
        
        return cls(
            id=poi.get("id", poi.get("name", "")),
            name=poi.get("name", ""),
            category=category,
            lat=lat,
            lng=lng,
            city=poi.get("cityname", poi.get("city", "")),
            district=poi.get("adname", poi.get("district")),
            address=poi.get("address", ""),
            rating=float(poi.get("rating", 0)) if poi.get("rating") else None,
            price=int(poi.get("cost", 0)) if poi.get("cost") else None,
            tags=poi.get("type", "").split(";") if poi.get("type") else [],
        )


class POIDistanceMatrix:
    """
    POI 之间的距离矩阵
    
    预计算距离，避免重复调用
    """
    
    def __init__(self, pois: list[EnhancedPOI] | None = None):
        self.pois: dict[str, EnhancedPOI] = {}
        self._cache: dict[tuple[str, str], float] = {}
        
        if pois:
            for poi in pois:
                self.add_poi(poi)
    
    def add_poi(self, poi: EnhancedPOI) -> None:
        """添加 POI"""
        self.pois[poi.id] = poi
    
    def get_distance(self, poi_id_1: str, poi_id_2: str) -> float | None:
        """
        获取两个 POI 之间的距离（km）
        
        Returns:
            距离（公里），如果任一 POI 不存在则返回 None
        """
        if poi_id_1 == poi_id_2:
            return 0.0
        
        key = tuple(sorted([poi_id_1, poi_id_2]))
        
        if key not in self._cache:
            p1 = self.pois.get(poi_id_1)
            p2 = self.pois.get(poi_id_2)
            
            if not p1 or not p2:
                return None
            
            self._cache[key] = p1.distance_to(p2)
        
        return self._cache[key]
    
    def get_nearby(
        self,
        poi_id: str,
        max_km: float = 15.0,
        category: str | None = None,
    ) -> list[tuple[str, float]]:
        """
        获取指定 POI 附近的 POI（按距离排序）
        
        Args:
            poi_id: 起始 POI ID
            max_km: 最大距离（公里）
            category: 可选，筛选特定类别
        
        Returns:
            [(poi_id, distance_km), ...] 按距离升序排列
        """
        nearby = []
        
        for other_id, other_poi in self.pois.items():
            if other_id == poi_id:
                continue
            
            if category and other_poi.category != category:
                continue
            
            dist = self.get_distance(poi_id, other_id)
            if dist is not None and dist <= max_km:
                nearby.append((other_id, dist))
        
        return sorted(nearby, key=lambda x: x[1])
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典（用于存储到 state）"""
        return {
            "pois": {k: v.to_dict() for k, v in self.pois.items()},
            "cache": {f"{k[0]}|{k[1]}": v for k, v in self._cache.items()},
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "POIDistanceMatrix":
        """从字典创建"""
        matrix = cls()
        
        for poi_id, poi_data in data.get("pois", {}).items():
            matrix.pois[poi_id] = EnhancedPOI(**poi_data)
        
        for key_str, dist in data.get("cache", {}).items():
            id1, id2 = key_str.split("|")
            matrix._cache[tuple(sorted([id1, id2]))] = dist
        
        return matrix

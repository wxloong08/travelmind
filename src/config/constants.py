"""
TravelMind 常量配置

将散落在代码中的 Magic Numbers 统一管理
遵循 Twelve-Factor App 原则：配置与代码分离
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class HttpConfig:
    """HTTP 请求配置"""
    DEFAULT_TIMEOUT: float = 30.0
    SHORT_TIMEOUT: float = 10.0
    LONG_TIMEOUT: float = 60.0
    
    MAX_RETRIES: int = 3
    RETRY_MULTIPLIER: int = 1
    RETRY_MIN_WAIT: int = 1
    RETRY_MAX_WAIT: int = 10


@dataclass(frozen=True)
class DistanceConfig:
    """距离阈值配置（公里）"""
    # 同天景点最大距离（城市）
    MAX_SAME_DAY_KM: float = 50.0
    # 同天景点最大距离（自然风光区）
    MAX_SAME_DAY_NATURE_KM: float = 120.0
    # POI 分散判断阈值
    POI_SPREAD_THRESHOLD_KM: float = 30.0
    # 附近搜索半径（米）
    NEARBY_SEARCH_RADIUS_M: int = 1000
    # 步行距离阈值
    WALKING_DISTANCE_KM: float = 1.0
    # 地球半径（公里）
    EARTH_RADIUS_KM: float = 6371.0


@dataclass(frozen=True)
class PaginationConfig:
    """分页配置"""
    DEFAULT_PAGE_SIZE: int = 20
    DEFAULT_SEARCH_COUNT: int = 10
    MAX_PAGE_SIZE: int = 50
    POI_SEARCH_LIMIT: int = 15


@dataclass(frozen=True)
class PriceConfig:
    """价格配置（人民币）"""
    # 酒店价格范围
    BUDGET_HOTEL_MIN: int = 150
    BUDGET_HOTEL_MAX: int = 300
    COMFORT_HOTEL_MIN: int = 300
    COMFORT_HOTEL_MAX: int = 500
    LUXURY_HOTEL_MIN: int = 500
    LUXURY_HOTEL_MAX: int = 1500
    
    # 默认酒店估价
    DEFAULT_BUDGET_PRICE: int = 180
    DEFAULT_COMFORT_PRICE: int = 320
    DEFAULT_LUXURY_PRICE: int = 600
    
    # 门票估价
    TICKET_MUSEUM: int = 60
    TICKET_THEME_PARK: int = 500
    TICKET_PARK: int = 20
    TICKET_TEMPLE: int = 10
    TICKET_DEFAULT: int = 30
    
    # 交通估价
    TRANSPORT_TAXI_BASE: int = 50


@dataclass(frozen=True)
class ContentConfig:
    """内容配置"""
    # 页面内容最大长度
    MAX_PAGE_CONTENT_LENGTH: int = 8000
    GUIDE_CONTENT_LENGTH: int = 6000
    # LLM 上下文限制
    MAX_CONTEXT_LENGTH: int = 4000


@dataclass(frozen=True)
class LLMConfig:
    """LLM 配置"""
    DEFAULT_MAX_TOKENS: int = 4096
    SCORE_MAX_TOKENS: int = 2048
    DEFAULT_TEMPERATURE: float = 0.7
    SCORE_TEMPERATURE: float = 0.3


@dataclass(frozen=True)
class PlanningConfig:
    """行程规划配置"""
    # 每天最大活动时长（分钟）
    MAX_DAILY_DURATION_MIN: int = 480
    # 餐饮活动距上一活动的最大距离（公里）
    MEAL_MAX_DISTANCE_KM: float = 5.0
    # 坐标偏移量（用于餐饮活动附近模拟，约 80m）
    MEAL_COORD_OFFSET: float = 0.0008
    # POI 名称匹配最低相似度
    POI_SIMILARITY_THRESHOLD: float = 0.5
    # 最大距离验证阈值（公里）
    MAX_ITINERARY_DISTANCE_KM: float = 50.0
    # 默认酒店价格
    DEFAULT_HOTEL_PRICE: int = 300


# 创建单例实例
HTTP = HttpConfig()
DISTANCE = DistanceConfig()
PAGINATION = PaginationConfig()
PRICE = PriceConfig()
CONTENT = ContentConfig()
LLM = LLMConfig()
PLANNING = PlanningConfig()

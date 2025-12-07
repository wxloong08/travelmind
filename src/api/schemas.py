"""
API 请求/响应 Schema

使用 Pydantic v2 进行数据验证
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ============================================================
# 通用响应
# ============================================================


class BaseResponse(BaseModel):
    """基础响应模型"""

    success: bool = True
    message: str = "OK"
    timestamp: datetime = Field(default_factory=datetime.now)


class ErrorResponse(BaseResponse):
    """错误响应模型"""

    success: bool = False
    error_code: str | None = None
    detail: str | None = None


# ============================================================
# 聊天相关
# ============================================================


class ChatRequest(BaseModel):
    """聊天请求"""

    message: str = Field(..., min_length=1, max_length=10000, description="用户消息")
    session_id: str | None = Field(None, description="会话ID，用于多轮对话")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message": "帮我规划一个杭州三日游",
                    "session_id": "session_123",
                }
            ]
        }
    }


class ChatResponse(BaseResponse):
    """聊天响应"""

    response: str = Field(..., description="AI 回复内容")
    session_id: str = Field(..., description="会话 ID")
    task_type: str | None = Field(None, description="识别的任务类型")
    planning_phase: str | None = Field(None, description="当前规划阶段")
    has_plan: bool = Field(False, description="是否已生成旅游计划")
    metadata: dict[str, Any] | None = Field(None, description="额外元数据")


# ============================================================
# POI 搜索
# ============================================================


class POISearchRequest(BaseModel):
    """POI 搜索请求"""

    keywords: str = Field(..., min_length=1, max_length=100, description="搜索关键词")
    city: str = Field(..., min_length=1, max_length=50, description="城市名称")
    poi_type: str | None = Field(
        None,
        description="POI类型: scenic, hotel, restaurant, shopping",
    )
    page_size: int = Field(10, ge=1, le=20, description="返回数量")


class POIItem(BaseModel):
    """POI 项目"""

    name: str
    address: str
    type: str
    rating: float | None = None
    cost: float | None = None
    tel: str | None = None
    city: str | None = None
    district: str | None = None
    location: dict[str, float] | None = None


class POISearchResponse(BaseResponse):
    """POI 搜索响应"""

    query: dict[str, str]
    count: int
    results: list[POIItem]


# ============================================================
# 天气
# ============================================================


class WeatherRequest(BaseModel):
    """天气查询请求"""

    city: str = Field(..., min_length=1, max_length=50, description="城市名称")
    forecast: bool = Field(False, description="是否获取天气预报")


class WeatherResponse(BaseResponse):
    """天气查询响应"""

    city: str
    weather: str | None = None
    temperature: str | None = None
    humidity: str | None = None
    wind: str | None = None
    forecasts: list[dict[str, Any]] | None = None


# ============================================================
# 路线规划
# ============================================================


class RouteRequest(BaseModel):
    """路线规划请求"""

    origin_lng: float = Field(..., description="起点经度")
    origin_lat: float = Field(..., description="起点纬度")
    dest_lng: float = Field(..., description="终点经度")
    dest_lat: float = Field(..., description="终点纬度")
    mode: str = Field("driving", description="出行方式: driving, walking, transit")


class RouteResponse(BaseResponse):
    """路线规划响应"""

    origin: dict[str, float]
    destination: dict[str, float]
    mode: str
    distance_km: float
    duration_min: int
    steps: list[dict[str, Any]] | None = None


# ============================================================
# 网络搜索
# ============================================================


class WebSearchRequest(BaseModel):
    """网络搜索请求"""

    query: str = Field(..., min_length=1, max_length=200, description="搜索关键词")
    count: int = Field(5, ge=1, le=10, description="返回数量")
    freshness: str | None = Field(None, description="时效性: day, week, month")


class SearchResultItem(BaseModel):
    """搜索结果项"""

    title: str
    url: str
    snippet: str
    source: str | None = None
    date: str | None = None


class WebSearchResponse(BaseResponse):
    """网络搜索响应"""

    query: str
    count: int
    results: list[SearchResultItem]


# ============================================================
# 健康检查
# ============================================================


class HealthResponse(BaseModel):
    """健康检查响应"""

    status: str = "healthy"
    version: str = "0.1.0"
    environment: str
    timestamp: datetime = Field(default_factory=datetime.now)
    services: dict[str, str] = Field(default_factory=dict)


# ============================================================
# AI 助手功能 - 前端 BFF 接口
# ============================================================


class AssistantRequest(BaseModel):
    """AI 助手通用请求"""

    destination: str = Field(..., min_length=1, max_length=50, description="目的地城市")
    context: str | None = Field(None, description="行程上下文（景点列表等）")
    weather: str | None = Field(None, description="天气信息")
    days: int = Field(3, ge=1, le=30, description="旅行天数")


# --- 预算估算 ---
class BudgetCategory(BaseModel):
    """预算分类"""

    name: str = Field(..., description="分类名称，如餐饮、住宿")
    amount: str = Field(..., description="金额范围，如 800-1200")
    desc: str = Field(..., description="说明")


class BudgetResponse(BaseResponse):
    """预算估算响应"""

    total_range: str = Field(..., description="总预算范围，如 3000-5000 RMB")
    categories: list[BudgetCategory] = Field(default_factory=list)
    saving_tip: str = Field(..., description="省钱小贴士")


# --- 行李清单 ---
class PackingItem(BaseModel):
    """行李物品"""

    name: str
    reason: str | None = None


class PackingCategory(BaseModel):
    """行李分类"""

    name: str = Field(..., description="分类名称，如电子产品、洗漱用品")
    items: list[PackingItem] = Field(default_factory=list)


class PackingResponse(BaseResponse):
    """行李清单响应"""

    special_tips: str | None = Field(None, description="特别提醒")
    categories: list[PackingCategory] = Field(default_factory=list)


# --- 氛围歌单 ---
class SongItem(BaseModel):
    """歌曲"""

    title: str
    artist: str
    reason: str | None = None


class PlaylistResponse(BaseResponse):
    """歌单响应"""

    vibe_title: str = Field(..., description="歌单标题")
    vibe_desc: str = Field(..., description="氛围描述")
    songs: list[SongItem] = Field(default_factory=list)


# --- 紧急助手 ---
class SOSCard(BaseModel):
    """SOS 求助卡"""

    text_local: str = Field(..., description="本地语言求助文本")
    text_en: str = Field(..., description="英文求助文本")
    pronunciation: str = Field(..., description="发音指南")


class EmergencyResponse(BaseResponse):
    """紧急助手响应"""

    local_numbers: dict[str, str] = Field(..., description="本地紧急电话")
    sos_card: SOSCard | None = None
    embassy_tip: str | None = Field(None, description="领事馆/安全提示")


# --- 文化锦囊 ---
class PhraseItem(BaseModel):
    """地道话术"""

    local: str = Field(..., description="本地语言")
    pronunciation: str = Field(..., description="发音")
    meaning: str = Field(..., description="含义")


class CultureResponse(BaseResponse):
    """文化锦囊响应"""

    taboos: list[str] = Field(default_factory=list, description="禁忌事项")
    etiquette: str | None = Field(None, description="礼仪建议")
    phrases: list[PhraseItem] = Field(default_factory=list)


# --- 伴手礼指南 ---
class SouvenirItem(BaseModel):
    """伴手礼"""

    name: str
    desc: str


class SouvenirResponse(BaseResponse):
    """伴手礼响应"""

    must_buy: list[SouvenirItem] = Field(default_factory=list, description="推荐购买")
    avoid: list[str] = Field(default_factory=list, description="避坑清单")


# --- 摄影挑战 ---
class PhotoChallenge(BaseModel):
    """摄影挑战任务"""

    title: str
    desc: str


class PhotoChallengeResponse(BaseResponse):
    """摄影挑战响应"""

    challenges: list[PhotoChallenge] = Field(default_factory=list)


# --- 问路卡 ---
class DirectionCardRequest(BaseModel):
    """问路卡请求"""

    destination: str = Field(..., description="目的地城市")
    place_name: str = Field(..., description="要去的地点名称")


class DirectionCardResponse(BaseResponse):
    """问路卡响应"""

    local_text: str = Field(..., description="本地语言：请带我去...")
    pronunciation: str = Field(..., description="发音指南")
    address: str | None = Field(None, description="详细地址")


# --- 景点故事 ---
class StoryRequest(BaseModel):
    """景点故事请求"""

    destination: str = Field(..., description="目的地城市")
    place_name: str = Field(..., description="景点名称")


class StoryResponse(BaseResponse):
    """景点故事响应"""

    story: str = Field(..., description="景点故事/传说")


# --- 每日攻略 ---
class PhotoSpot(BaseModel):
    """拍照点"""

    name: str
    desc: str


class DayTipsResponse(BaseResponse):
    """每日攻略响应"""

    photo_spots: list[PhotoSpot] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    food: list[str] = Field(default_factory=list)
    transport: str | None = None


class DayTipsRequest(BaseModel):
    """每日攻略请求"""

    destination: str
    day_title: str
    activities: list[str] = Field(default_factory=list)


# --- 结构化行程（含坐标）---
class Location(BaseModel):
    """地理位置"""

    lat: float
    lng: float


class ActivityItem(BaseModel):
    """行程活动"""

    time: str = Field(..., description="时间，如 09:00")
    title: str = Field(..., description="地点/活动名称")
    type: str = Field("sight", description="类型: sight, food, hotel, transport")
    desc: str = Field(..., description="简短描述")
    location: Location | None = Field(None, description="经纬度坐标")
    image: str | None = Field(None, description="图片URL")


class ItineraryDay(BaseModel):
    """行程日"""

    day: int
    title: str = Field(..., description="当日主题")
    activities: list[ActivityItem] = Field(default_factory=list)


class StructuredChatResponse(BaseResponse):
    """结构化聊天响应（含行程数据）"""

    chat_response: str = Field(..., description="AI 对话回复")
    destination_detected: str | None = Field(None, description="识别到的目的地")
    status_update: str = Field("Planning", description="状态: Planning, Created")
    weather_forecast: dict[str, str] | None = Field(None, description="天气预报")
    itinerary: list[ItineraryDay] = Field(default_factory=list)
    pois: list[POIItem] = Field(default_factory=list, description="推荐酒店/地点")

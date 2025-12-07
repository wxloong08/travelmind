"""
FastAPI 路由定义

RESTful API 端点
"""

from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from src.api.schemas import (
    ChatRequest,
    ChatResponse,
    ErrorResponse,
    HealthResponse,
    POISearchRequest,
    POISearchResponse,
    RouteRequest,
    RouteResponse,
    WeatherRequest,
    WeatherResponse,
    WebSearchRequest,
    WebSearchResponse,
)
from src.config import settings
from src.graphs import run_travel_agent, stream_travel_agent
from src.tools import get_route, get_weather, search_poi, web_search

logger = structlog.get_logger()

# 创建路由器
router = APIRouter()


# ============================================================
# 健康检查
# ============================================================


@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="健康检查",
)
async def health_check() -> HealthResponse:
    """
    系统健康检查

    返回服务状态和版本信息
    """
    services = {}

    # 检查 LLM 配置
    services["llm"] = "configured" if settings.dashscope_api_key else "not_configured"

    # 检查高德地图配置
    services["amap"] = "configured" if settings.amap_api_key else "not_configured"

    # 检查搜索配置
    services["search"] = "configured" if settings.bocha_api_key else "not_configured"

    # 检查 Langfuse 配置
    services["langfuse"] = "configured" if settings.langfuse_enabled else "not_configured"

    return HealthResponse(
        status="healthy",
        version="0.1.0",
        environment=settings.environment,
        services=services,
    )


# ============================================================
# 聊天 API
# ============================================================


@router.post(
    "/chat",
    response_model=ChatResponse,
    responses={500: {"model": ErrorResponse}},
    tags=["Chat"],
    summary="智能对话",
)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    与 TravelMind 进行智能对话

    支持：
    - 旅游规划
    - 景点推荐
    - 行程安排
    - 租房咨询
    """
    logger.info("Chat request", session_id=request.session_id, message_length=len(request.message))

    try:
        result = await run_travel_agent(
            user_input=request.message,
            session_id=request.session_id,
        )

        return ChatResponse(
            success=True,
            message="OK",
            response=result["response"],
            session_id=result["session_id"],
            task_type=result.get("task_type"),
            planning_phase=result.get("planning_phase"),
            has_plan=result.get("has_plan", False),
            metadata={
                "collected_pois_count": result.get("collected_pois_count", 0),
            },
        )

    except Exception as e:
        logger.error("Chat failed", error=str(e), session_id=request.session_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat processing failed: {str(e)}",
        )


@router.post(
    "/chat/stream",
    tags=["Chat"],
    summary="流式对话",
)
async def chat_stream(request: ChatRequest):
    """
    流式返回对话结果

    使用 Server-Sent Events (SSE) 格式
    """
    import json

    async def generate():
        try:
            async for event in stream_travel_agent(
                user_input=request.message,
                session_id=request.session_id,
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


# ============================================================
# 工具 API
# ============================================================


@router.post(
    "/tools/poi/search",
    response_model=POISearchResponse,
    tags=["Tools"],
    summary="POI 搜索",
)
async def api_search_poi(request: POISearchRequest) -> POISearchResponse:
    """
    搜索地点/景点/酒店/餐厅

    直接调用高德地图 API 进行 POI 搜索
    """
    logger.info("POI search", keywords=request.keywords, city=request.city)

    try:
        result = await search_poi.ainvoke({
            "keywords": request.keywords,
            "city": request.city,
            "poi_type": request.poi_type,
            "page_size": request.page_size,
        })

        return POISearchResponse(
            query=result["query"],
            count=result["count"],
            results=result["results"],
        )

    except Exception as e:
        logger.error("POI search failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/tools/weather",
    response_model=WeatherResponse,
    tags=["Tools"],
    summary="天气查询",
)
async def api_get_weather(request: WeatherRequest) -> WeatherResponse:
    """
    查询城市天气

    支持实时天气和天气预报
    """
    logger.info("Weather query", city=request.city, forecast=request.forecast)

    try:
        result = await get_weather.ainvoke({
            "city": request.city,
            "forecast": request.forecast,
        })

        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["error"],
            )

        return WeatherResponse(
            city=result.get("city", request.city),
            weather=result.get("weather"),
            temperature=result.get("temperature"),
            humidity=result.get("humidity"),
            wind=f"{result.get('winddirection', '')}风 {result.get('windpower', '')}级",
            forecasts=result.get("forecasts"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Weather query failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/tools/route",
    response_model=RouteResponse,
    tags=["Tools"],
    summary="路线规划",
)
async def api_get_route(request: RouteRequest) -> RouteResponse:
    """
    获取两点之间的路线规划

    支持驾车、步行、公交三种方式
    """
    logger.info("Route planning", mode=request.mode)

    try:
        result = await get_route.ainvoke({
            "origin_lng": request.origin_lng,
            "origin_lat": request.origin_lat,
            "dest_lng": request.dest_lng,
            "dest_lat": request.dest_lat,
            "mode": request.mode,
        })

        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["error"],
            )

        return RouteResponse(
            origin=result["origin"],
            destination=result["destination"],
            mode=result["mode"],
            distance_km=result["distance_km"],
            duration_min=result["duration_min"],
            steps=result.get("steps"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Route planning failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/tools/search",
    response_model=WebSearchResponse,
    tags=["Tools"],
    summary="网络搜索",
)
async def api_web_search(request: WebSearchRequest) -> WebSearchResponse:
    """
    搜索网络信息

    获取旅游攻略、最新资讯等
    """
    logger.info("Web search", query=request.query)

    try:
        result = await web_search.ainvoke({
            "query": request.query,
            "count": request.count,
            "freshness": request.freshness,
        })

        return WebSearchResponse(
            query=result["query"],
            count=result["count"],
            results=result["results"],
        )

    except Exception as e:
        logger.error("Web search failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================
# AI 助手 API (BFF 风格)
# ============================================================


from src.api.schemas import (
    AssistantRequest,
    BudgetResponse,
    BudgetCategory,
    PackingResponse,
    PackingCategory,
    PackingItem,
    PlaylistResponse,
    SongItem,
    EmergencyResponse,
    SOSCard,
    CultureResponse,
    PhraseItem,
    SouvenirResponse,
    SouvenirItem,
    PhotoChallengeResponse,
    PhotoChallenge,
    DirectionCardRequest,
    DirectionCardResponse,
    StoryRequest,
    StoryResponse,
    DayTipsRequest,
    DayTipsResponse,
    PhotoSpot,
)
from src.services.assistants import assistant_service


@router.post(
    "/assistants/budget",
    response_model=BudgetResponse,
    tags=["AI Assistants"],
    summary="预算估算",
)
async def api_estimate_budget(request: AssistantRequest) -> BudgetResponse:
    """
    AI 智能预算估算

    根据目的地和行程生成预算建议
    """
    logger.info("Budget estimation", destination=request.destination)

    result = await assistant_service.estimate_budget(
        destination=request.destination,
        context=request.context,
        days=request.days,
    )

    return BudgetResponse(
        total_range=result.get("total_range", ""),
        categories=[
            BudgetCategory(**cat) for cat in result.get("categories", [])
        ],
        saving_tip=result.get("saving_tip", ""),
    )


@router.post(
    "/assistants/packing",
    response_model=PackingResponse,
    tags=["AI Assistants"],
    summary="行李清单",
)
async def api_generate_packing(request: AssistantRequest) -> PackingResponse:
    """
    AI 智能行李清单

    根据目的地、天气和行程生成行李建议
    """
    logger.info("Packing list", destination=request.destination)

    result = await assistant_service.generate_packing_list(
        destination=request.destination,
        context=request.context,
        weather=request.weather,
        days=request.days,
    )

    categories = []
    for cat in result.get("categories", []):
        items = [PackingItem(**item) for item in cat.get("items", [])]
        categories.append(PackingCategory(name=cat.get("name", ""), items=items))

    return PackingResponse(
        special_tips=result.get("special_tips"),
        categories=categories,
    )


@router.post(
    "/assistants/playlist",
    response_model=PlaylistResponse,
    tags=["AI Assistants"],
    summary="氛围歌单",
)
async def api_generate_playlist(request: AssistantRequest) -> PlaylistResponse:
    """
    AI 氛围歌单推荐

    根据目的地生成旅行歌单
    """
    logger.info("Playlist generation", destination=request.destination)

    result = await assistant_service.generate_playlist(
        destination=request.destination,
        context=request.context,
    )

    return PlaylistResponse(
        vibe_title=result.get("vibe_title", ""),
        vibe_desc=result.get("vibe_desc", ""),
        songs=[SongItem(**song) for song in result.get("songs", [])],
    )


@router.post(
    "/assistants/emergency",
    response_model=EmergencyResponse,
    tags=["AI Assistants"],
    summary="紧急助手",
)
async def api_generate_emergency(request: AssistantRequest) -> EmergencyResponse:
    """
    紧急求助信息

    提供当地紧急电话和 SOS 求助卡
    """
    logger.info("Emergency info", destination=request.destination)

    result = await assistant_service.generate_emergency_info(
        destination=request.destination,
    )

    sos_card = None
    if result.get("sos_card"):
        sos_card = SOSCard(**result["sos_card"])

    return EmergencyResponse(
        local_numbers=result.get("local_numbers", {}),
        sos_card=sos_card,
        embassy_tip=result.get("embassy_tip"),
    )


@router.post(
    "/assistants/culture",
    response_model=CultureResponse,
    tags=["AI Assistants"],
    summary="文化锦囊",
)
async def api_generate_culture(request: AssistantRequest) -> CultureResponse:
    """
    本地文化指南

    提供禁忌、礼仪和地道话术
    """
    logger.info("Culture guide", destination=request.destination)

    result = await assistant_service.generate_culture_guide(
        destination=request.destination,
    )

    return CultureResponse(
        taboos=result.get("taboos", []),
        etiquette=result.get("etiquette"),
        phrases=[PhraseItem(**p) for p in result.get("phrases", [])],
    )


@router.post(
    "/assistants/souvenirs",
    response_model=SouvenirResponse,
    tags=["AI Assistants"],
    summary="伴手礼指南",
)
async def api_generate_souvenirs(request: AssistantRequest) -> SouvenirResponse:
    """
    伴手礼推荐

    推荐值得购买的特产和避坑清单
    """
    logger.info("Souvenir guide", destination=request.destination)

    result = await assistant_service.generate_souvenir_guide(
        destination=request.destination,
    )

    return SouvenirResponse(
        must_buy=[SouvenirItem(**item) for item in result.get("must_buy", [])],
        avoid=result.get("avoid", []),
    )


@router.post(
    "/assistants/photography",
    response_model=PhotoChallengeResponse,
    tags=["AI Assistants"],
    summary="摄影挑战",
)
async def api_generate_photo_challenges(request: AssistantRequest) -> PhotoChallengeResponse:
    """
    摄影挑战任务

    生成有趣的摄影打卡任务
    """
    logger.info("Photo challenges", destination=request.destination)

    result = await assistant_service.generate_photo_challenges(
        destination=request.destination,
    )

    return PhotoChallengeResponse(
        challenges=[PhotoChallenge(**c) for c in result.get("challenges", [])],
    )


@router.post(
    "/assistants/direction_card",
    response_model=DirectionCardResponse,
    tags=["AI Assistants"],
    summary="问路卡",
)
async def api_generate_direction_card(request: DirectionCardRequest) -> DirectionCardResponse:
    """
    生成问路卡

    用于向当地人问路
    """
    logger.info("Direction card", destination=request.destination, place=request.place_name)

    result = await assistant_service.generate_direction_card(
        destination=request.destination,
        place_name=request.place_name,
    )

    return DirectionCardResponse(
        local_text=result.get("local_text", ""),
        pronunciation=result.get("pronunciation", ""),
        address=result.get("address"),
    )


@router.post(
    "/assistants/story",
    response_model=StoryResponse,
    tags=["AI Assistants"],
    summary="景点故事",
)
async def api_generate_story(request: StoryRequest) -> StoryResponse:
    """
    景点故事/传说

    讲述景点的历史典故或民间传说
    """
    logger.info("Story generation", destination=request.destination, place=request.place_name)

    story = await assistant_service.generate_story(
        destination=request.destination,
        place_name=request.place_name,
    )

    return StoryResponse(story=story)


@router.post(
    "/assistants/day_tips",
    response_model=DayTipsResponse,
    tags=["AI Assistants"],
    summary="每日攻略",
)
async def api_generate_day_tips(request: DayTipsRequest) -> DayTipsResponse:
    """
    每日攻略

    提供拍照点、避坑指南、美食和交通建议
    """
    logger.info("Day tips", destination=request.destination, title=request.day_title)

    result = await assistant_service.generate_day_tips(
        destination=request.destination,
        day_title=request.day_title,
        activities=request.activities,
    )

    return DayTipsResponse(
        photo_spots=[PhotoSpot(**s) for s in result.get("photo_spots", [])],
        warnings=result.get("warnings", []),
        food=result.get("food", []),
        transport=result.get("transport"),
    )


from pydantic import BaseModel


class DiaryRequest(BaseModel):
    """日记请求"""
    destination: str
    day: int
    day_title: str
    activities: list[str]


class DiaryResponse(BaseModel):
    """日记响应"""
    text: str


class SocialCaptionsRequest(BaseModel):
    """发圈文案请求"""
    destination: str
    place_name: str


class CaptionStyle(BaseModel):
    """文案风格"""
    name: str
    text: str


class SocialCaptionsResponse(BaseModel):
    """发圈文案响应"""
    styles: list[CaptionStyle]


@router.post(
    "/assistants/diary",
    response_model=DiaryResponse,
    tags=["AI Assistants"],
    summary="旅行日记",
)
async def api_generate_diary(request: DiaryRequest) -> DiaryResponse:
    """
    生成旅行日记

    以第一人称写一篇深刻动人的旅行日记
    """
    logger.info("Diary generation", destination=request.destination, day=request.day)

    diary_text = await assistant_service.generate_diary(
        destination=request.destination,
        day=request.day,
        day_title=request.day_title,
        activities=request.activities,
    )

    return DiaryResponse(text=diary_text)


@router.post(
    "/assistants/social_captions",
    response_model=SocialCaptionsResponse,
    tags=["AI Assistants"],
    summary="发圈文案",
)
async def api_generate_social_captions(request: SocialCaptionsRequest) -> SocialCaptionsResponse:
    """
    生成社交媒体发圈文案

    返回3种不同风格的朋友圈文案
    """
    logger.info("Social captions generation", destination=request.destination, place=request.place_name)

    result = await assistant_service.generate_social_captions(
        destination=request.destination,
        place_name=request.place_name,
    )

    return SocialCaptionsResponse(
        styles=[CaptionStyle(**s) for s in result.get("styles", [])]
    )


# --- Vlog 脚本 ---
class VlogRequest(BaseModel):
    """Vlog 脚本请求"""
    destination: str
    day: int
    day_title: str
    activities: list[str]


class VlogShot(BaseModel):
    """Vlog 镜头"""
    action: str
    angle: str
    duration: str
    audio: str


class VlogResponse(BaseModel):
    """Vlog 脚本响应"""
    title: str
    shots: list[VlogShot]
    bgm: str


@router.post(
    "/assistants/vlog_script",
    response_model=VlogResponse,
    tags=["AI Assistants"],
    summary="Vlog 脚本",
)
async def api_generate_vlog_script(request: VlogRequest) -> VlogResponse:
    """
    生成 Vlog 拍摄脚本

    包含镜头列表、配音文案、背景音乐建议
    """
    logger.info("Vlog script generation", destination=request.destination, day=request.day)

    result = await assistant_service.generate_vlog_script(
        destination=request.destination,
        day=request.day,
        day_title=request.day_title,
        activities=request.activities,
    )

    return VlogResponse(
        title=result.get("title", ""),
        shots=[VlogShot(**s) for s in result.get("shots", [])],
        bgm=result.get("bgm", ""),
    )


# --- 摄影指导 ---
class PhotoGuideRequest(BaseModel):
    """摄影指导请求"""
    destination: str
    place_name: str


class PhotoGuideResponse(BaseModel):
    """摄影指导响应"""
    best_time: str
    best_angle: str
    composition_tip: str
    gear_tip: str
    avoid: str


@router.post(
    "/assistants/photo_guide",
    response_model=PhotoGuideResponse,
    tags=["AI Assistants"],
    summary="摄影指导",
)
async def api_generate_photo_guide(request: PhotoGuideRequest) -> PhotoGuideResponse:
    """
    生成景点摄影指导

    包含最佳拍摄时间、角度、构图建议
    """
    logger.info("Photo guide generation", destination=request.destination, place=request.place_name)

    result = await assistant_service.generate_photo_guide(
        destination=request.destination,
        place_name=request.place_name,
    )

    return PhotoGuideResponse(**result)


# --- 海报数据 ---
class PosterRequest(BaseModel):
    """海报数据请求"""
    destination: str
    days: int
    activities: list[str] | None = None


class PosterResponse(BaseModel):
    """海报数据响应"""
    destination: str
    days: str
    highlights: list[str]
    budget: str


@router.post(
    "/assistants/poster_data",
    response_model=PosterResponse,
    tags=["AI Assistants"],
    summary="海报数据",
)
async def api_generate_poster_data(request: PosterRequest) -> PosterResponse:
    """
    生成分享海报所需数据

    包含行程亮点、预算摘要
    """
    logger.info("Poster data generation", destination=request.destination, days=request.days)

    result = await assistant_service.generate_poster_data(
        destination=request.destination,
        days=request.days,
        activities=request.activities,
    )

    return PosterResponse(**result)


# ============================================================
# 调试 API (仅开发环境)
# ============================================================


if settings.debug:

    @router.get(
        "/debug/config",
        tags=["Debug"],
        summary="查看配置",
    )
    async def debug_config() -> dict[str, Any]:
        """查看当前配置（仅开发环境）"""
        return {
            "environment": settings.environment,
            "llm_model": settings.llm_model,
            "langfuse_enabled": settings.langfuse_enabled,
            "api_keys_configured": {
                "dashscope": bool(settings.dashscope_api_key),
                "amap": bool(settings.amap_api_key),
                "bocha": bool(settings.bocha_api_key),
            },
        }

    @router.get(
        "/debug/tools",
        tags=["Debug"],
        summary="查看可用工具",
    )
    async def debug_tools() -> dict[str, Any]:
        """查看可用工具定义（仅开发环境）"""
        from src.tools import get_tool_definitions

        return {
            "tools": get_tool_definitions(),
        }

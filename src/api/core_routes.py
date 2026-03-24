"""
FastAPI 路由定义

RESTful API 端点
"""

import json
import traceback
from typing import Any
from urllib.parse import quote

import structlog
from fastapi import APIRouter, Header, HTTPException, status
from fastapi.responses import Response, StreamingResponse

from src.api.schemas import (
    AssistantRequest,
    BudgetBreakdownRequest,
    BudgetBreakdownResponse,
    BudgetCategory,
    BudgetResponse,
    CaptionStyle,
    ChatRequest,
    ChatResponse,
    CultureResponse,
    DayTipsRequest,
    DayTipsResponse,
    DiaryRequest,
    DiaryResponse,
    DirectionCardRequest,
    DirectionCardResponse,
    EmergencyResponse,
    ErrorResponse,
    HealthResponse,
    LocalNewsResponse,
    PackingCategory,
    PackingItem,
    PackingResponse,
    PhotoChallenge,
    PhotoChallengeResponse,
    PhotoGuideRequest,
    PhotoGuideResponse,
    PhotoSpot,
    PlaylistResponse,
    POISearchRequest,
    POISearchResponse,
    PosterImageRequest,
    PosterRequest,
    PosterResponse,
    PhraseItem,
    RouteRequest,
    RouteResponse,
    SOSCard,
    SocialCaptionsRequest,
    SocialCaptionsResponse,
    SongItem,
    SouvenirItem,
    SouvenirResponse,
    StoryRequest,
    StoryResponse,
    VlogRequest,
    VlogResponse,
    VlogShot,
    WeatherForecastResponse,
    WeatherRequest,
    WeatherResponse,
    WebSearchRequest,
    WebSearchResponse,
)
from src.auth.jwt import verify_token
from src.config import settings
from src.graphs import run_travel_agent, stream_travel_agent
from src.services.assistants import assistant_service
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
    """系统健康检查"""
    services = {
        "llm": "configured" if settings.dashscope_api_key else "not_configured",
        "amap": "configured" if settings.amap_api_key else "not_configured",
        "search": "configured" if settings.bocha_api_key else "not_configured",
        "langfuse": "configured" if settings.langfuse_enabled else "not_configured",
    }
    return HealthResponse(
        status="healthy",
        version=settings.version if hasattr(settings, "version") else "0.1.0",
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
    """与 TravelMind 进行智能对话"""
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


def _parse_auth_header(authorization: str | None) -> tuple[str | None, str | None]:
    """从 Authorization header 解析 user_id / guest_id"""
    if not settings.database_enabled or not authorization:
        return None, None

    if not authorization.startswith("Bearer "):
        return None, None

    try:
        token = authorization[7:]  # 比 split 更安全
        payload = verify_token(token)
        if not payload:
            return None, None

        if payload.is_guest:
            return None, payload.sub
        return payload.sub, None
    except Exception as e:
        logger.warning("Failed to parse auth token", error=str(e))
        return None, None


async def _save_trip_if_needed(
    event: dict,
    session_id: str,
    user_id: str | None,
    guest_id: str | None,
    user_message: str,
    ai_response: str,
) -> str | None:
    """在 end 事件时保存行程，返回 trip_id"""
    if not (event.get("itinerary") and settings.database_enabled):
        return None

    try:
        from src.services.trip_service import save_trip_from_stream_event

        effective_session_id = event.get("session_id") or session_id
        trip_id = await save_trip_from_stream_event(
            event_data=event,
            session_id=effective_session_id,
            user_id=user_id,
            guest_id=guest_id,
            user_message=user_message,
            ai_response=ai_response,
        )
        if trip_id:
            logger.info("Trip saved", trip_id=trip_id, user_id=user_id, guest_id=guest_id)
        return trip_id
    except Exception as save_error:
        logger.warning("Failed to save trip", error=str(save_error))
        return None


@router.post(
    "/chat/stream",
    tags=["Chat"],
    summary="流式对话",
)
async def chat_stream(
    request: ChatRequest,
    authorization: str | None = Header(default=None),
):
    """流式返回对话结果（SSE 格式）"""
    user_id, guest_id = _parse_auth_header(authorization)

    async def generate():
        trip_id = None
        ai_response_content = ""
        try:
            logger.info("Stream started", session_id=request.session_id, regenerate=request.regenerate)

            async for event in stream_travel_agent(
                user_input=request.message,
                session_id=request.session_id,
                regenerate=request.regenerate,
                previous_itinerary=request.previous_itinerary,
            ):
                event_type = event.get("type", "unknown")

                if event_type == "token" and event.get("content"):
                    ai_response_content = event.get("content", "")

                if event_type == "end":
                    trip_id = await _save_trip_if_needed(
                        event, request.session_id, user_id, guest_id,
                        request.message, ai_response_content,
                    )
                    if trip_id:
                        event["trip_id"] = trip_id

                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(
                "Stream error",
                error=str(e),
                error_type=type(e).__name__,
                traceback=traceback.format_exc(),
                session_id=request.session_id,
            )
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            logger.info("Stream completed", session_id=request.session_id, trip_id=trip_id)
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
    """搜索地点/景点/酒店/餐厅"""
    logger.info("POI search", keywords=request.keywords, city=request.city)

    try:
        result = await search_poi.ainvoke({
            "keywords": request.keywords,
            "city": request.city,
            "poi_type": request.poi_type,
            "page_size": request.page_size,
        })

        return POISearchResponse(
            query=result.get("query", {}),
            count=result.get("count", 0),
            results=result.get("results", []),
        )

    except Exception as e:
        logger.error("POI search failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


def _format_wind(result: dict) -> str:
    """安全格式化风力信息"""
    direction = result.get("winddirection", "")
    power = result.get("windpower", "")
    if direction and power:
        return f"{direction}风 {power}级"
    if direction:
        return f"{direction}风"
    if power:
        return f"{power}级"
    return ""


@router.post(
    "/tools/weather",
    response_model=WeatherResponse,
    tags=["Tools"],
    summary="天气查询",
)
async def api_get_weather(request: WeatherRequest) -> WeatherResponse:
    """查询城市天气"""
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
            wind=_format_wind(result),
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
    """获取两点之间的路线规划"""
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
            origin=result.get("origin", {}),
            destination=result.get("destination", {}),
            mode=result.get("mode", request.mode),
            distance_km=result.get("distance_km", 0),
            duration_min=result.get("duration_min", 0),
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
    """搜索网络信息"""
    logger.info("Web search", query=request.query)

    try:
        result = await web_search.ainvoke({
            "query": request.query,
            "count": request.count,
            "freshness": request.freshness,
        })

        return WebSearchResponse(
            query=result.get("query", request.query),
            count=result.get("count", 0),
            results=result.get("results", []),
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


@router.post("/assistants/budget", response_model=BudgetResponse, tags=["AI Assistants"], summary="预算估算")
async def api_estimate_budget(request: AssistantRequest) -> BudgetResponse:
    """AI 智能预算估算"""
    logger.info("Budget estimation", destination=request.destination)
    result = await assistant_service.estimate_budget(
        destination=request.destination, context=request.context, days=request.days,
    )
    return BudgetResponse(
        total_range=result.get("total_range", ""),
        categories=[BudgetCategory(**cat) for cat in result.get("categories", [])],
        saving_tip=result.get("saving_tip", ""),
    )


@router.post("/assistants/packing", response_model=PackingResponse, tags=["AI Assistants"], summary="行李清单")
async def api_generate_packing(request: AssistantRequest) -> PackingResponse:
    """AI 智能行李清单"""
    logger.info("Packing list", destination=request.destination)
    result = await assistant_service.generate_packing_list(
        destination=request.destination, context=request.context,
        weather=request.weather, days=request.days,
    )
    categories = []
    for cat in result.get("categories", []):
        items = [PackingItem(**item) for item in cat.get("items", [])]
        categories.append(PackingCategory(name=cat.get("name", ""), items=items))
    return PackingResponse(special_tips=result.get("special_tips"), categories=categories)


@router.post("/assistants/playlist", response_model=PlaylistResponse, tags=["AI Assistants"], summary="氛围歌单")
async def api_generate_playlist(request: AssistantRequest) -> PlaylistResponse:
    """AI 氛围歌单推荐"""
    logger.info("Playlist generation", destination=request.destination)
    result = await assistant_service.generate_playlist(
        destination=request.destination, context=request.context,
    )
    return PlaylistResponse(
        vibe_title=result.get("vibe_title", ""),
        vibe_desc=result.get("vibe_desc", ""),
        songs=[SongItem(**song) for song in result.get("songs", [])],
    )


@router.post("/assistants/emergency", response_model=EmergencyResponse, tags=["AI Assistants"], summary="紧急助手")
async def api_generate_emergency(request: AssistantRequest) -> EmergencyResponse:
    """紧急求助信息"""
    logger.info("Emergency info", destination=request.destination)
    result = await assistant_service.generate_emergency_info(destination=request.destination)
    sos_card = SOSCard(**result["sos_card"]) if result.get("sos_card") else None
    return EmergencyResponse(
        local_numbers=result.get("local_numbers", {}),
        sos_card=sos_card,
        embassy_tip=result.get("embassy_tip"),
    )


@router.post("/assistants/culture", response_model=CultureResponse, tags=["AI Assistants"], summary="文化锦囊")
async def api_generate_culture(request: AssistantRequest) -> CultureResponse:
    """本地文化指南"""
    logger.info("Culture guide", destination=request.destination)
    result = await assistant_service.generate_culture_guide(destination=request.destination)
    return CultureResponse(
        taboos=result.get("taboos", []),
        etiquette=result.get("etiquette"),
        phrases=[PhraseItem(**p) for p in result.get("phrases", [])],
    )


@router.post("/assistants/souvenirs", response_model=SouvenirResponse, tags=["AI Assistants"], summary="伴手礼指南")
async def api_generate_souvenirs(request: AssistantRequest) -> SouvenirResponse:
    """伴手礼推荐"""
    logger.info("Souvenir guide", destination=request.destination)
    result = await assistant_service.generate_souvenir_guide(destination=request.destination)
    return SouvenirResponse(
        must_buy=[SouvenirItem(**item) for item in result.get("must_buy", [])],
        avoid=result.get("avoid", []),
    )


@router.post("/assistants/photography", response_model=PhotoChallengeResponse, tags=["AI Assistants"], summary="摄影挑战")
async def api_generate_photo_challenges(request: AssistantRequest) -> PhotoChallengeResponse:
    """摄影挑战任务"""
    logger.info("Photo challenges", destination=request.destination)
    result = await assistant_service.generate_photo_challenges(destination=request.destination)
    return PhotoChallengeResponse(
        challenges=[PhotoChallenge(**c) for c in result.get("challenges", [])],
    )


@router.post("/assistants/direction_card", response_model=DirectionCardResponse, tags=["AI Assistants"], summary="问路卡")
async def api_generate_direction_card(request: DirectionCardRequest) -> DirectionCardResponse:
    """生成问路卡"""
    logger.info("Direction card", destination=request.destination, place=request.place_name)
    result = await assistant_service.generate_direction_card(
        destination=request.destination, place_name=request.place_name,
    )
    return DirectionCardResponse(
        local_text=result.get("local_text", ""),
        pronunciation=result.get("pronunciation", ""),
        address=result.get("address"),
    )


@router.post("/assistants/story", response_model=StoryResponse, tags=["AI Assistants"], summary="景点故事")
async def api_generate_story(request: StoryRequest) -> StoryResponse:
    """景点故事/传说"""
    logger.info("Story generation", destination=request.destination, place=request.place_name)
    story = await assistant_service.generate_story(
        destination=request.destination, place_name=request.place_name,
    )
    return StoryResponse(story=story)


@router.post("/assistants/day_tips", response_model=DayTipsResponse, tags=["AI Assistants"], summary="每日攻略")
async def api_generate_day_tips(request: DayTipsRequest) -> DayTipsResponse:
    """每日攻略"""
    logger.info("Day tips", destination=request.destination, title=request.day_title)
    result = await assistant_service.generate_day_tips(
        destination=request.destination, day_title=request.day_title, activities=request.activities,
    )
    return DayTipsResponse(
        photo_spots=[PhotoSpot(**s) for s in result.get("photo_spots", [])],
        warnings=result.get("warnings", []),
        food=result.get("food", []),
        transport=result.get("transport"),
    )


@router.post("/assistants/diary", response_model=DiaryResponse, tags=["AI Assistants"], summary="旅行日记")
async def api_generate_diary(request: DiaryRequest) -> DiaryResponse:
    """生成旅行日记"""
    logger.info("Diary generation", destination=request.destination, day=request.day)
    diary_text = await assistant_service.generate_diary(
        destination=request.destination, day=request.day,
        day_title=request.day_title, activities=request.activities,
    )
    return DiaryResponse(text=diary_text)


@router.post("/assistants/social_captions", response_model=SocialCaptionsResponse, tags=["AI Assistants"], summary="发圈文案")
async def api_generate_social_captions(request: SocialCaptionsRequest) -> SocialCaptionsResponse:
    """生成社交媒体发圈文案"""
    logger.info("Social captions generation", destination=request.destination, place=request.place_name)
    result = await assistant_service.generate_social_captions(
        destination=request.destination, place_name=request.place_name,
    )
    return SocialCaptionsResponse(
        styles=[CaptionStyle(**s) for s in result.get("styles", [])]
    )


@router.post("/assistants/vlog_script", response_model=VlogResponse, tags=["AI Assistants"], summary="Vlog 脚本")
async def api_generate_vlog_script(request: VlogRequest) -> VlogResponse:
    """生成 Vlog 拍摄脚本"""
    logger.info("Vlog script generation", destination=request.destination, day=request.day)
    result = await assistant_service.generate_vlog_script(
        destination=request.destination, day=request.day,
        day_title=request.day_title, activities=request.activities,
    )
    return VlogResponse(
        title=result.get("title", ""),
        shots=[VlogShot(**s) for s in result.get("shots", [])],
        bgm=result.get("bgm", ""),
    )


@router.post("/assistants/photo_guide", response_model=PhotoGuideResponse, tags=["AI Assistants"], summary="摄影指导")
async def api_generate_photo_guide(request: PhotoGuideRequest) -> PhotoGuideResponse:
    """生成景点摄影指导"""
    logger.info("Photo guide generation", destination=request.destination, place=request.place_name)
    result = await assistant_service.generate_photo_guide(
        destination=request.destination, place_name=request.place_name,
    )
    return PhotoGuideResponse(**result)


@router.post("/assistants/poster_data", response_model=PosterResponse, tags=["AI Assistants"], summary="海报数据")
async def api_generate_poster_data(request: PosterRequest) -> PosterResponse:
    """生成分享海报所需数据"""
    logger.info("Poster data generation", destination=request.destination, days=request.days)
    result = await assistant_service.generate_poster_data(
        destination=request.destination, days=request.days, activities=request.activities,
    )
    return PosterResponse(**result)


@router.post("/poster/generate", tags=["Poster"], summary="生成海报图片", response_class=Response)
async def api_generate_poster_image(request: PosterImageRequest):
    """生成分享海报图片（Playwright 渲染 HTML 模板 → PNG）"""
    from src.services.images import image_service
    from src.services.poster import poster_service

    logger.info("Poster image generation", destination=request.destination, days=request.days)

    background_url = request.background_url
    image_source = request.image_source

    if not background_url:
        image_data = await image_service.get_city_image(request.destination, "poster_bg")
        background_url = image_data.get("url", "")
        image_source = image_data.get("source", "")

    try:
        image_bytes = await poster_service.generate_poster(
            destination=request.destination,
            days=request.days,
            nights=request.nights,
            budget=request.budget,
            highlights=request.highlights,
            travel_style=request.travel_style,
            background_url=background_url,
            image_source=image_source,
        )
        filename = f"{request.destination}_poster.png"
        encoded_filename = quote(filename)
        return Response(
            content=image_bytes,
            media_type="image/png",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"},
        )
    except Exception as e:
        logger.error("Poster generation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"海报生成失败: {str(e)}",
        )


# ============================================================
# 侧边栏 API
# ============================================================


@router.get("/sidebar/weather/{city}", response_model=WeatherForecastResponse, tags=["Sidebar"], summary="获取天气预报")
async def api_get_weather_forecast(city: str) -> WeatherForecastResponse:
    """获取城市 5 天天气预报"""
    from src.services.sidebar import get_weather_forecast

    result = await get_weather_forecast(city)
    return WeatherForecastResponse(city=result.get("city", city), forecasts=result.get("forecasts", []))


@router.get("/sidebar/news/{city}", response_model=LocalNewsResponse, tags=["Sidebar"], summary="获取当地资讯")
async def api_get_local_news(city: str) -> LocalNewsResponse:
    """获取目的地当地资讯"""
    from src.services.sidebar import get_local_news

    news = await get_local_news(city)
    return LocalNewsResponse(city=city, news=news)


@router.post("/sidebar/budget", response_model=BudgetBreakdownResponse, tags=["Sidebar"], summary="计算预算分解")
async def api_calculate_budget(request: BudgetBreakdownRequest) -> BudgetBreakdownResponse:
    """从行程数据计算预算分解"""
    from src.services.sidebar import calculate_budget_breakdown

    result = calculate_budget_breakdown(request.itinerary, request.destination)
    return BudgetBreakdownResponse(**result)


# ============================================================
# 调试 API (仅开发环境)
# ============================================================


if settings.debug:

    @router.get("/debug/config", tags=["Debug"], summary="查看配置")
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

    @router.get("/debug/tools", tags=["Debug"], summary="查看可用工具")
    async def debug_tools() -> dict[str, Any]:
        """查看可用工具定义（仅开发环境）"""
        from src.tools import get_tool_definitions

        return {"tools": get_tool_definitions()}

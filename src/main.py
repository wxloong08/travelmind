"""
TravelMind - AI 旅游规划与租房助手

FastAPI 应用入口
"""

import structlog
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api import router
from src.config import settings

# 配置结构化日志
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer() if settings.is_production else structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """应用生命周期管理"""
    # 启动时
    logger.info(
        "Starting TravelMind",
        environment=settings.environment,
        debug=settings.debug,
    )

    # 检查必要配置
    if not settings.dashscope_api_key:
        logger.warning("DASHSCOPE_API_KEY not configured, LLM features will not work")

    if not settings.amap_api_key:
        logger.warning("AMAP_API_KEY not configured, map features will not work")

    yield

    # 关闭时
    logger.info("Shutting down TravelMind")


# 创建 FastAPI 应用
app = FastAPI(
    title="TravelMind API",
    description="""
## TravelMind - AI 旅游规划与租房助手

### 功能特性

- 🗺️ **智能旅游规划**: 根据您的偏好，制定个性化旅游攻略
- 🏨 **景点/酒店推荐**: 搜索目的地的景点、酒店、餐厅
- 📅 **行程安排**: 合理安排每日行程，考虑距离和时间
- 🏠 **租房咨询**: 长租房信息搜索和建议

### 技术栈

- **AI 框架**: LangGraph
- **LLM**: 通义千问 (Qwen)
- **数据源**: 高德地图 POI + 博查搜索
- **向量库**: Chroma
- **可观测性**: Langfuse
    """,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    logger.error(
        "Unhandled exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True,
    )

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
            "detail": str(exc) if settings.debug else None,
        },
    )


# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录请求日志"""
    logger.info(
        "Request",
        method=request.method,
        path=request.url.path,
        client=request.client.host if request.client else None,
    )

    response = await call_next(request)

    logger.info(
        "Response",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
    )

    return response


# 注册路由
app.include_router(router, prefix="/api/v1")


# 根路径
@app.get("/", tags=["Root"])
async def root():
    """API 根路径"""
    return {
        "name": "TravelMind API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }


# ============================================================
# 开发服务器入口
# ============================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        workers=settings.api_workers if not settings.debug else 1,
        log_level=settings.log_level.lower(),
    )

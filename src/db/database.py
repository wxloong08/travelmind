"""
数据库连接管理

提供异步数据库连接和会话管理
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from src.config import settings

logger = structlog.get_logger()

# 全局引擎（延迟初始化）
engine = None
AsyncSessionLocal = None


def _create_engine():
    """创建数据库引擎"""
    if not settings.database_url:
        raise ValueError(
            "DATABASE_URL not configured. "
            "Please set DATABASE_URL in your .env file. "
            "Example: DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/travelmind"
        )
    
    # 转换 URL 格式（如果需要）
    db_url = settings.database_url
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    return create_async_engine(
        db_url,
        echo=settings.debug,
        poolclass=NullPool if settings.environment == "development" else None,
        pool_pre_ping=True,
    )


async def init_db() -> None:
    """
    初始化数据库连接
    
    在应用启动时调用
    """
    global engine, AsyncSessionLocal
    
    if not settings.database_url:
        logger.warning("Database not configured, skipping initialization")
        return
    
    try:
        engine = _create_engine()
        AsyncSessionLocal = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        
        # 测试连接
        async with engine.begin() as conn:
            await conn.run_sync(lambda _: None)
        
        logger.info("Database connected", url=settings.database_url.split("@")[-1])
        
    except Exception as e:
        logger.error("Database connection failed", error=str(e))
        raise


async def close_db() -> None:
    """
    关闭数据库连接
    
    在应用关闭时调用
    """
    global engine
    
    if engine:
        await engine.dispose()
        logger.info("Database connection closed")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话
    
    使用方式:
    ```python
    async def my_endpoint(db: AsyncSession = Depends(get_db)):
        ...
    ```
    """
    if AsyncSessionLocal is None:
        raise RuntimeError(
            "Database not initialized. "
            "Make sure DATABASE_URL is configured and init_db() was called."
        )
    
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    上下文管理器版本的数据库会话
    
    使用方式:
    ```python
    async with get_db_context() as db:
        ...
    ```
    """
    if AsyncSessionLocal is None:
        raise RuntimeError("Database not initialized")
    
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def is_db_configured() -> bool:
    """检查数据库是否已配置"""
    return bool(settings.database_url)

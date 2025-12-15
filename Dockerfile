# ============================================================
# TravelMind Dockerfile
# 使用 Playwright 官方镜像（包含 Python + Chromium）
# ============================================================

FROM mcr.microsoft.com/playwright/python:v1.49.0-jammy

WORKDIR /app

# 安装 Node.js（用于 MCP Server）
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# 预安装 MCP Server（高德地图）
RUN npm install -g @amap/amap-maps-mcp-server

# 复制依赖文件
COPY pyproject.toml README.md ./

# 安装 Python 依赖（完整版）
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    # Web Framework
    fastapi>=0.115.0 \
    "uvicorn[standard]>=0.32.0" \
    python-multipart>=0.0.12 \
    # AI/LLM
    langgraph>=0.2.0 \
    langchain>=0.3.0 \
    langchain-community>=0.3.0 \
    langchain-mcp-adapters \
    dashscope>=1.20.0 \
    # Vector Database
    chromadb>=0.5.0 \
    # HTTP
    httpx>=0.27.0 \
    aiohttp>=3.10.0 \
    # Data Validation
    pydantic>=2.9.0 \
    pydantic-settings>=2.6.0 \
    # Utilities
    python-dotenv>=1.0.0 \
    tenacity>=9.0.0 \
    structlog>=24.4.0 \
    cachetools>=5.3.0 \
    # Observability
    "langfuse>=2.0.0,<3.0.0" \
    # Browser Automation
    jinja2>=3.1.0 \
    playwright>=1.49.0 \
    # Database - PostgreSQL
    "sqlalchemy[asyncio]>=2.0.0" \
    asyncpg>=0.29.0 \
    alembic>=1.13.0 \
    # Cache - Redis
    redis>=5.0.0 \
    # Authentication
    # bcrypt 4.0.1 是与 passlib 兼容的最新安全版本（4.1+ 移除了 __about__ 属性导致兼容问题）
    bcrypt==4.0.1 \
    "python-jose[cryptography]>=3.3.0" \
    "passlib[bcrypt]>=1.7.4" \
    # SMS Service
    tencentcloud-sdk-python-sms>=3.0.0

# 安装 Playwright Chromium（镜像已包含，但需确保）
RUN playwright install chromium

# 复制应用代码
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# 创建数据目录
RUN mkdir -p /app/data

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# 环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# 启动命令（以 root 运行，Playwright 需要）
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

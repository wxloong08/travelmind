# ============================================================
# TravelMind Dockerfile
# 支持 MCP (Model Context Protocol) 集成
# ============================================================

FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖 + Node.js（用于 MCP Server）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# 预安装 MCP Server（高德地图 + 博查搜索）
RUN npm install -g @amap/amap-maps-mcp-server bocha-search-mcp

# 创建非 root 用户
RUN groupadd --gid 1000 travelmind && \
    useradd --uid 1000 --gid 1000 --shell /bin/bash --create-home travelmind

# 复制依赖文件
COPY pyproject.toml README.md ./

# 安装 Python 依赖（包括 langchain-mcp-adapters）
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    fastapi>=0.115.0 \
    "uvicorn[standard]>=0.32.0" \
    python-multipart>=0.0.12 \
    langgraph>=0.2.0 \
    langchain>=0.3.0 \
    langchain-community>=0.3.0 \
    langchain-mcp-adapters \
    dashscope>=1.20.0 \
    chromadb>=0.5.0 \
    httpx>=0.27.0 \
    aiohttp>=3.10.0 \
    pydantic>=2.9.0 \
    pydantic-settings>=2.6.0 \
    python-dotenv>=1.0.0 \
    tenacity>=9.0.0 \
    structlog>=24.4.0 \
    "langfuse>=2.0.0,<3.0.0" && \
    echo "=== Installed packages ===" && \
    pip list | grep -i langfuse && \
    python -c "from langfuse.decorators import observe; print('Langfuse v2 import OK')"

# 复制应用代码
COPY --chown=travelmind:travelmind src/ ./src/

# 创建数据目录
RUN mkdir -p /app/data && chown -R travelmind:travelmind /app

# 切换到非 root 用户
USER travelmind

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# 环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# 启动命令
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

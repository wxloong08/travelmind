# ============================================================
# TravelMind Makefile
# ============================================================

.PHONY: help install dev test lint format clean docker-build docker-up docker-down

.DEFAULT_GOAL := help

# ============================================================
# 帮助信息
# ============================================================
help: ## 显示帮助信息
	@echo "TravelMind - AI 旅游规划助手"
	@echo ""
	@echo "可用命令:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-18s %s\n", $$1, $$2}'

# ============================================================
# 环境设置
# ============================================================
install: ## 安装依赖
	pip install -e ".[dev]"

setup: install ## 完整环境设置
	cp -n .env.example .env || true
	mkdir -p data/chroma
	@echo "Setup complete! Please edit .env with your API keys."

# ============================================================
# 开发
# ============================================================
dev: ## 启动开发服务器
	python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# ============================================================
# 测试
# ============================================================
test: ## 运行测试
	pytest tests/ -v --cov=src --cov-report=term-missing

test-fast: ## 快速测试
	pytest tests/ -v -x

# ============================================================
# 代码质量
# ============================================================
lint: ## 代码检查
	ruff check src/ tests/
	mypy src/

format: ## 代码格式化
	ruff format src/ tests/
	ruff check --fix src/ tests/

# ============================================================
# Docker
# ============================================================
docker-build: ## 构建 Docker 镜像
	docker-compose build --no-cache

docker-up: ## 启动所有服务 (TravelMind + Langfuse)
	docker-compose up -d

docker-down: ## 停止所有服务
	docker-compose down

docker-logs: ## 查看日志
	docker-compose logs -f

docker-restart: ## 重启 TravelMind
	docker-compose restart app

docker-clean: ## 清理 Docker 资源
	docker-compose down -v --rmi local
	docker system prune -f

# ============================================================
# 清理
# ============================================================
clean: ## 清理临时文件
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/ .coverage htmlcov/

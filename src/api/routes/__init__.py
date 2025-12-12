"""
API 路由模块

路由结构:
- core_routes.py: 主路由（chat, health, tools, assistants）
- auth.py: 认证相关
- trips.py: 行程管理
- admin.py: 后台管理
"""

# 主路由（从重命名后的 core_routes.py 导入）
from src.api.core_routes import router

# 子路由
from src.api.routes.auth import router as auth_router
from src.api.routes.trips import router as trips_router
from src.api.routes.admin import router as admin_router

__all__ = [
    "router",
    "auth_router",
    "trips_router",
    "admin_router",
]

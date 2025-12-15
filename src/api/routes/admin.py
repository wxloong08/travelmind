"""
后台管理 API 路由

提供:
- 用户管理
- 激活码管理
- 配额管理
- 使用统计
"""

import secrets
import string
from datetime import datetime, timezone
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.deps import get_current_user
from src.config import settings
from src.db.database import get_db
from src.db.models import (
    User, UserRole, Guest,
    ActivationCode, CodeType,
    UsageRecord, DailyUsageSummary,
)
from src.services.quota_service import QuotaService

logger = structlog.get_logger()

router = APIRouter(prefix="/admin", tags=["Admin"])


# ============================================================
# 请求/响应模型
# ============================================================

class UserListItem(BaseModel):
    id: str
    phone: str | None
    nickname: str | None
    role: str
    daily_quota: int
    bonus_quota: int
    is_active: bool
    created_at: str
    last_login_at: str | None


class UserListResponse(BaseModel):
    users: list[UserListItem]
    total: int
    page: int
    page_size: int


class UpdateUserRequest(BaseModel):
    role: str | None = None
    daily_quota: int | None = None
    bonus_quota: int | None = None
    is_active: bool | None = None


class AddBonusRequest(BaseModel):
    amount: int = Field(..., ge=1, le=1000, description="增加的次数")


class CreateCodeRequest(BaseModel):
    code_type: str = Field(..., description="类型: upgrade_paid/add_quota")
    quota_value: int = Field(default=0, description="配额值（add_quota 类型时有效）")
    note: str | None = None
    count: int = Field(default=1, ge=1, le=100, description="生成数量")


class CodeListItem(BaseModel):
    id: str
    code: str
    code_type: str
    quota_value: int
    note: str | None
    is_used: bool
    used_by_phone: str | None
    used_at: str | None
    created_at: str


class StatsResponse(BaseModel):
    total_users: int
    total_guests: int
    total_paid_users: int
    total_usage_today: int
    total_usage_week: int


# ============================================================
# 权限检查
# ============================================================

async def require_admin(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """要求管理员权限"""
    if user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return user


# ============================================================
# 管理员密码登录
# ============================================================

class AdminPasswordLoginRequest(BaseModel):
    """管理员密码登录请求"""
    phone: str = Field(..., description="管理员手机号")
    password: str = Field(..., description="管理员密码")


class AdminLoginResponse(BaseModel):
    """管理员登录响应"""
    access_token: str
    token_type: str = "bearer"
    user_id: str
    message: str


@router.post("/login", response_model=AdminLoginResponse)
async def admin_password_login(
    request: AdminPasswordLoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    管理员密码登录
    
    使用手机号 + 密码登录后台（需要在 .env 设置 ADMIN_PASSWORD）
    """
    # 检查是否配置了管理员密码
    if not settings.admin_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="管理员密码未配置，请使用短信验证码登录",
        )
    
    # 验证密码
    if request.password != settings.admin_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="密码错误",
        )
    
    # 查找用户
    from src.db.repositories import UserRepository
    user_repo = UserRepository(db)
    user = await user_repo.get_by_phone(request.phone)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在，请先通过前端注册",
        )
    
    # 检查是否是管理员
    if user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="该用户不是管理员",
        )
    
    # 生成 Token
    from src.auth.jwt import create_access_token
    access_token = create_access_token(user.id, phone=user.phone)
    
    logger.info("Admin password login", user_id=user.id)
    
    return AdminLoginResponse(
        access_token=access_token,
        user_id=user.id,
        message="登录成功",
    )


# ============================================================
# 用户管理
# ============================================================

@router.get("/users", response_model=UserListResponse)
async def list_users(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = 1,
    page_size: int = 20,
    role: str | None = None,
    search: str | None = None,
):
    """获取用户列表"""
    query = select(User).order_by(desc(User.created_at))
    count_query = select(func.count()).select_from(User)
    
    if role:
        query = query.where(User.role == role)
        count_query = count_query.where(User.role == role)
    
    if search:
        query = query.where(
            (User.phone.contains(search)) | 
            (User.nickname.contains(search))
        )
        count_query = count_query.where(
            (User.phone.contains(search)) | 
            (User.nickname.contains(search))
        )
    
    # 分页
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    # 执行查询
    result = await db.execute(query)
    users = result.scalars().all()
    
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0
    
    return UserListResponse(
        users=[
            UserListItem(
                id=u.id,
                phone=u.phone[:3] + "****" + u.phone[-4:] if u.phone else None,
                nickname=u.nickname,
                role=u.role,
                daily_quota=u.daily_quota,
                bonus_quota=u.bonus_quota,
                is_active=u.is_active,
                created_at=u.created_at.isoformat(),
                last_login_at=u.last_login_at.isoformat() if u.last_login_at else None,
            )
            for u in users
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/users/{user_id}")
async def get_user(
    user_id: str,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """获取用户详情"""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    quota_service = QuotaService(db)
    quota_info = await quota_service.get_user_quota_info(user)
    
    return {
        "id": user.id,
        "phone": user.phone,
        "nickname": user.nickname,
        "role": user.role,
        "daily_quota": user.daily_quota,
        "bonus_quota": user.bonus_quota,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat(),
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        "quota_info": quota_info,
    }


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    request: UpdateUserRequest,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """更新用户信息"""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    if request.role is not None:
        if request.role not in [r.value for r in UserRole]:
            raise HTTPException(status_code=400, detail="无效的角色")
        user.role = request.role
    
    if request.daily_quota is not None:
        user.daily_quota = request.daily_quota
    
    if request.bonus_quota is not None:
        user.bonus_quota = request.bonus_quota
    
    if request.is_active is not None:
        user.is_active = request.is_active
    
    await db.commit()
    
    logger.info(
        "Admin updated user",
        admin_id=admin.id,
        user_id=user_id,
        updates=request.model_dump(exclude_none=True),
    )
    
    return {"message": "更新成功"}


@router.post("/users/{user_id}/add-bonus")
async def add_user_bonus(
    user_id: str,
    request: AddBonusRequest,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """为用户增加临时次数"""
    quota_service = QuotaService(db)
    success, message = await quota_service.admin_add_bonus(
        admin_id=admin.id,
        target_user_id=user_id,
        amount=request.amount,
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """删除用户（仅非管理员用户可删除）"""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 不能删除管理员
    if user.role == UserRole.ADMIN.value:
        raise HTTPException(status_code=400, detail="不能删除管理员用户")
    
    # 不能删除自己
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="不能删除自己")
    
    await db.delete(user)
    await db.commit()
    
    logger.info(
        "Admin deleted user",
        admin_id=admin.id,
        deleted_user_id=user_id,
        deleted_phone=user.phone[:3] + "****" + user.phone[-4:] if user.phone else None,
    )
    
    return {"message": "用户已删除"}


# ============================================================
# 激活码管理
# ============================================================

def generate_code() -> str:
    """生成激活码"""
    chars = string.ascii_uppercase + string.digits
    part1 = ''.join(secrets.choice(chars) for _ in range(4))
    part2 = ''.join(secrets.choice(chars) for _ in range(4))
    part3 = ''.join(secrets.choice(chars) for _ in range(4))
    return f"TRVL-{part1}-{part2}-{part3}"


@router.post("/codes")
async def create_codes(
    request: CreateCodeRequest,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """生成激活码"""
    if request.code_type not in [t.value for t in CodeType]:
        raise HTTPException(status_code=400, detail="无效的激活码类型")
    
    codes = []
    for _ in range(request.count):
        code = generate_code()
        
        # 确保唯一
        while True:
            existing = await db.execute(
                select(ActivationCode).where(ActivationCode.code == code)
            )
            if not existing.scalar_one_or_none():
                break
            code = generate_code()
        
        activation_code = ActivationCode(
            code=code,
            code_type=request.code_type,
            quota_value=request.quota_value if request.code_type == CodeType.ADD_QUOTA.value else 0,
            note=request.note,
            created_by_id=admin.id,
        )
        db.add(activation_code)
        codes.append(code)
    
    await db.commit()
    
    logger.info(
        "Admin created activation codes",
        admin_id=admin.id,
        count=len(codes),
        code_type=request.code_type,
    )
    
    return {
        "message": f"成功生成 {len(codes)} 个激活码",
        "codes": codes,
    }


@router.get("/codes")
async def list_codes(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = 1,
    page_size: int = 20,
    is_used: bool | None = None,
):
    """获取激活码列表"""
    query = select(ActivationCode).order_by(desc(ActivationCode.created_at))
    
    if is_used is not None:
        query = query.where(ActivationCode.is_used == is_used)
    
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    result = await db.execute(query)
    codes = result.scalars().all()
    
    items = []
    for c in codes:
        used_by_phone = None
        if c.used_by_id:
            user = await db.get(User, c.used_by_id)
            if user and user.phone:
                used_by_phone = user.phone[:3] + "****" + user.phone[-4:]
        
        items.append(CodeListItem(
            id=c.id,
            code=c.code,
            code_type=c.code_type,
            quota_value=c.quota_value,
            note=c.note,
            is_used=c.is_used,
            used_by_phone=used_by_phone,
            used_at=c.used_at.isoformat() if c.used_at else None,
            created_at=c.created_at.isoformat(),
        ))
    
    return {"codes": items, "page": page, "page_size": page_size}


@router.delete("/codes/{code_id}")
async def delete_code(
    code_id: str,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """删除激活码（仅未使用的）"""
    code = await db.get(ActivationCode, code_id)
    if not code:
        raise HTTPException(status_code=404, detail="激活码不存在")
    
    if code.is_used:
        raise HTTPException(status_code=400, detail="已使用的激活码不能删除")
    
    await db.delete(code)
    await db.commit()
    
    return {"message": "删除成功"}


# ============================================================
# 统计
# ============================================================

@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """获取统计信息"""
    from datetime import date, timedelta
    
    today = date.today()
    week_ago = today - timedelta(days=7)
    
    # 用户总数
    result = await db.execute(select(func.count()).select_from(User))
    total_users = result.scalar() or 0
    
    # 游客总数
    result = await db.execute(select(func.count()).select_from(Guest))
    total_guests = result.scalar() or 0
    
    # 付费用户数
    result = await db.execute(
        select(func.count()).select_from(User).where(User.role == UserRole.PAID.value)
    )
    total_paid_users = result.scalar() or 0
    
    # 今日使用次数
    result = await db.execute(
        select(func.count()).select_from(UsageRecord).where(UsageRecord.usage_date == today)
    )
    total_usage_today = result.scalar() or 0
    
    # 本周使用次数
    result = await db.execute(
        select(func.count()).select_from(UsageRecord).where(UsageRecord.usage_date >= week_ago)
    )
    total_usage_week = result.scalar() or 0
    
    return StatsResponse(
        total_users=total_users,
        total_guests=total_guests,
        total_paid_users=total_paid_users,
        total_usage_today=total_usage_today,
        total_usage_week=total_usage_week,
    )


# ============================================================
# 简易后台页面
# ============================================================

ADMIN_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TravelMind 管理后台</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background: #0f111a; color: #e5e7eb; }
        .card { background: #1a1d2d; border: 1px solid rgba(255,255,255,0.1); }
        .btn { transition: all 0.2s; }
        .btn:hover { transform: translateY(-1px); }
    </style>
</head>
<body class="min-h-screen p-6">
    <div class="max-w-6xl mx-auto">
        <!-- 头部 -->
        <div class="flex justify-between items-center mb-8">
            <h1 class="text-2xl font-bold text-white">TravelMind 管理后台</h1>
            <div id="admin-info" class="text-gray-400 text-sm"></div>
        </div>
        
        <!-- 登录表单 -->
        <div id="login-form" class="card rounded-2xl p-6 max-w-md mx-auto mb-8">
            <h2 class="text-lg font-bold text-white mb-4">管理员登录</h2>
            <div class="space-y-4">
                <input id="phone" type="text" placeholder="手机号" 
                    class="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-500">
                
                <!-- 登录方式切换 -->
                <div class="flex gap-2 text-sm">
                    <button onclick="switchLoginMode('password')" id="mode-password" 
                        class="flex-1 py-1 rounded bg-blue-600 text-white">密码登录</button>
                    <button onclick="switchLoginMode('sms')" id="mode-sms" 
                        class="flex-1 py-1 rounded bg-white/5 text-gray-400">验证码登录</button>
                </div>
                
                <!-- 密码登录 -->
                <div id="password-section">
                    <input id="password" type="password" placeholder="管理员密码" 
                        class="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-500">
                </div>
                
                <!-- 验证码登录 -->
                <div id="sms-section" class="hidden space-y-4">
                    <input id="code" type="text" placeholder="验证码" 
                        class="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-500">
                    <button onclick="sendCode()" class="w-full btn py-2 bg-gray-600 hover:bg-gray-500 text-white rounded-lg">
                        获取验证码
                    </button>
                    <div id="dev-code" class="text-yellow-400 text-sm text-center"></div>
                </div>
                
                <button onclick="login()" class="w-full btn py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg">
                    登录
                </button>
            </div>
        </div>
        
        <!-- 管理面板 -->
        <div id="admin-panel" class="hidden">
            <!-- 统计卡片 -->
            <div class="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
                <div class="card rounded-xl p-4 text-center">
                    <div class="text-2xl font-bold text-white" id="stat-users">-</div>
                    <div class="text-gray-500 text-sm">注册用户</div>
                </div>
                <div class="card rounded-xl p-4 text-center">
                    <div class="text-2xl font-bold text-white" id="stat-paid">-</div>
                    <div class="text-gray-500 text-sm">付费用户</div>
                </div>
                <div class="card rounded-xl p-4 text-center">
                    <div class="text-2xl font-bold text-white" id="stat-guests">-</div>
                    <div class="text-gray-500 text-sm">游客数</div>
                </div>
                <div class="card rounded-xl p-4 text-center">
                    <div class="text-2xl font-bold text-emerald-400" id="stat-today">-</div>
                    <div class="text-gray-500 text-sm">今日生成次数</div>
                </div>
                <div class="card rounded-xl p-4 text-center">
                    <div class="text-2xl font-bold text-blue-400" id="stat-week">-</div>
                    <div class="text-gray-500 text-sm">本周生成次数</div>
                </div>
            </div>
            
            <!-- Tab 切换 -->
            <div class="flex gap-2 mb-4">
                <button onclick="showTab('users')" class="tab-btn px-4 py-2 rounded-lg bg-blue-600 text-white" data-tab="users">
                    用户管理
                </button>
                <button onclick="showTab('codes')" class="tab-btn px-4 py-2 rounded-lg bg-white/5 text-gray-400" data-tab="codes">
                    激活码管理
                </button>
            </div>
            
            <!-- 用户管理 -->
            <div id="tab-users" class="card rounded-2xl p-6">
                <div class="flex justify-between items-center mb-4">
                    <h2 class="text-lg font-bold text-white">用户列表</h2>
                    <input id="user-search" type="text" placeholder="搜索手机号/昵称" 
                        class="px-3 py-1 bg-white/5 border border-white/10 rounded-lg text-white text-sm placeholder-gray-500"
                        onkeyup="searchUsers()">
                </div>
                <div id="user-list" class="space-y-2"></div>
            </div>
            
            <!-- 激活码管理 -->
            <div id="tab-codes" class="card rounded-2xl p-6 hidden">
                <div class="flex justify-between items-center mb-4">
                    <h2 class="text-lg font-bold text-white">激活码管理</h2>
                    <button onclick="showCreateCodeModal()" class="btn px-4 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-sm">
                        生成激活码
                    </button>
                </div>
                <div id="code-list" class="space-y-2"></div>
            </div>
        </div>
        
        <!-- 用户编辑弹窗 -->
        <div id="user-modal" class="fixed inset-0 bg-black/50 hidden flex items-center justify-center z-50">
            <div class="card rounded-2xl p-6 w-full max-w-md mx-4">
                <h3 class="text-lg font-bold text-white mb-4">编辑用户</h3>
                <div id="user-edit-form" class="space-y-4"></div>
                <div class="flex gap-2 mt-6">
                    <button onclick="closeModal('user-modal')" class="btn flex-1 py-2 bg-gray-600 hover:bg-gray-500 text-white rounded-lg">
                        取消
                    </button>
                    <button onclick="saveUser()" class="btn flex-1 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg">
                        保存
                    </button>
                </div>
            </div>
        </div>
        
        <!-- 生成激活码弹窗 -->
        <div id="code-modal" class="fixed inset-0 bg-black/50 hidden flex items-center justify-center z-50">
            <div class="card rounded-2xl p-6 w-full max-w-md mx-4">
                <h3 class="text-lg font-bold text-white mb-4">生成激活码</h3>
                <div class="space-y-4">
                    <div>
                        <label class="block text-sm text-gray-400 mb-1">激活码作用</label>
                        <select id="code-type" class="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white" style="color-scheme: dark;">
                            <option value="upgrade_paid" style="background:#1a1d2d; color:white;">升级为付费用户 (用户使用后变为付费会员)</option>
                            <option value="add_quota" style="background:#1a1d2d; color:white;">增加额外次数 (给用户增加临时使用次数)</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-sm text-gray-400 mb-1">增加次数 (仅"增加额外次数"类型有效)</label>
                        <input id="code-quota" type="number" placeholder="例如: 10" value="10"
                            class="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-500">
                    </div>
                    <div>
                        <label class="block text-sm text-gray-400 mb-1">生成数量 (1-100个)</label>
                        <input id="code-count" type="number" placeholder="生成数量" value="1" min="1" max="100"
                            class="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-500">
                    </div>
                    <div>
                        <label class="block text-sm text-gray-400 mb-1">备注 (可选)</label>
                        <input id="code-note" type="text" placeholder="例如: 送给VIP客户的激活码"
                            class="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-500">
                    </div>
                </div>
                <div id="generated-codes" class="mt-4 hidden">
                    <div class="text-sm text-gray-400 mb-2">生成的激活码：</div>
                    <div id="codes-display" class="bg-white/5 rounded-lg p-3 font-mono text-sm text-emerald-400"></div>
                </div>
                <div class="flex gap-2 mt-6">
                    <button onclick="closeModal('code-modal')" class="btn flex-1 py-2 bg-gray-600 hover:bg-gray-500 text-white rounded-lg">
                        关闭
                    </button>
                    <button onclick="generateCodes()" class="btn flex-1 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg">
                        生成
                    </button>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        const API_BASE = '/api/v1';
        let token = localStorage.getItem('admin_token');
        let currentEditUserId = null;
        
        // 初始化
        if (token) {
            checkAuth();
        }
        
        async function api(url, options = {}) {
            const headers = { 'Content-Type': 'application/json' };
            if (token) headers['Authorization'] = `Bearer ${token}`;
            
            const res = await fetch(API_BASE + url, { ...options, headers });
            if (res.status === 401 || res.status === 403) {
                logout();
                throw new Error('需要登录');
            }
            return res;
        }
        
        async function checkAuth() {
            try {
                const res = await api('/auth/me');
                if (res.ok) {
                    const data = await res.json();
                    if (data.is_guest) {
                        logout();
                        return;
                    }
                    // 直接使用 role 字段检查是否是管理员
                    if (data.role !== 'admin') {
                        alert('需要管理员权限');
                        logout();
                        return;
                    }
                    showAdminPanel(data);
                }
            } catch (e) {
                // 静默处理
            }
        }
        
        // 登录模式切换
        let loginMode = 'password';
        
        function switchLoginMode(mode) {
            loginMode = mode;
            document.getElementById('password-section').classList.toggle('hidden', mode !== 'password');
            document.getElementById('sms-section').classList.toggle('hidden', mode !== 'sms');
            document.getElementById('mode-password').className = mode === 'password' 
                ? 'flex-1 py-1 rounded bg-blue-600 text-white' 
                : 'flex-1 py-1 rounded bg-white/5 text-gray-400';
            document.getElementById('mode-sms').className = mode === 'sms' 
                ? 'flex-1 py-1 rounded bg-blue-600 text-white' 
                : 'flex-1 py-1 rounded bg-white/5 text-gray-400';
        }
        
        async function sendCode() {
            const phone = document.getElementById('phone').value;
            if (!phone || phone.length !== 11) {
                alert('请输入正确的手机号');
                return;
            }
            
            const res = await fetch(API_BASE + '/auth/sms/send', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ phone }),
            });
            const data = await res.json();
            
            if (data.code) {
                document.getElementById('dev-code').textContent = `开发模式验证码: ${data.code}`;
            }
            alert(data.message || '验证码已发送');
        }
        
        async function login() {
            const phone = document.getElementById('phone').value;
            if (!phone || phone.length !== 11) {
                alert('请输入正确的手机号');
                return;
            }
            
            let res;
            if (loginMode === 'password') {
                // 密码登录
                const password = document.getElementById('password').value;
                if (!password) {
                    alert('请输入密码');
                    return;
                }
                
                res = await fetch(API_BASE + '/admin/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ phone, password }),
                });
            } else {
                // 验证码登录
                const code = document.getElementById('code').value;
                if (!code) {
                    alert('请输入验证码');
                    return;
                }
                
                res = await fetch(API_BASE + '/auth/sms/verify', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ phone, code }),
                });
            }
            
            if (!res.ok) {
                const data = await res.json();
                alert(data.detail || '登录失败');
                return;
            }
            
            const data = await res.json();
            token = data.access_token;
            localStorage.setItem('admin_token', token);
            checkAuth();
        }
        
        function logout() {
            token = null;
            localStorage.removeItem('admin_token');
            document.getElementById('login-form').classList.remove('hidden');
            document.getElementById('admin-panel').classList.add('hidden');
        }
        
        function showAdminPanel(user) {
            document.getElementById('login-form').classList.add('hidden');
            document.getElementById('admin-panel').classList.remove('hidden');
            document.getElementById('admin-info').textContent = `管理员: ${user.phone || user.nickname}`;
            loadStats();
            loadUsers();
        }
        
        async function loadStats() {
            const res = await api('/admin/stats');
            if (res.ok) {
                const data = await res.json();
                document.getElementById('stat-users').textContent = data.total_users;
                document.getElementById('stat-paid').textContent = data.total_paid_users;
                document.getElementById('stat-guests').textContent = data.total_guests;
                document.getElementById('stat-today').textContent = data.total_usage_today;
                document.getElementById('stat-week').textContent = data.total_usage_week;
            }
        }
        
        async function loadUsers(search = '') {
            const url = search ? `/admin/users?search=${encodeURIComponent(search)}` : '/admin/users';
            const res = await api(url);
            if (res.ok) {
                const data = await res.json();
                const list = document.getElementById('user-list');
                list.innerHTML = data.users.map(u => `
                    <div class="flex items-center justify-between p-3 bg-white/5 rounded-lg">
                        <div>
                            <span class="text-white">${u.nickname || u.phone || '未知'}</span>
                            <span class="ml-2 text-xs px-2 py-0.5 rounded ${
                                u.role === 'admin' ? 'bg-purple-500/20 text-purple-400' :
                                u.role === 'paid' ? 'bg-emerald-500/20 text-emerald-400' :
                                'bg-gray-500/20 text-gray-400'
                            }">${u.role}</span>
                            <span class="ml-2 text-gray-500 text-xs">配额: ${u.daily_quota}/天 + ${u.bonus_quota}额外</span>
                        </div>
                        <div class="flex gap-2">
                            <button onclick="editUser('${u.id}')" class="btn px-3 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded text-sm">
                                编辑
                            </button>
                            ${u.role !== 'admin' ? `
                            <button onclick="deleteUser('${u.id}', '${u.phone || u.nickname}')" class="btn px-3 py-1 bg-red-600 hover:bg-red-500 text-white rounded text-sm">
                                删除
                            </button>
                            ` : ''}
                        </div>
                    </div>
                `).join('');
            }
        }
        
        function searchUsers() {
            const search = document.getElementById('user-search').value;
            loadUsers(search);
        }
        
        async function editUser(userId) {
            currentEditUserId = userId;
            const res = await api(`/admin/users/${userId}`);
            if (res.ok) {
                const user = await res.json();
                document.getElementById('user-edit-form').innerHTML = `
                    <div>
                        <label class="text-gray-400 text-sm">手机号</label>
                        <div class="text-white">${user.phone || '-'}</div>
                    </div>
                    <div>
                        <label class="text-gray-400 text-sm">角色</label>
                        <select id="edit-role" class="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white" style="color-scheme: dark;">
                            <option value="free" style="background:#1a1d2d; color:white;" ${user.role === 'free' ? 'selected' : ''}>免费用户</option>
                            <option value="paid" style="background:#1a1d2d; color:white;" ${user.role === 'paid' ? 'selected' : ''}>付费用户</option>
                            <option value="admin" style="background:#1a1d2d; color:white;" ${user.role === 'admin' ? 'selected' : ''}>管理员</option>
                        </select>
                    </div>
                    <div>
                        <label class="text-gray-400 text-sm">每日配额</label>
                        <input id="edit-quota" type="number" value="${user.daily_quota}" 
                            class="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white">
                    </div>
                    <div>
                        <label class="text-gray-400 text-sm">额外次数（临时）</label>
                        <input id="edit-bonus" type="number" value="${user.bonus_quota}" 
                            class="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white">
                    </div>
                    <div class="text-xs text-gray-500">
                        今日已用: ${user.quota_info.used_today} | 今日剩余: ${user.quota_info.remaining_today}
                    </div>
                `;
                document.getElementById('user-modal').classList.remove('hidden');
            }
        }
        
        async function saveUser() {
            const role = document.getElementById('edit-role').value;
            const daily_quota = parseInt(document.getElementById('edit-quota').value);
            const bonus_quota = parseInt(document.getElementById('edit-bonus').value);
            
            const res = await api(`/admin/users/${currentEditUserId}`, {
                method: 'PUT',
                body: JSON.stringify({ role, daily_quota, bonus_quota }),
            });
            
            if (res.ok) {
                closeModal('user-modal');
                loadUsers();
                alert('保存成功');
            } else {
                const data = await res.json();
                alert(data.detail || '保存失败');
            }
        }
        
        async function deleteUser(userId, userInfo) {
            if (!confirm(`确定要删除用户 ${userInfo} 吗？此操作不可恢复！`)) {
                return;
            }
            
            const res = await api(`/admin/users/${userId}`, {
                method: 'DELETE',
            });
            
            if (res.ok) {
                loadUsers();
                loadStats();
                alert('用户已删除');
            } else {
                const data = await res.json();
                alert(data.detail || '删除失败');
            }
        }
        
        async function loadCodes() {
            const res = await api('/admin/codes');
            if (res.ok) {
                const data = await res.json();
                const list = document.getElementById('code-list');
                list.innerHTML = data.codes.map(c => `
                    <div class="flex items-center justify-between p-3 bg-white/5 rounded-lg">
                        <div>
                            <span class="font-mono text-emerald-400">${c.code}</span>
                            <span class="ml-2 text-xs px-2 py-0.5 rounded ${
                                c.code_type === 'upgrade_paid' ? 'bg-purple-500/20 text-purple-400' :
                                'bg-blue-500/20 text-blue-400'
                            }">${c.code_type === 'upgrade_paid' ? '升级付费' : '+' + c.quota_value + '次'}</span>
                            ${c.is_used ? `<span class="ml-2 text-xs text-gray-500">已使用: ${c.used_by_phone || '-'}</span>` : ''}
                        </div>
                        ${!c.is_used ? `
                            <button onclick="deleteCode('${c.id}')" class="btn px-3 py-1 bg-red-600 hover:bg-red-500 text-white rounded text-sm">
                                删除
                            </button>
                        ` : ''}
                    </div>
                `).join('');
            }
        }
        
        function showCreateCodeModal() {
            document.getElementById('generated-codes').classList.add('hidden');
            document.getElementById('code-modal').classList.remove('hidden');
        }
        
        async function generateCodes() {
            const code_type = document.getElementById('code-type').value;
            const quota_value = parseInt(document.getElementById('code-quota').value) || 10;
            const count = parseInt(document.getElementById('code-count').value) || 1;
            const note = document.getElementById('code-note').value;
            
            const res = await api('/admin/codes', {
                method: 'POST',
                body: JSON.stringify({ code_type, quota_value, count, note }),
            });
            
            if (res.ok) {
                const data = await res.json();
                document.getElementById('codes-display').innerHTML = data.codes.join('<br>');
                document.getElementById('generated-codes').classList.remove('hidden');
                loadCodes();
            } else {
                const data = await res.json();
                alert(data.detail || '生成失败');
            }
        }
        
        async function deleteCode(codeId) {
            if (!confirm('确定删除该激活码？')) return;
            
            const res = await api(`/admin/codes/${codeId}`, { method: 'DELETE' });
            if (res.ok) {
                loadCodes();
            } else {
                const data = await res.json();
                alert(data.detail || '删除失败');
            }
        }
        
        function showTab(tab) {
            document.querySelectorAll('.tab-btn').forEach(btn => {
                if (btn.dataset.tab === tab) {
                    btn.classList.remove('bg-white/5', 'text-gray-400');
                    btn.classList.add('bg-blue-600', 'text-white');
                } else {
                    btn.classList.add('bg-white/5', 'text-gray-400');
                    btn.classList.remove('bg-blue-600', 'text-white');
                }
            });
            
            document.getElementById('tab-users').classList.toggle('hidden', tab !== 'users');
            document.getElementById('tab-codes').classList.toggle('hidden', tab !== 'codes');
            
            if (tab === 'codes') loadCodes();
        }
        
        function closeModal(id) {
            document.getElementById(id).classList.add('hidden');
        }
    </script>
</body>
</html>
"""


@router.get("/", response_class=HTMLResponse)
async def admin_page():
    """管理后台页面"""
    return HTMLResponse(content=ADMIN_HTML)

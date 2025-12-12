#!/usr/bin/env python3
"""
集成验证脚本

验证所有新模块是否正确集成到项目中
"""

import sys


def check_imports():
    """检查所有 import 是否正常"""
    errors = []
    
    print("=" * 50)
    print("检查模块导入...")
    print("=" * 50)
    
    # 1. 检查数据库模块
    try:
        from src.db import get_db, init_db, close_db, User, Guest, Trip, Conversation, Message
        print("✅ src.db 模块正常")
    except ImportError as e:
        errors.append(f"❌ src.db 导入失败: {e}")
    
    # 2. 检查认证模块
    try:
        from src.auth import create_access_token, verify_token, get_current_identity, SMSService
        print("✅ src.auth 模块正常")
    except ImportError as e:
        errors.append(f"❌ src.auth 导入失败: {e}")
    
    # 3. 检查缓存模块
    try:
        from src.cache import init_redis, close_redis, rate_limiter, api_cache
        print("✅ src.cache 模块正常")
    except ImportError as e:
        errors.append(f"❌ src.cache 导入失败: {e}")
    
    # 4. 检查服务模块
    try:
        from src.services import budget_calculator, accommodation_logic
        print("✅ src.services (budget/accommodation) 模块正常")
    except ImportError as e:
        errors.append(f"❌ src.services 导入失败: {e}")
    
    # 5. 检查路由模块
    try:
        from src.api.routes import auth_router, trips_router
        print("✅ src.api.routes (auth/trips) 路由正常")
    except ImportError as e:
        errors.append(f"❌ src.api.routes 导入失败: {e}")
    
    # 6. 检查 nodes.py 中的集成
    try:
        from src.graphs import nodes
        # 检查是否导入了 budget_calculator 和 accommodation_logic
        source_code = open("src/graphs/nodes.py").read()
        
        if "from src.services.budget_calculator import budget_calculator" in source_code:
            print("✅ nodes.py 已导入 budget_calculator")
        else:
            errors.append("❌ nodes.py 未导入 budget_calculator")
        
        if "from src.services.accommodation_logic import accommodation_logic" in source_code:
            print("✅ nodes.py 已导入 accommodation_logic")
        else:
            errors.append("❌ nodes.py 未导入 accommodation_logic")
        
        # 检查是否在 planning_node 中调用
        if "budget_calculator.calculate" in source_code:
            print("✅ planning_node 调用了 budget_calculator.calculate()")
        else:
            errors.append("❌ planning_node 未调用 budget_calculator.calculate()")
        
        if "accommodation_logic.process_itinerary_accommodation" in source_code:
            print("✅ planning_node 调用了 accommodation_logic.process_itinerary_accommodation()")
        else:
            errors.append("❌ planning_node 未调用 accommodation_logic.process_itinerary_accommodation()")
            
    except Exception as e:
        errors.append(f"❌ 检查 nodes.py 失败: {e}")
    
    # 7. 检查 main.py 中的集成
    try:
        source_code = open("src/main.py").read()
        
        if "settings.database_enabled" in source_code:
            print("✅ main.py 检查了 database_enabled")
        else:
            errors.append("❌ main.py 未检查 database_enabled")
        
        if "auth_router" in source_code and "trips_router" in source_code:
            print("✅ main.py 注册了 auth_router 和 trips_router")
        else:
            errors.append("❌ main.py 未注册认证路由")
            
    except Exception as e:
        errors.append(f"❌ 检查 main.py 失败: {e}")
    
    print()
    print("=" * 50)
    print("检查结果")
    print("=" * 50)
    
    if errors:
        print(f"发现 {len(errors)} 个问题:")
        for err in errors:
            print(f"  {err}")
        return False
    else:
        print("✅ 所有集成检查通过！")
        return True


def check_config():
    """检查配置是否正确"""
    print()
    print("=" * 50)
    print("检查配置...")
    print("=" * 50)
    
    from src.config import settings
    
    print(f"数据库配置: {'✅ 已配置' if settings.database_enabled else '⚠️ 未配置'}")
    print(f"Redis 配置: {'✅ 已配置' if settings.redis_enabled else '⚠️ 未配置（将使用内存缓存）'}")
    print(f"短信服务: {'✅ 已配置' if settings.sms_enabled else '⚠️ 未配置（开发模式）'}")
    print(f"JWT 密钥: {'✅ 已配置' if settings.secret_key else '❌ 未配置'}")


if __name__ == "__main__":
    import os
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    success = check_imports()
    check_config()
    
    sys.exit(0 if success else 1)

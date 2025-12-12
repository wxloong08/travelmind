"""
TravelMind 配置管理

使用 pydantic-settings 进行类型安全的配置管理
支持从环境变量和 .env 文件加载配置

配置分类:
- 【必须】没有则无法运行
- 【推荐】影响核心功能
- 【可选】不配置也能运行
- 【预留】当前版本未使用，为扩展预留
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置类"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ===========================================================
    # 基础配置【可选】- 都有合理默认值
    # ===========================================================
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 1

    # ===========================================================
    # LLM 配置【必须】- 核心功能依赖
    # ===========================================================
    # 获取: https://bailian.console.aliyun.com/
    dashscope_api_key: str = Field(default="", description="通义千问 API Key【必须】")
    llm_model: str = "qwen3-max"  # Qwen3 系列最强模型
    llm_fallback_model: str = "qwen-plus"  # 基于 Qwen3 的 Plus 模型
    llm_max_tokens: int = 4096
    llm_temperature: float = 0.7

    # ===========================================================
    # 外部 API【推荐】- 影响具体功能
    # ===========================================================
    # 高德地图: https://lbs.amap.com/ (POI/天气/路线)
    amap_api_key: str = Field(default="", description="高德地图 API Key【推荐】")
    # 博查搜索: https://open.bochaai.com/ (网络搜索)
    bocha_api_key: str = Field(default="", description="博查搜索 API Key【可选】")

    # ===========================================================
    # 向量数据库【可选】- 使用本地文件存储
    # ===========================================================
    chroma_persist_dir: str = "./data/chroma"
    embedding_model: str = "text-embedding-v3"

    # ===========================================================
    # Langfuse 可观测性【可选】- 不配置也能运行
    # ===========================================================
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = ""  # 空则不启用

    # ===========================================================
    # CORS 配置【可选】
    # ===========================================================
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # ===========================================================
    # 数据库配置【推荐】- 用户系统和数据持久化
    # ===========================================================
    # PostgreSQL: postgresql+asyncpg://user:pass@localhost:5432/travelmind
    database_url: str = Field(default="", description="数据库连接 URL")
    
    # ===========================================================
    # Redis 缓存【可选】- 会话缓存和限流
    # ===========================================================
    # Redis: redis://localhost:6379/0
    redis_url: str = Field(default="", description="Redis 连接 URL")
    
    # ===========================================================
    # JWT 认证【需要数据库】
    # ===========================================================
    secret_key: str = Field(
        default="",
        description="JWT 密钥（生产环境必须设置强密钥）",
    )
    access_token_expire_minutes: int = Field(
        default=60,
        description="Access Token 过期时间（分钟）",
    )
    refresh_token_expire_days: int = Field(
        default=7,
        description="Refresh Token 过期时间（天）",
    )
    
    # ===========================================================
    # 腾讯云短信【可选】- 手机号登录
    # ===========================================================
    tencent_sms_secret_id: str = Field(default="", description="腾讯云 SecretId")
    tencent_sms_secret_key: str = Field(default="", description="腾讯云 SecretKey")
    tencent_sms_app_id: str = Field(default="", description="短信应用 ID")
    tencent_sms_sign_name: str = Field(default="TravelMind", description="短信签名")
    tencent_sms_template_id: str = Field(default="", description="短信模板 ID")
    
    # ===========================================================
    # 管理员密码【推荐】- 后台管理登录
    # ===========================================================
    admin_password: str = Field(
        default="", 
        description="管理员登录密码（设置后可用密码登录后台）"
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """解析 CORS 配置，支持字符串和列表格式"""
        if isinstance(v, str):
            import json

            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",")]
        return v

    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.environment == "production"

    @property
    def langfuse_enabled(self) -> bool:
        """Langfuse 是否已配置"""
        return bool(self.langfuse_public_key and self.langfuse_secret_key and self.langfuse_host)

    @property
    def redis_enabled(self) -> bool:
        """Redis 是否已配置"""
        return bool(self.redis_url)
    
    @property
    def database_enabled(self) -> bool:
        """数据库是否已配置"""
        return bool(self.database_url)
    
    @property
    def auth_enabled(self) -> bool:
        """认证系统是否已配置"""
        return bool(self.secret_key and self.database_url)
    
    @property
    def sms_enabled(self) -> bool:
        """短信服务是否已配置"""
        return bool(
            self.tencent_sms_secret_id and 
            self.tencent_sms_secret_key and 
            self.tencent_sms_app_id
        )

    @property
    def llm_configured(self) -> bool:
        """LLM 是否已配置"""
        return bool(self.dashscope_api_key)


@lru_cache
def get_settings() -> Settings:
    """
    获取配置单例

    使用 lru_cache 确保整个应用生命周期内只创建一个配置实例
    """
    return Settings()


# 导出便捷访问
settings = get_settings()

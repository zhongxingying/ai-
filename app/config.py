from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置，从 .env 读取"""

    # ===== 应用 =====
    app_name: str = "智能办卡 Agent 工作台"
    debug: bool = False

    # ===== LLM =====
    oneapi_api_base: str = "http://localhost:3000/v1"
    oneapi_chat_api_key: str = ""
    oneapi_chat_model: str = "qwen-turbo"

    # ===== 数据库 =====
    database_url: str = "postgresql://user:pass@localhost:5432/aicard"

    # ===== 安全 =====
    secret_key: str = "change-me"
    access_token_expire_minutes: int = 60

    # 告诉 Pydantic 从 .env 读
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,  # 大小写不敏感，ONEAPI_API_BASE 能匹配 oneapi_api_base
        extra="ignore",        # .env 里多余的变量不报错
    )


@lru_cache
def get_settings() -> Settings:
    """单例，只读一次 .env"""
    return Settings()


settings = get_settings()
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./policy_qa.db"
    database_url_sync: str = "sqlite:///./policy_qa.db"

    secret_key: str = "change-this-secret-key-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    llm_provider: str = "dashscope"
    dashscope_api_key: str = ""
    dashscope_model: str = "qwen-plus"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    qianfan_api_key: str = ""
    qianfan_model: str = "deepseek-v3.1-250821"
    qianfan_api_url: str = "https://qianfan.baidubce.com/v2"

    upload_dir: str = "./uploads"
    max_file_size_mb: int = 50

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()

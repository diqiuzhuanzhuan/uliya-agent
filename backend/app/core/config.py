from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[3]
BACKEND_DIR = ROOT_DIR / "backend"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "Uliya Agent"
    api_prefix: str = "/api"
    backend_host: str = Field(default="0.0.0.0", alias="BACKEND_HOST")
    backend_port: int = Field(default=8000, alias="BACKEND_PORT")
    frontend_url: str = Field(default="http://localhost:3000", alias="FRONTEND_URL")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4.1-mini", alias="OPENAI_MODEL")
    database_url: str = Field(
        default="sqlite:///./backend/data/agent.db",
        alias="DATABASE_URL",
    )
    use_real_deepagents: bool = Field(default=False, alias="USE_REAL_DEEPAGENTS")

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def sqlite_path(self) -> Path:
        if self.database_url.startswith("sqlite:///"):
            raw_path = self.database_url.removeprefix("sqlite:///")
            return (ROOT_DIR / raw_path).resolve()
        return BACKEND_DIR / "data" / "agent.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()

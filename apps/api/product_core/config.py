from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///.data/workspace.db"
    artifact_dir: str = ".data/artifacts"
    mode: str = "development"
    session_secret: SecretStr = SecretStr("local-only-change-before-hosting-5af814ded")
    serpapi_api_key: SecretStr = SecretStr("")
    groq_api_key: SecretStr = SecretStr("")
    nvidia_api_key: SecretStr = SecretStr("")
    openai_api_key: SecretStr = SecretStr("")
    anthropic_api_key: SecretStr = SecretStr("")
    gemini_api_key: SecretStr = SecretStr("")
    llm_provider: str = "groq"
    llm_model: str = ""
    serpapi_search_usd: float = 0.01
    llm_input_usd_per_million: float = 0.6
    llm_output_usd_per_million: float = 0.8
    max_run_seconds: int = 600
    max_pdf_pages: int = 100
    oidc_issuer: str = ""
    oidc_client_id: str = ""
    oidc_client_secret: SecretStr = SecretStr("")
    oidc_workspace_id: str = ""
    public_url: str = "http://127.0.0.1:8000"
    allowed_hosts: str = "localhost,127.0.0.1,testserver,api"
    web_dist: str = "apps/web/dist"
    workspace_daily_usd: float = 10
    workspace_storage_bytes: int = 1_073_741_824

    @model_validator(mode="after")
    def validate_deployment(self):
        if self.mode not in {"development", "production"}:
            raise ValueError("MODE must be development or production")
        defaults = {
            "groq": "openai/gpt-oss-120b",
            "nvidia": "meta/llama-3.3-70b-instruct",
            "openai": "gpt-4.1-mini",
            "anthropic": "claude-sonnet-4-6",
            "gemini": "gemini-2.5-flash",
        }
        if self.llm_provider not in defaults:
            raise ValueError("Unsupported LLM provider")
        if not self.llm_model.strip():
            self.llm_model = defaults[self.llm_provider]
        if min(self.serpapi_search_usd, self.llm_input_usd_per_million, self.llm_output_usd_per_million) < 0:
            raise ValueError("Provider accounting rates must be nonnegative")
        if self.mode == "production":
            if len(
                self.session_secret.get_secret_value()
            ) < 32 or self.session_secret.get_secret_value().startswith("local-only"):
                raise ValueError("Production requires a private SESSION_SECRET of at least 32 characters")
            if (
                not self.oidc_issuer.startswith("https://")
                or not self.oidc_client_id
                or not self.public_url.startswith("https://")
            ):
                raise ValueError("Production requires HTTPS public URL and configured OIDC issuer/client")
            if not self.database_url.startswith("postgresql"):
                raise ValueError("Production requires PostgreSQL")
        return self

    def model_api_key(self, provider: str) -> SecretStr:
        """Select exactly the pinned provider; never silently switch paid accounts."""
        if provider not in {"groq", "nvidia", "openai", "anthropic", "gemini"}:
            raise ValueError("Unsupported LLM provider")
        return getattr(self, provider + "_api_key")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def artifact_root() -> Path:
    path = Path(get_settings().artifact_dir).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path

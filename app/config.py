from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    database_url: str
    redis_url: str | None = None

    openai_api_key: str | None = None
    llm_enabled: bool = False
    llm_api_key: str | None = None
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: int = 60
    serpapi_api_key: str | None = None
    tavily_api_key: str | None = None
    tavilty_api_key: str | None = None

    slack_bot_token: str | None = None
    slack_signing_secret: str | None = None
    slack_approval_channel_id: str | None = None

    webflow_api_token: str | None = None
    webflow_site_id: str | None = None
    webflow_collection_id: str | None = None

    default_time_window_hours: int = 24
    max_stories_per_run: int = 10
    min_relevance_score: float = 0.72
    scheduler_enabled: bool = False
    scheduler_interval_minutes: int = 5
    scheduler_topic: str = "AI startup funding"
    scheduler_api_base_url: str = "http://127.0.0.1:8000"
    scheduler_request_timeout_seconds: int = 600
    app_public_base_url: str | None = None
    duplicate_lookback_days: int = 30
    slack_processing_lock_timeout_minutes: int = 15


settings = Settings()

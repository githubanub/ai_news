from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    database_url: str
    redis_url: str

    openai_api_key: str | None = None

    slack_bot_token: str | None = None
    slack_signing_secret: str | None = None
    slack_approval_channel_id: str | None = None

    webflow_api_token: str | None = None
    webflow_site_id: str | None = None
    webflow_collection_id: str | None = None

    default_time_window_hours: int = 24
    max_stories_per_run: int = 10
    min_relevance_score: float = 0.72


settings = Settings()

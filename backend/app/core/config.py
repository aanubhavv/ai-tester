from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "QAForge"
    app_env: str = "development"
    api_prefix: str = "/api/v1"
    debug: bool = False
    screenshots_dir: str = "app/screenshots"
    readiness_max_wait_seconds: float = 30.0
    readiness_final_delay_seconds: float = 0.5
    readiness_wait_for_videos: bool = True
    readiness_videos_timeout_ms: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        case_sensitive=False
    )

settings = Settings()

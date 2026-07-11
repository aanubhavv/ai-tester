from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "QAForge"
    app_env: str = "development"
    api_prefix: str = "/api/v1"
    debug: bool = False
    screenshots_dir: str = "app/screenshots"

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        case_sensitive=False
    )

settings = Settings()

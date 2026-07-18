from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "QAForge"
    app_env: str = "development"
    api_prefix: str = "/api/v1"
    debug: bool = False
    artifacts_dir: str = "artifacts"
    gemini_api_key: str | None = None
    openrouter_api_key: str | None = None
    aws_bedrock_api_key: str | None = None
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_session_token: str | None = None
    aws_region_name: str | None = None
    enable_target_screenshot: bool = False

    # --- Readiness Engine Settings ---
    # These map directly to ReadinessConfig fields and can be overridden
    # via .env for environment-level tuning without code changes.
    readiness_max_wait_seconds: float = 30.0
    readiness_final_delay_seconds: float = 0.5
    readiness_wait_for_videos: bool = True
    readiness_videos_timeout_ms: int = 8000

    # Navigation strategy: "domcontentloaded" (fast, reliable) or
    # "networkidle" (waits for 0 network connections for 500ms).
    # Default changed from "networkidle" to "domcontentloaded" because
    # SPAs with continuous polling/WebSockets cause networkidle to timeout.
    readiness_navigation_wait_strategy: str = "domcontentloaded"

    # Scroll discovery: scrolls the page to trigger lazy-loaded content.
    readiness_enable_scroll_discovery: bool = True
    readiness_scroll_step_pixels: int = 800
    readiness_scroll_pause_ms: int = 400
    readiness_max_scroll_iterations: int = 25

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        case_sensitive=False
    )

settings = Settings()


from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Driver Monitoring System API"
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "sqlite:///./dms.db"
    upload_dir: str = "uploads"
    report_dir: str = "reports"
    target_fps: float = 10.0
    clip_pre_event_sec: float = 5.0
    clip_post_event_sec: float = 5.0


settings = Settings()

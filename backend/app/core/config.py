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
    road_profile: str = "kenya"
    min_scene_reliability: float = 0.35
    primary_stream_for_dms: str = "cabin"
    object_model_path: str = "yolov8n.pt"
    seatbelt_model_path: str = ""
    ttc_warning_sec: float = 2.0


settings = Settings()

from pathlib import Path

from fastapi import FastAPI
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.config import settings
from app.db import Base, engine

app = FastAPI(title="Driver Monitoring System API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
Path(settings.report_dir).mkdir(parents=True, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")
app.mount("/reports", StaticFiles(directory=settings.report_dir), name="reports")


def _ensure_timeline_start_iso_column() -> None:
    """Add timeline_start_iso to trips if missing (e.g. existing DB before this column was added)."""
    if not settings.database_url.startswith("sqlite"):
        return
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT name FROM pragma_table_info('trips') WHERE name = 'timeline_start_iso'")
        )
        if result.fetchone() is None:
            conn.execute(text("ALTER TABLE trips ADD COLUMN timeline_start_iso TEXT"))
            conn.commit()


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_timeline_start_iso_column()


app.include_router(router, prefix="/api")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

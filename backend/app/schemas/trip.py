from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class TripOut(BaseModel):
    id: str
    created_at: datetime
    status: str
    day_folder: str | None = None
    vehicle_id: str | None = None
    driver_id: str | None = None
    duration_seconds: float = 0.0
    sync_offset_seconds: float = 0.0
    progress: float = 0.0
    message: str = ""
    error: str | None = None
    report_pdf_url: str | None = None


class EventOut(BaseModel):
    id: int
    trip_id: str
    type: str
    ts_ms_start: int
    ts_ms_end: int
    severity: float = Field(ge=0.0, le=1.0)
    stream: str
    clip_name: str
    snapshot_url: str | None = None
    clip_url: str | None = None
    metadata: dict = Field(default_factory=dict)


class ScoreOut(BaseModel):
    trip_id: str
    fatigue_score: float
    distraction_score: float
    lane_score: float
    following_distance_score: float
    overall_score: float
    details: dict = Field(default_factory=dict)


class TripCreateResponse(BaseModel):
    trip: TripOut
    uploaded_front_files: int
    uploaded_cabin_files: int


class TripCompleteResponse(BaseModel):
    trip_id: str
    status: str
    message: str


class LegacyJobStatus(BaseModel):
    job_id: str
    status: str
    message: str = ""
    progress: float = 0.0
    report_path: str | None = None
    error: str | None = None

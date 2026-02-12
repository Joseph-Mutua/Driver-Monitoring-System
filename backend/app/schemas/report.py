from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class DetectionEvent(BaseModel):
    event_type: str
    timestamp_sec: float
    clip_name: str
    severity: str = "medium"
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    details: dict[str, float | str] = Field(default_factory=dict)


class ClipSummary(BaseModel):
    clip_name: str
    camera: str
    duration_sec: float
    event_counts: dict[str, int] = Field(default_factory=dict)


class AnalysisReport(BaseModel):
    job_id: str
    day_folder: str
    created_at: datetime
    total_clips: int
    total_duration_sec: float
    overall_risk_score: float
    kpi: dict[str, float | int]
    events: list[DetectionEvent]
    clip_summaries: list[ClipSummary]
    limitations: list[str] = Field(default_factory=list)


class JobStatus(BaseModel):
    job_id: str
    status: str
    message: str = ""
    progress: float = 0.0
    report_path: str | None = None
    error: str | None = None

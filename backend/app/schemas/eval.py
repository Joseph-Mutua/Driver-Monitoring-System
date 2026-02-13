from __future__ import annotations

from pydantic import BaseModel, Field


class EvalRunRequest(BaseModel):
    ground_truth_path: str
    predictions_path: str
    iou_threshold: float = Field(default=0.30, ge=0.0, le=1.0)
    tolerance_ms: int = Field(default=1200, ge=0)
    bins: int = Field(default=10, ge=2, le=50)


class EvalRangeRequest(BaseModel):
    ground_truth_path: str
    date_from: str | None = None  # YYYY-MM-DD
    date_to: str | None = None  # YYYY-MM-DD
    iou_threshold: float = Field(default=0.30, ge=0.0, le=1.0)
    tolerance_ms: int = Field(default=1200, ge=0)
    bins: int = Field(default=10, ge=2, le=50)


class EvalReportFileLinks(BaseModel):
    summary_json: str
    evaluation_json: str
    metrics_by_event_csv: str
    metrics_by_stream_csv: str
    metrics_by_scenario_csv: str
    threshold_sweep_csv: str
    reliability_diagram_png: str
    threshold_curve_png: str


class EvalRunResponse(BaseModel):
    report_id: str
    output_dir: str
    links: EvalReportFileLinks
    summary: dict
    selected_trip_ids: list[str] = Field(default_factory=list)


class EvalReportEntry(BaseModel):
    report_id: str
    created_at: str
    summary_url: str


class EvalReportsResponse(BaseModel):
    reports: list[EvalReportEntry] = Field(default_factory=list)

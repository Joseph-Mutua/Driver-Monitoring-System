from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.models import Event, Score, Trip
from app.schemas.trip import (
    BulkDeleteRequest,
    BulkDeleteResponse,
    EventOut,
    LegacyJobStatus,
    ScoreOut,
    TripCompleteResponse,
    TripCreateResponse,
    TripOut,
)
from app.schemas.eval import EvalRangeRequest, EvalReportsResponse, EvalRunRequest, EvalRunResponse
from app.schemas.ml import (
    MlPipelineActionResponse,
    MlPipelineJob,
    MlPipelineJobList,
    MlPipelineLogResponse,
    MlPipelineRunRequest,
)
from app.services.evaluation_service import list_eval_reports, run_eval_for_date_range, run_eval_from_paths
from app.services.ml_pipeline_service import ml_pipeline_service
from app.services.video_processor import process_trip
from app.utils.file_parser import parse_clip_name

router = APIRouter()


@router.post("/evaluation/run", response_model=EvalRunResponse)
def run_evaluation(body: EvalRunRequest) -> EvalRunResponse:
    return run_eval_from_paths(
        ground_truth_path=body.ground_truth_path,
        predictions_path=body.predictions_path,
        iou_threshold=body.iou_threshold,
        tolerance_ms=body.tolerance_ms,
        bins=body.bins,
    )


@router.post("/evaluation/run-range", response_model=EvalRunResponse)
def run_evaluation_range(body: EvalRangeRequest, db: Session = Depends(get_db)) -> EvalRunResponse:
    return run_eval_for_date_range(
        db=db,
        ground_truth_path=body.ground_truth_path,
        date_from=body.date_from,
        date_to=body.date_to,
        iou_threshold=body.iou_threshold,
        tolerance_ms=body.tolerance_ms,
        bins=body.bins,
    )


@router.get("/evaluation/reports", response_model=EvalReportsResponse)
def get_evaluation_reports(limit: int = 40) -> EvalReportsResponse:
    return EvalReportsResponse(reports=list_eval_reports(limit=max(1, min(limit, 200))))


@router.post("/ml/pipeline/run", response_model=MlPipelineJob)
def run_ml_pipeline(body: MlPipelineRunRequest) -> MlPipelineJob:
    try:
        return ml_pipeline_service.run(body)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/ml/pipeline/jobs", response_model=MlPipelineJobList)
def list_ml_jobs() -> MlPipelineJobList:
    return MlPipelineJobList(jobs=ml_pipeline_service.list_jobs())


@router.get("/ml/pipeline/jobs/{job_id}", response_model=MlPipelineJob)
def get_ml_job(job_id: str) -> MlPipelineJob:
    job = ml_pipeline_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="ML pipeline job not found")
    return job


@router.get("/ml/pipeline/jobs/{job_id}/log", response_model=MlPipelineLogResponse)
def get_ml_job_log(job_id: str) -> MlPipelineLogResponse:
    job = ml_pipeline_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="ML pipeline job not found")
    return MlPipelineLogResponse(job_id=job_id, log_tail=ml_pipeline_service.read_log_tail(job_id))


@router.post("/ml/pipeline/jobs/{job_id}/cancel", response_model=MlPipelineActionResponse)
def cancel_ml_job(job_id: str) -> MlPipelineActionResponse:
    job = ml_pipeline_service.cancel_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="ML pipeline job not found")
    return MlPipelineActionResponse(job_id=job_id, status=job.status, message=job.message)


@router.post("/ml/pipeline/jobs/{job_id}/retry", response_model=MlPipelineJob)
def retry_ml_job(job_id: str) -> MlPipelineJob:
    new_job = ml_pipeline_service.retry_job(job_id)
    if not new_job:
        raise HTTPException(status_code=404, detail="ML pipeline job not found")
    return new_job


@router.get("/ml/pipeline/jobs/{job_id}/artifacts/{artifact_key}")
def download_ml_artifact(job_id: str, artifact_key: str):
    artifact = ml_pipeline_service.artifact_path(job_id, artifact_key)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return FileResponse(path=str(artifact), filename=artifact.name)


def _trip_to_out(trip: Trip) -> TripOut:
    return TripOut(
        id=trip.id,
        created_at=trip.created_at,
        status=trip.status,
        day_folder=trip.day_folder,
        vehicle_id=trip.vehicle_id,
        driver_id=trip.driver_id,
        duration_seconds=trip.duration_seconds,
        sync_offset_seconds=trip.sync_offset_seconds,
        progress=trip.progress,
        message=trip.message,
        error=trip.error,
        report_pdf_url=trip.report_pdf_url,
    )


@router.post("/trips", response_model=TripCreateResponse)
async def create_trip(
    day_folder: str = Form(""),
    driver_id: str | None = Form(None),
    vehicle_id: str | None = Form(None),
    front_files: list[UploadFile] = File(...),
    rear_files: list[UploadFile] | None = File(default=None),
    cabin_files: list[UploadFile] | None = File(default=None),
    db: Session = Depends(get_db),
) -> TripCreateResponse:
    valid_front = [f for f in front_files if f.filename and f.filename.lower().endswith(".mp4")]
    valid_rear = [f for f in (rear_files or []) if f.filename and f.filename.lower().endswith(".mp4")]
    valid_cabin = [f for f in (cabin_files or []) if f.filename and f.filename.lower().endswith(".mp4")]

    if not valid_front:
        raise HTTPException(status_code=400, detail="At least one front video is required")

    trip_id = str(uuid.uuid4())
    trip_root = Path(settings.upload_dir) / "trips" / trip_id
    front_dir = trip_root / "front"
    rear_dir = trip_root / "rear"
    cabin_dir = trip_root / "cabin"
    front_dir.mkdir(parents=True, exist_ok=True)
    rear_dir.mkdir(parents=True, exist_ok=True)
    cabin_dir.mkdir(parents=True, exist_ok=True)

    for upload in valid_front:
        out = front_dir / Path(upload.filename).name
        with out.open("wb") as handle:
            shutil.copyfileobj(upload.file, handle)

    for upload in valid_rear:
        out = rear_dir / Path(upload.filename).name
        with out.open("wb") as handle:
            shutil.copyfileobj(upload.file, handle)

    for upload in valid_cabin:
        out = cabin_dir / Path(upload.filename).name
        with out.open("wb") as handle:
            shutil.copyfileobj(upload.file, handle)

    front_first = sorted(front_dir.glob("*.mp4"))[0]
    secondary_first = None
    if valid_rear:
        secondary_first = sorted(rear_dir.glob("*.mp4"))[0]
    elif valid_cabin:
        secondary_first = sorted(cabin_dir.glob("*.mp4"))[0]

    trip = Trip(
        id=trip_id,
        status="uploaded",
        day_folder=day_folder or None,
        driver_id=driver_id,
        vehicle_id=vehicle_id,
        front_video_url=f"/uploads/trips/{trip_id}/front/{front_first.name}",
        cabin_video_url=(
            f"/uploads/trips/{trip_id}/rear/{secondary_first.name}"
            if (secondary_first and valid_rear)
            else (f"/uploads/trips/{trip_id}/cabin/{secondary_first.name}" if secondary_first else None)
        ),
        upload_dir=str(trip_root.resolve()),
        message="Upload complete",
        progress=0.0,
    )
    db.add(trip)
    db.commit()
    db.refresh(trip)

    return TripCreateResponse(
        trip=_trip_to_out(trip),
        uploaded_front_files=len(valid_front),
        uploaded_cabin_files=len(valid_rear) + len(valid_cabin),
    )


@router.post("/trips/{trip_id}/complete-upload", response_model=TripCompleteResponse)
def complete_upload(trip_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)) -> TripCompleteResponse:
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    if trip.status in {"processing", "done"}:
        return TripCompleteResponse(trip_id=trip.id, status=trip.status, message="Trip already queued or finished")

    trip.status = "processing"
    trip.message = "Queued for analysis"
    trip.progress = 0.5
    db.commit()

    background_tasks.add_task(process_trip, trip_id)
    return TripCompleteResponse(trip_id=trip.id, status=trip.status, message=trip.message)


def _delete_trip_files(trip_id: str, upload_dir_path: str | None) -> None:
    """Remove on-disk upload and report directories for a trip."""
    if upload_dir_path:
        try:
            shutil.rmtree(upload_dir_path, ignore_errors=True)
        except OSError:
            pass
    report_path = Path(settings.report_dir) / trip_id
    try:
        shutil.rmtree(report_path, ignore_errors=True)
    except OSError:
        pass


@router.delete("/trips/{trip_id}")
def delete_trip(trip_id: str, db: Session = Depends(get_db)) -> dict:
    """Delete a single trip and all its data (DB + uploads + reports)."""
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    upload_dir_path = trip.upload_dir
    db.delete(trip)
    db.commit()
    _delete_trip_files(trip_id, upload_dir_path)
    return {"deleted": trip_id}


@router.post("/trips/bulk-delete", response_model=BulkDeleteResponse)
def bulk_delete_trips(body: BulkDeleteRequest, db: Session = Depends(get_db)) -> BulkDeleteResponse:
    """Delete multiple trips and all their data. Returns deleted ids and any failures."""
    deleted: list[str] = []
    failed: list[dict] = []
    for trip_id in body.trip_ids:
        trip = db.get(Trip, trip_id)
        if not trip:
            failed.append({"id": trip_id, "detail": "Trip not found"})
            continue
        upload_dir_path = trip.upload_dir
        try:
            db.delete(trip)
            db.commit()
            _delete_trip_files(trip_id, upload_dir_path)
            deleted.append(trip_id)
        except Exception as e:
            db.rollback()
            failed.append({"id": trip_id, "detail": str(e)})
    return BulkDeleteResponse(deleted=deleted, failed=failed)


@router.get("/trips", response_model=list[TripOut])
def list_trips(limit: int = 50, db: Session = Depends(get_db)) -> list[TripOut]:
    rows = db.execute(select(Trip).order_by(desc(Trip.created_at)).limit(max(1, min(limit, 500)))).scalars().all()
    return [_trip_to_out(t) for t in rows]


@router.get("/trips/{trip_id}", response_model=TripOut)
def get_trip(trip_id: str, db: Session = Depends(get_db)) -> TripOut:
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return _trip_to_out(trip)


def _event_display_time(timeline_start_iso: str | None, offset_ms: int) -> str | None:
    """Format event time as in video overlay: 2023-11-01, 21:49:25"""
    if not timeline_start_iso:
        return None
    try:
        base = datetime.fromisoformat(timeline_start_iso.replace("Z", "+00:00"))
        dt = base + timedelta(milliseconds=offset_ms)
        return dt.strftime("%Y-%m-%d, %H:%M:%S")
    except (ValueError, TypeError):
        return None


@router.get("/trips/{trip_id}/events", response_model=list[EventOut])
def get_trip_events(trip_id: str, db: Session = Depends(get_db)) -> list[EventOut]:
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    rows = (
        db.execute(select(Event).where(Event.trip_id == trip_id).order_by(Event.ts_ms_start.asc())).scalars().all()
    )
    out: list[EventOut] = []
    for row in rows:
        try:
            metadata = json.loads(row.metadata_json)
        except Exception:
            metadata = {}
        out.append(
            EventOut(
                id=row.id,
                trip_id=row.trip_id,
                type=row.type,
                ts_ms_start=row.ts_ms_start,
                ts_ms_end=row.ts_ms_end,
                severity=row.severity,
                stream=row.stream,
                clip_name=row.clip_name,
                snapshot_url=row.snapshot_url,
                clip_url=row.clip_url,
                metadata=metadata,
                start_display_time=_event_display_time(trip.timeline_start_iso, row.ts_ms_start),
                end_display_time=_event_display_time(trip.timeline_start_iso, row.ts_ms_end),
            )
        )
    return out


@router.get("/trips/{trip_id}/scores", response_model=ScoreOut)
def get_trip_scores(trip_id: str, db: Session = Depends(get_db)) -> ScoreOut:
    score = db.get(Score, trip_id)
    if not score:
        raise HTTPException(status_code=404, detail="Scores not found")

    try:
        details = json.loads(score.details_json)
    except Exception:
        details = {}

    return ScoreOut(
        trip_id=score.trip_id,
        fatigue_score=score.fatigue_score,
        distraction_score=score.distraction_score,
        lane_score=score.lane_score,
        following_distance_score=score.following_distance_score,
        overall_score=score.overall_score,
        details=details,
    )


@router.post("/analyze/day", response_model=LegacyJobStatus)
async def analyze_day_compat(
    background_tasks: BackgroundTasks,
    day_folder: str = Form(...),
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
) -> LegacyJobStatus:
    front: list[UploadFile] = []
    rear: list[UploadFile] = []

    for file in files:
        if not file.filename or not file.filename.lower().endswith(".mp4"):
            continue
        parsed = parse_clip_name(file.filename)
        if parsed.stream_hint == "rear":
            rear.append(file)
        else:
            front.append(file)

    if not front:
        raise HTTPException(status_code=400, detail="No front MP4 files found")

    response = await create_trip(
        day_folder=day_folder,
        driver_id=None,
        vehicle_id=None,
        front_files=front,
        rear_files=rear,
        cabin_files=[],
        db=db,
    )
    complete_upload(response.trip.id, background_tasks=background_tasks, db=db)

    return LegacyJobStatus(
        job_id=response.trip.id,
        status="processing",
        message="Queued for analysis",
        progress=0.5,
        report_path=None,
        error=None,
    )


@router.get("/jobs/{job_id}", response_model=LegacyJobStatus)
def legacy_job(job_id: str, db: Session = Depends(get_db)) -> LegacyJobStatus:
    trip = db.get(Trip, job_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Job not found")
    return LegacyJobStatus(
        job_id=trip.id,
        status=trip.status,
        message=trip.message,
        progress=trip.progress,
        report_path=trip.report_json_url,
        error=trip.error,
    )


@router.get("/reports/{job_id}")
def legacy_report(job_id: str, db: Session = Depends(get_db)) -> dict:
    trip = db.get(Trip, job_id)
    if not trip or not trip.report_json_url:
        raise HTTPException(status_code=404, detail="Report not found")

    report_path = Path(settings.report_dir) / job_id / "report.json"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report artifact missing")
    return json.loads(report_path.read_text(encoding="utf-8"))

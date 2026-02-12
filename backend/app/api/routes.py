from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
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
from app.services.video_processor import process_trip
from app.utils.file_parser import parse_clip_name

router = APIRouter()


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
    cabin_files: list[UploadFile] | None = File(default=None),
    db: Session = Depends(get_db),
) -> TripCreateResponse:
    valid_front = [f for f in front_files if f.filename and f.filename.lower().endswith(".mp4")]
    valid_cabin = [f for f in (cabin_files or []) if f.filename and f.filename.lower().endswith(".mp4")]

    if not valid_front:
        raise HTTPException(status_code=400, detail="At least one front video is required")

    trip_id = str(uuid.uuid4())
    trip_root = Path(settings.upload_dir) / "trips" / trip_id
    front_dir = trip_root / "front"
    cabin_dir = trip_root / "cabin"
    front_dir.mkdir(parents=True, exist_ok=True)
    cabin_dir.mkdir(parents=True, exist_ok=True)

    for upload in valid_front:
        out = front_dir / Path(upload.filename).name
        with out.open("wb") as handle:
            shutil.copyfileobj(upload.file, handle)

    for upload in valid_cabin:
        out = cabin_dir / Path(upload.filename).name
        with out.open("wb") as handle:
            shutil.copyfileobj(upload.file, handle)

    front_first = sorted(front_dir.glob("*.mp4"))[0]
    cabin_first = sorted(cabin_dir.glob("*.mp4"))[0] if valid_cabin else None

    trip = Trip(
        id=trip_id,
        status="uploaded",
        day_folder=day_folder or None,
        driver_id=driver_id,
        vehicle_id=vehicle_id,
        front_video_url=f"/uploads/trips/{trip_id}/front/{front_first.name}",
        cabin_video_url=(f"/uploads/trips/{trip_id}/cabin/{cabin_first.name}" if cabin_first else None),
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
        uploaded_cabin_files=len(valid_cabin),
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
    cabin: list[UploadFile] = []

    for file in files:
        if not file.filename or not file.filename.lower().endswith(".mp4"):
            continue
        parsed = parse_clip_name(file.filename)
        if parsed.stream_hint == "rear":
            cabin.append(file)
        else:
            front.append(file)

    if not front:
        raise HTTPException(status_code=400, detail="No front MP4 files found")

    response = await create_trip(
        day_folder=day_folder,
        driver_id=None,
        vehicle_id=None,
        front_files=front,
        cabin_files=cabin,
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

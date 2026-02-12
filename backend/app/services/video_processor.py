from __future__ import annotations

import json
from collections import Counter, deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2
from fpdf import FPDF
from app.core.config import settings
from app.db import SessionLocal
from app.detectors.vision import (
    DriverFaceMonitor,
    LaneDeviationDetector,
    ObjectDetector,
    SeatbeltDetector,
    detect_phone_obstruction_tailgating,
)
from app.models import Event, Score, Trip
from app.utils.file_parser import clip_sort_key, parse_clip_name


EVENT_RULES: dict[str, dict[str, int]] = {
    "driver_fatigue": {"min_duration_ms": 15_000, "cooldown_ms": 20_000},
    "microsleep": {"min_duration_ms": 1_500, "cooldown_ms": 8_000},
    "distracted_driving": {"min_duration_ms": 2_000, "cooldown_ms": 7_000},
    "lane_deviation": {"min_duration_ms": 700, "cooldown_ms": 4_000},
    "mobile_phone_use": {"min_duration_ms": 1_000, "cooldown_ms": 6_000},
    "seatbelt_not_worn": {"min_duration_ms": 3_000, "cooldown_ms": 20_000},
    "obstruction_ahead": {"min_duration_ms": 800, "cooldown_ms": 4_000},
    "tailgating": {"min_duration_ms": 1_500, "cooldown_ms": 5_000},
}


@dataclass
class Segment:
    path: Path
    stream: str
    start_sec: int


class DebounceEngine:
    def __init__(self) -> None:
        self.state: dict[str, dict[str, float]] = {
            k: {"active_ms": 0.0, "last_emit_ms": -1e9, "ema": 0.0, "start_ms": 0.0} for k in EVENT_RULES
        }

    def update(
        self,
        event_type: str,
        active: bool,
        conf: float,
        now_ms: int,
        delta_ms: int,
        ctx: dict[str, Any],
    ) -> dict[str, Any] | None:
        rule = EVENT_RULES[event_type]
        st = self.state[event_type]

        if active:
            if st["active_ms"] <= 0:
                st["start_ms"] = now_ms - delta_ms
            st["active_ms"] += delta_ms
            st["ema"] = 0.75 * st["ema"] + 0.25 * conf if st["ema"] > 0 else conf
        else:
            st["active_ms"] = max(0.0, st["active_ms"] - delta_ms)
            st["ema"] *= 0.85

        can_emit = (
            st["active_ms"] >= rule["min_duration_ms"]
            and now_ms - st["last_emit_ms"] >= rule["cooldown_ms"]
            and st["ema"] >= 0.45
        )
        if not can_emit:
            return None

        st["last_emit_ms"] = float(now_ms)
        return {
            "type": event_type,
            "ts_ms_start": int(st["start_ms"]),
            "ts_ms_end": int(now_ms),
            "severity": float(min(1.0, max(0.0, st["ema"]))),
            **ctx,
        }


def _ordered_segments(folder: Path, stream: str) -> list[Segment]:
    if not folder.exists():
        return []
    files = [p for p in folder.glob("*.mp4") if p.is_file()]
    files.sort(key=lambda p: clip_sort_key(p.name))
    segments: list[Segment] = []
    for p in files:
        parsed = parse_clip_name(p.name)
        segments.append(Segment(path=p, stream=stream, start_sec=parsed.seconds_of_day))
    return segments


def _estimate_sync_offset(front: list[Segment], cabin: list[Segment]) -> float:
    if not front or not cabin:
        return 0.0
    return float(cabin[0].start_sec - front[0].start_sec)


def _video_meta(path: Path) -> tuple[float, float]:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return 25.0, 0.0
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    cap.release()
    return float(fps), float(frames / max(fps, 1.0))


def _save_snapshot(video_path: Path, sec: float, out_path: Path, label: str) -> bool:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return False
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_idx = max(0, int(sec * fps))
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        return False
    cv2.putText(frame, label, (24, 42), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2, cv2.LINE_AA)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    return bool(cv2.imwrite(str(out_path), frame))


def _save_clip(video_path: Path, start_sec: float, end_sec: float, out_path: Path, label: str) -> bool:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return False
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1280)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 720)

    start_frame = max(0, int(start_sec * fps))
    end_frame = max(start_frame + 1, int(end_sec * fps))
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Use H.264 (avc1) for browser playback; mp4v is often not supported in Chrome/Firefox
    fourcc = cv2.VideoWriter_fourcc(*"avc1")
    writer = cv2.VideoWriter(str(out_path), fourcc, fps, (width, height))
    if not writer.isOpened():
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(out_path), fourcc, fps, (width, height))

    idx = start_frame
    while idx <= end_frame:
        ok, frame = cap.read()
        if not ok:
            break
        cv2.putText(frame, label, (24, 42), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2, cv2.LINE_AA)
        writer.write(frame)
        idx += 1

    cap.release()
    writer.release()
    return out_path.exists()


def _score_trip(events: list[dict[str, Any]], duration_seconds: float) -> dict[str, Any]:
    cat_events = {
        "fatigue": {"driver_fatigue", "microsleep"},
        "distraction": {"distracted_driving", "mobile_phone_use", "seatbelt_not_worn"},
        "lane": {"lane_deviation"},
        "following": {"tailgating", "obstruction_ahead"},
    }
    weights = {
        "driver_fatigue": 2.2,
        "microsleep": 3.0,
        "distracted_driving": 1.9,
        "mobile_phone_use": 2.0,
        "seatbelt_not_worn": 1.6,
        "lane_deviation": 1.5,
        "tailgating": 1.8,
        "obstruction_ahead": 1.4,
    }

    norm = max(1.0, duration_seconds / 3600.0)
    penalties = {"fatigue": 0.0, "distraction": 0.0, "lane": 0.0, "following": 0.0}

    for ev in events:
        duration_s = max(0.5, (ev["ts_ms_end"] - ev["ts_ms_start"]) / 1000.0)
        penalty = weights.get(ev["type"], 1.0) * ev["severity"] * duration_s
        for cat, members in cat_events.items():
            if ev["type"] in members:
                penalties[cat] += penalty

    fatigue_score = max(0.0, 100.0 - penalties["fatigue"] / norm)
    distraction_score = max(0.0, 100.0 - penalties["distraction"] / norm)
    lane_score = max(0.0, 100.0 - penalties["lane"] / norm)
    following_score = max(0.0, 100.0 - penalties["following"] / norm)
    overall = round((fatigue_score + distraction_score + lane_score + following_score) / 4.0, 2)

    return {
        "fatigue_score": round(fatigue_score, 2),
        "distraction_score": round(distraction_score, 2),
        "lane_score": round(lane_score, 2),
        "following_distance_score": round(following_score, 2),
        "overall_score": overall,
        "details": {
            "penalties": penalties,
            "event_counts": dict(Counter(ev["type"] for ev in events)),
            "total_events": len(events),
            "duration_seconds": round(duration_seconds, 2),
        },
    }


def _write_pdf_summary(trip: Trip, scores: dict[str, Any], events: list[dict[str, Any]], out_pdf: Path) -> None:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Driver Monitoring Trip Report", ln=1)

    pdf.set_font("Helvetica", size=11)
    pdf.cell(0, 8, f"Trip ID: {trip.id}", ln=1)
    pdf.cell(0, 8, f"Status: {trip.status}", ln=1)
    pdf.cell(0, 8, f"Driver: {trip.driver_id or '-'}", ln=1)
    pdf.cell(0, 8, f"Vehicle: {trip.vehicle_id or '-'}", ln=1)
    pdf.cell(0, 8, f"Duration: {trip.duration_seconds:.1f} sec", ln=1)

    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Scores", ln=1)
    pdf.set_font("Helvetica", size=11)
    pdf.cell(0, 7, f"Overall: {scores['overall_score']}", ln=1)
    pdf.cell(0, 7, f"Fatigue: {scores['fatigue_score']}", ln=1)
    pdf.cell(0, 7, f"Distraction: {scores['distraction_score']}", ln=1)
    pdf.cell(0, 7, f"Lane: {scores['lane_score']}", ln=1)
    pdf.cell(0, 7, f"Following Distance: {scores['following_distance_score']}", ln=1)

    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Top Events", ln=1)
    pdf.set_font("Helvetica", size=10)

    for ev in events[:20]:
        line = f"{ev['type']} | {ev['clip_name']} | {ev['ts_ms_start']}ms | sev={ev['severity']:.2f}"
        pdf.cell(0, 6, line[:110], ln=1)

    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(out_pdf))


def process_trip(trip_id: str) -> None:
    db = SessionLocal()
    try:
        trip = db.get(Trip, trip_id)
        if not trip:
            return

        trip.status = "processing"
        trip.started_at = datetime.utcnow()
        trip.progress = 1.0
        trip.message = "Assembling trip segments"
        db.commit()

        trip_root = Path(trip.upload_dir)
        front_segments = _ordered_segments(trip_root / "front", "front")
        cabin_segments = _ordered_segments(trip_root / "cabin", "cabin")
        sync_offset = _estimate_sync_offset(front_segments, cabin_segments)
        trip.sync_offset_seconds = sync_offset

        if not front_segments and not cabin_segments:
            trip.status = "failed"
            trip.error = "No video segments found"
            trip.message = "Trip processing failed"
            db.commit()
            return

        all_segments = front_segments + cabin_segments
        all_segments.sort(key=lambda s: s.start_sec)

        face = DriverFaceMonitor(settings.target_fps)
        lane = LaneDeviationDetector(settings.target_fps)
        seatbelt = SeatbeltDetector()
        obj = ObjectDetector()
        limitations = [*face.limitations, *seatbelt.limitations, *obj.limitations]

        debouncer = DebounceEngine()
        perclos_window: deque[tuple[int, int]] = deque()
        closed_streak_ms = 0

        events: list[dict[str, Any]] = []
        total_duration = 0.0
        processed_segments = 0

        for segment in all_segments:
            processed_segments += 1
            trip.progress = 5.0 + (processed_segments / max(len(all_segments), 1)) * 75.0
            trip.message = f"Analyzing {segment.path.name} ({processed_segments}/{len(all_segments)})"
            db.commit()

            cap = cv2.VideoCapture(str(segment.path))
            if not cap.isOpened():
                continue

            fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
            duration = float(frame_count / max(fps, 1.0))
            total_duration += duration

            sample_step = max(1, int(fps / settings.target_fps))
            frame_idx = 0
            yolo_every = 2

            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                if frame_idx % sample_step != 0:
                    frame_idx += 1
                    continue

                ts_local_ms = int((frame_idx / max(fps, 1.0)) * 1000)
                ts_global_sec = segment.start_sec + (ts_local_ms / 1000.0)
                if segment.stream == "cabin":
                    ts_global_sec -= sync_offset
                now_ms = int(ts_global_sec * 1000)
                delta_ms = int(1000 / settings.target_fps)

                raw: dict[str, tuple[bool, float, dict[str, Any]]] = {}
                dets: list[dict] = []

                if frame_idx % (sample_step * yolo_every) == 0:
                    dets = obj.detect(frame)

                if segment.stream == "cabin" or (segment.stream == "front" and not cabin_segments):
                    face_metrics = face.detect_metrics(frame)
                    seatbelt_missing, seatbelt_conf = seatbelt.detect(frame)
                    perclos_window.append((now_ms, 1 if face_metrics["eyes_closed"] else 0))
                    while perclos_window and now_ms - perclos_window[0][0] > 60_000:
                        perclos_window.popleft()

                    closed_ratio = sum(v for _, v in perclos_window) / max(len(perclos_window), 1)
                    fatigue_conf = min(1.0, max(face_metrics["fatigue_conf"], (closed_ratio - 0.25) * 2.0))
                    fatigue_active = closed_ratio > 0.35

                    if face_metrics["eyes_closed"]:
                        closed_streak_ms += delta_ms
                    else:
                        closed_streak_ms = 0

                    microsleep_active = closed_streak_ms >= 1500
                    microsleep_conf = min(1.0, closed_streak_ms / 3000)

                    scene = detect_phone_obstruction_tailgating(dets, frame.shape) if dets else {}
                    raw["driver_fatigue"] = (
                        fatigue_active,
                        fatigue_conf,
                        {"perclos": round(closed_ratio, 3)},
                    )
                    raw["microsleep"] = (microsleep_active, microsleep_conf, {"closed_ms": closed_streak_ms})
                    raw["distracted_driving"] = (
                        bool(face_metrics["distracted"]),
                        float(face_metrics["distracted_conf"]),
                        {"yaw_ratio": round(face_metrics["yaw_ratio"], 3)},
                    )
                    raw["mobile_phone_use"] = (
                        bool(scene.get("phone", False)),
                        float(scene.get("phone_conf", 0.0)),
                        {},
                    )
                    raw["seatbelt_not_worn"] = (seatbelt_missing, seatbelt_conf, {})

                if segment.stream == "front":
                    lane_dev, lane_conf, lane_offset = lane.detect(frame)
                    scene = detect_phone_obstruction_tailgating(dets, frame.shape) if dets else {}
                    raw["lane_deviation"] = (lane_dev, lane_conf, {"offset_ratio": round(lane_offset, 3)})
                    raw["obstruction_ahead"] = (
                        bool(scene.get("obstruction", False)),
                        float(scene.get("obstruction_conf", 0.0)),
                        {"lead_distance_m": round(float(scene.get("lead_distance_m", 0.0)), 2)},
                    )
                    raw["tailgating"] = (
                        bool(scene.get("tailgating", False)),
                        float(scene.get("tailgating_conf", 0.0)),
                        {"lead_distance_m": round(float(scene.get("lead_distance_m", 0.0)), 2)},
                    )

                for event_type, (active, conf, metadata) in raw.items():
                    emitted = debouncer.update(
                        event_type=event_type,
                        active=active,
                        conf=conf,
                        now_ms=now_ms,
                        delta_ms=delta_ms,
                        ctx={
                            "stream": segment.stream,
                            "clip_name": segment.path.name,
                            "video_path": str(segment.path),
                            "metadata": metadata,
                            "local_ts_sec": round(ts_local_ms / 1000.0, 3),
                        },
                    )
                    if emitted:
                        events.append(emitted)

                frame_idx += 1

            cap.release()

        trip.duration_seconds = round(total_duration, 2)

        report_root = Path(settings.report_dir) / trip_id
        snaps_dir = report_root / "snapshots"
        clips_dir = report_root / "clips"

        db.query(Event).filter(Event.trip_id == trip_id).delete()

        for idx, ev in enumerate(events, start=1):
            center_sec = (ev["ts_ms_start"] + ev["ts_ms_end"]) / 2000.0
            local_center = max(0.0, float(ev.get("local_ts_sec", center_sec)))

            snap_file = snaps_dir / f"event_{idx:04d}.jpg"
            clip_file = clips_dir / f"event_{idx:04d}.mp4"
            label = ev["type"].replace("_", " ").upper()

            video_path = Path(ev["video_path"])
            _save_snapshot(video_path, local_center, snap_file, label)
            _save_clip(
                video_path,
                max(0.0, local_center - settings.clip_pre_event_sec),
                local_center + settings.clip_post_event_sec,
                clip_file,
                label,
            )

            event_row = Event(
                trip_id=trip_id,
                type=ev["type"],
                ts_ms_start=ev["ts_ms_start"],
                ts_ms_end=ev["ts_ms_end"],
                severity=round(float(ev["severity"]), 3),
                stream=ev["stream"],
                clip_name=ev["clip_name"],
                snapshot_url=f"/reports/{trip_id}/snapshots/{snap_file.name}" if snap_file.exists() else None,
                clip_url=f"/reports/{trip_id}/clips/{clip_file.name}" if clip_file.exists() else None,
                metadata_json=json.dumps(ev["metadata"]),
            )
            db.add(event_row)

        score_dict = _score_trip(events, total_duration)
        existing_score = db.get(Score, trip_id)
        if existing_score:
            db.delete(existing_score)
            db.flush()

        db.add(
            Score(
                trip_id=trip_id,
                fatigue_score=score_dict["fatigue_score"],
                distraction_score=score_dict["distraction_score"],
                lane_score=score_dict["lane_score"],
                following_distance_score=score_dict["following_distance_score"],
                overall_score=score_dict["overall_score"],
                details_json=json.dumps({**score_dict["details"], "limitations": limitations}),
            )
        )

        trip.progress = 90.0
        trip.message = "Generating reports"
        db.commit()

        events_for_report = [
            {
                "type": ev["type"],
                "ts_ms_start": ev["ts_ms_start"],
                "ts_ms_end": ev["ts_ms_end"],
                "severity": ev["severity"],
                "clip_name": ev["clip_name"],
                "stream": ev["stream"],
                "metadata": ev["metadata"],
            }
            for ev in events
        ]
        report_json = {
            "trip_id": trip_id,
            "generated_at": datetime.utcnow().isoformat(),
            "trip": {
                "driver_id": trip.driver_id,
                "vehicle_id": trip.vehicle_id,
                "duration_seconds": trip.duration_seconds,
                "sync_offset_seconds": trip.sync_offset_seconds,
                "day_folder": trip.day_folder,
            },
            "scores": score_dict,
            "events": events_for_report,
            "limitations": limitations,
        }

        report_json_path = report_root / "report.json"
        report_json_path.parent.mkdir(parents=True, exist_ok=True)
        report_json_path.write_text(json.dumps(report_json, indent=2), encoding="utf-8")

        pdf_path = report_root / "report.pdf"
        _write_pdf_summary(trip, score_dict, events_for_report, pdf_path)

        trip.report_json_url = f"/reports/{trip_id}/report.json"
        trip.report_pdf_url = f"/reports/{trip_id}/report.pdf" if pdf_path.exists() else None
        trip.status = "done"
        trip.progress = 100.0
        trip.message = "Analysis complete"
        trip.error = None
        db.commit()

    except Exception as exc:  # pragma: no cover
        trip = db.get(Trip, trip_id)
        if trip:
            trip.status = "failed"
            trip.error = str(exc)
            trip.message = "Trip processing failed"
            trip.progress = 100.0
            db.commit()
    finally:
        db.close()

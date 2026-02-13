from __future__ import annotations

from pathlib import Path

from app.eval.schemas import EventRecord


def _norm_stream(value: str | None) -> str:
    if not value:
        return "unknown"
    value = value.lower().strip()
    if value in {"front", "rear", "cabin"}:
        return value
    return "unknown"


def _norm_scenario(value: str | None) -> str:
    if not value:
        return "unknown"
    value = value.lower().strip()
    if value in {"day", "dusk", "night"}:
        return value
    return "unknown"


def _to_event(record: dict, trip_id: str, idx: int, predicted: bool) -> EventRecord:
    meta = record.get("metadata", {}) if isinstance(record.get("metadata", {}), dict) else {}
    confidence = float(record.get("severity", record.get("confidence", 1.0)))
    scenario = _norm_scenario(meta.get("lighting") or meta.get("scenario") or record.get("scenario"))
    stream = _norm_stream(record.get("stream"))

    return EventRecord(
        trip_id=str(trip_id),
        event_type=str(record.get("type", "unknown")),
        ts_ms_start=int(record.get("ts_ms_start", 0)),
        ts_ms_end=int(record.get("ts_ms_end", 0)),
        stream=stream,
        scenario=scenario,
        confidence=max(0.0, min(1.0, confidence if predicted else 1.0)),
        source_id=f"{trip_id}:{idx}",
    )


def _load_json(path: Path) -> dict:
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def load_ground_truth(path: Path) -> list[EventRecord]:
    data = _load_json(path)
    events: list[EventRecord] = []

    trips = data.get("trips", [])
    for trip in trips:
        trip_id = str(trip.get("trip_id", "unknown"))
        for idx, ev in enumerate(trip.get("events", []), start=1):
            events.append(_to_event(ev, trip_id=trip_id, idx=idx, predicted=False))
    return events


def load_predictions(path: Path) -> list[EventRecord]:
    events: list[EventRecord] = []

    if path.is_dir():
        report_files = sorted(path.rglob("report.json"))
        for report in report_files:
            payload = _load_json(report)
            trip_id = str(payload.get("trip_id", report.parent.name))
            for idx, ev in enumerate(payload.get("events", []), start=1):
                events.append(_to_event(ev, trip_id=trip_id, idx=idx, predicted=True))
        return events

    payload = _load_json(path)
    trips = payload.get("trips")
    if isinstance(trips, list):
        for trip in trips:
            trip_id = str(trip.get("trip_id", "unknown"))
            for idx, ev in enumerate(trip.get("events", []), start=1):
                events.append(_to_event(ev, trip_id=trip_id, idx=idx, predicted=True))
        return events

    trip_id = str(payload.get("trip_id", "unknown"))
    for idx, ev in enumerate(payload.get("events", []), start=1):
        events.append(_to_event(ev, trip_id=trip_id, idx=idx, predicted=True))
    return events


def filter_events_by_trip_ids(events: list[EventRecord], trip_ids: set[str]) -> list[EventRecord]:
    if not trip_ids:
        return []
    return [ev for ev in events if ev.trip_id in trip_ids]

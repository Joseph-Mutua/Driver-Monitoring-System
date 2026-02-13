from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class EventRecord:
    trip_id: str
    event_type: str
    ts_ms_start: int
    ts_ms_end: int
    stream: str = "unknown"
    scenario: str = "unknown"
    confidence: float = 1.0
    source_id: str = ""


@dataclass(slots=True)
class MatchResult:
    trip_id: str
    event_type: str
    stream: str
    scenario: str
    gt_id: str | None
    pred_id: str | None
    confidence: float
    iou: float
    outcome: str  # tp|fp|fn

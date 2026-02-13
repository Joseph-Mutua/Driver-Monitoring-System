from __future__ import annotations

from collections import defaultdict

from app.eval.schemas import EventRecord, MatchResult


def _duration(ev: EventRecord) -> int:
    return max(1, ev.ts_ms_end - ev.ts_ms_start)


def temporal_iou(a: EventRecord, b: EventRecord) -> float:
    left = max(a.ts_ms_start, b.ts_ms_start)
    right = min(a.ts_ms_end, b.ts_ms_end)
    inter = max(0, right - left)
    union = _duration(a) + _duration(b) - inter
    return 0.0 if union <= 0 else (inter / union)


def center_distance_ms(a: EventRecord, b: EventRecord) -> int:
    ac = (a.ts_ms_start + a.ts_ms_end) // 2
    bc = (b.ts_ms_start + b.ts_ms_end) // 2
    return abs(ac - bc)


def _compatible(a: EventRecord, b: EventRecord) -> bool:
    if a.trip_id != b.trip_id:
        return False
    if a.event_type != b.event_type:
        return False
    if a.stream != "unknown" and b.stream != "unknown" and a.stream != b.stream:
        return False
    return True


def match_events(
    gt_events: list[EventRecord],
    pred_events: list[EventRecord],
    iou_threshold: float,
    tolerance_ms: int,
) -> list[MatchResult]:
    by_key_gt: dict[tuple[str, str], list[EventRecord]] = defaultdict(list)
    by_key_pred: dict[tuple[str, str], list[EventRecord]] = defaultdict(list)

    for ev in gt_events:
        by_key_gt[(ev.trip_id, ev.event_type)].append(ev)
    for ev in pred_events:
        by_key_pred[(ev.trip_id, ev.event_type)].append(ev)

    keys = sorted(set(by_key_gt.keys()) | set(by_key_pred.keys()))
    results: list[MatchResult] = []

    for key in keys:
        gts = sorted(by_key_gt.get(key, []), key=lambda e: (e.ts_ms_start, e.ts_ms_end))
        preds = sorted(by_key_pred.get(key, []), key=lambda e: e.confidence, reverse=True)
        used_gt: set[str] = set()
        used_pred: set[str] = set()

        for pred in preds:
            best_gt = None
            best_score = -1.0
            best_iou = 0.0

            for gt in gts:
                if gt.source_id in used_gt or not _compatible(gt, pred):
                    continue
                iou = temporal_iou(gt, pred)
                close_enough = center_distance_ms(gt, pred) <= tolerance_ms
                if iou < iou_threshold and not close_enough:
                    continue
                score = iou + (0.1 if close_enough else 0.0)
                if score > best_score:
                    best_score = score
                    best_gt = gt
                    best_iou = iou

            if best_gt is None:
                continue

            used_gt.add(best_gt.source_id)
            used_pred.add(pred.source_id)
            results.append(
                MatchResult(
                    trip_id=pred.trip_id,
                    event_type=pred.event_type,
                    stream=pred.stream,
                    scenario=pred.scenario,
                    gt_id=best_gt.source_id,
                    pred_id=pred.source_id,
                    confidence=pred.confidence,
                    iou=best_iou,
                    outcome="tp",
                )
            )

        for pred in preds:
            if pred.source_id in used_pred:
                continue
            results.append(
                MatchResult(
                    trip_id=pred.trip_id,
                    event_type=pred.event_type,
                    stream=pred.stream,
                    scenario=pred.scenario,
                    gt_id=None,
                    pred_id=pred.source_id,
                    confidence=pred.confidence,
                    iou=0.0,
                    outcome="fp",
                )
            )

        for gt in gts:
            if gt.source_id in used_gt:
                continue
            results.append(
                MatchResult(
                    trip_id=gt.trip_id,
                    event_type=gt.event_type,
                    stream=gt.stream,
                    scenario=gt.scenario,
                    gt_id=gt.source_id,
                    pred_id=None,
                    confidence=0.0,
                    iou=0.0,
                    outcome="fn",
                )
            )

    return results

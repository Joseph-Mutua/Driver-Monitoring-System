from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict

import numpy as np

from app.eval.matching import match_events
from app.eval.schemas import EventRecord, MatchResult


def _safe_div(a: float, b: float) -> float:
    return 0.0 if b == 0 else a / b


def metrics_from_matches(matches: list[MatchResult]) -> dict[str, float | int]:
    tp = sum(1 for m in matches if m.outcome == "tp")
    fp = sum(1 for m in matches if m.outcome == "fp")
    fn = sum(1 for m in matches if m.outcome == "fn")

    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    f1 = _safe_div(2 * precision * recall, precision + recall)

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def sliced_metrics(matches: list[MatchResult], key_fn) -> dict[str, dict[str, float | int]]:
    grouped: dict[str, list[MatchResult]] = defaultdict(list)
    for m in matches:
        grouped[str(key_fn(m))].append(m)
    return {k: metrics_from_matches(v) for k, v in sorted(grouped.items(), key=lambda x: x[0])}


def threshold_sweep(
    gt_events: list[EventRecord],
    pred_events: list[EventRecord],
    iou_threshold: float,
    tolerance_ms: int,
) -> dict:
    thresholds = np.round(np.arange(0.10, 0.96, 0.05), 2).tolist()
    rows: list[dict] = []

    event_types = sorted({ev.event_type for ev in gt_events} | {ev.event_type for ev in pred_events})
    per_event_best: dict[str, dict] = {ev: {"threshold": 0.5, "f1": -1.0} for ev in event_types}
    global_best = {"threshold": 0.5, "f1": -1.0}

    for thr in thresholds:
        filtered = [p for p in pred_events if p.confidence >= thr]
        matches = match_events(gt_events, filtered, iou_threshold=iou_threshold, tolerance_ms=tolerance_ms)
        overall = metrics_from_matches(matches)
        if float(overall["f1"]) > global_best["f1"]:
            global_best = {"threshold": thr, "f1": float(overall["f1"])}

        row = {"threshold": thr, **overall}
        by_event = sliced_metrics(matches, lambda m: m.event_type)
        for event_type in event_types:
            f1 = float(by_event.get(event_type, {}).get("f1", 0.0))
            row[f"{event_type}_f1"] = round(f1, 4)
            if f1 > per_event_best[event_type]["f1"]:
                per_event_best[event_type] = {"threshold": thr, "f1": f1}

        rows.append(row)

    return {
        "rows": rows,
        "global_best": global_best,
        "per_event_best": per_event_best,
    }


def calibration_metrics(matches: list[MatchResult], bins: int = 10) -> dict:
    pred_rows = [m for m in matches if m.pred_id is not None]
    if not pred_rows:
        return {
            "ece": 0.0,
            "brier": 0.0,
            "bins": [],
        }

    conf = np.array([m.confidence for m in pred_rows], dtype=np.float64)
    corr = np.array([1.0 if m.outcome == "tp" else 0.0 for m in pred_rows], dtype=np.float64)

    brier = float(np.mean((corr - conf) ** 2))

    edges = np.linspace(0.0, 1.0, bins + 1)
    bucket_rows = []
    ece = 0.0

    total = len(conf)
    for i in range(bins):
        low, high = float(edges[i]), float(edges[i + 1])
        if i == bins - 1:
            idx = np.where((conf >= low) & (conf <= high))[0]
        else:
            idx = np.where((conf >= low) & (conf < high))[0]
        if idx.size == 0:
            bucket_rows.append({"bin": i, "low": low, "high": high, "count": 0, "avg_conf": 0.0, "accuracy": 0.0})
            continue

        avg_conf = float(np.mean(conf[idx]))
        acc = float(np.mean(corr[idx]))
        weight = idx.size / total
        ece += abs(acc - avg_conf) * weight
        bucket_rows.append(
            {
                "bin": i,
                "low": low,
                "high": high,
                "count": int(idx.size),
                "avg_conf": round(avg_conf, 4),
                "accuracy": round(acc, 4),
            }
        )

    return {
        "ece": round(float(ece), 5),
        "brier": round(brier, 5),
        "bins": bucket_rows,
    }


def evaluate(
    gt_events: list[EventRecord],
    pred_events: list[EventRecord],
    iou_threshold: float,
    tolerance_ms: int,
    bins: int,
) -> dict:
    matches = match_events(gt_events, pred_events, iou_threshold=iou_threshold, tolerance_ms=tolerance_ms)

    output = {
        "config": {
            "iou_threshold": iou_threshold,
            "tolerance_ms": tolerance_ms,
            "bins": bins,
        },
        "dataset": {
            "ground_truth_events": len(gt_events),
            "predicted_events": len(pred_events),
            "trips_ground_truth": len({g.trip_id for g in gt_events}),
            "trips_predicted": len({p.trip_id for p in pred_events}),
        },
        "overall": metrics_from_matches(matches),
        "by_event": sliced_metrics(matches, lambda m: m.event_type),
        "by_stream": sliced_metrics(matches, lambda m: m.stream),
        "by_scenario": sliced_metrics(matches, lambda m: m.scenario),
        "calibration": calibration_metrics(matches, bins=bins),
        "threshold_sweep": threshold_sweep(
            gt_events=gt_events,
            pred_events=pred_events,
            iou_threshold=iou_threshold,
            tolerance_ms=tolerance_ms,
        ),
        "failure_examples": {
            "false_positives": [asdict(m) for m in matches if m.outcome == "fp"][:200],
            "false_negatives": [asdict(m) for m in matches if m.outcome == "fn"][:200],
        },
        "matches": [asdict(m) for m in matches],
    }
    return output

from __future__ import annotations

import csv
import json
from datetime import datetime, time
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.eval.io import filter_events_by_trip_ids, load_ground_truth, load_predictions
from app.eval.metrics import evaluate
from app.eval.plots import save_reliability_diagram, save_threshold_curve
from app.models import Trip
from app.schemas.eval import EvalReportFileLinks, EvalReportEntry, EvalRunResponse


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def _eval_root() -> Path:
    root = Path(settings.report_dir) / "evaluations"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _links_for(report_id: str) -> EvalReportFileLinks:
    base = f"/reports/evaluations/{report_id}"
    return EvalReportFileLinks(
        summary_json=f"{base}/summary.json",
        evaluation_json=f"{base}/evaluation.json",
        metrics_by_event_csv=f"{base}/metrics_by_event.csv",
        metrics_by_stream_csv=f"{base}/metrics_by_stream.csv",
        metrics_by_scenario_csv=f"{base}/metrics_by_scenario.csv",
        threshold_sweep_csv=f"{base}/threshold_sweep.csv",
        reliability_diagram_png=f"{base}/reliability_diagram.png",
        threshold_curve_png=f"{base}/threshold_curve.png",
    )


def _run_eval(
    gt_events,
    pred_events,
    iou_threshold: float,
    tolerance_ms: int,
    bins: int,
    report_id: str,
    selected_trip_ids: list[str],
) -> EvalRunResponse:
    out_dir = _eval_root() / report_id
    out_dir.mkdir(parents=True, exist_ok=True)

    results = evaluate(
        gt_events=gt_events,
        pred_events=pred_events,
        iou_threshold=iou_threshold,
        tolerance_ms=tolerance_ms,
        bins=bins,
    )

    (out_dir / "evaluation.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

    by_event = [{"event_type": k, **v} for k, v in results["by_event"].items()]
    by_stream = [{"stream": k, **v} for k, v in results["by_stream"].items()]
    by_scenario = [{"scenario": k, **v} for k, v in results["by_scenario"].items()]

    _write_csv(out_dir / "metrics_by_event.csv", by_event)
    _write_csv(out_dir / "metrics_by_stream.csv", by_stream)
    _write_csv(out_dir / "metrics_by_scenario.csv", by_scenario)
    _write_csv(out_dir / "threshold_sweep.csv", results["threshold_sweep"]["rows"])

    save_reliability_diagram(results["calibration"], out_dir / "reliability_diagram.png")
    save_threshold_curve(results["threshold_sweep"]["rows"], out_dir / "threshold_curve.png")

    summary = {
        "overall": results["overall"],
        "global_best_threshold": results["threshold_sweep"]["global_best"],
        "calibration": {
            "ece": results["calibration"].get("ece", 0.0),
            "brier": results["calibration"].get("brier", 0.0),
        },
        "selected_trip_count": len(selected_trip_ids),
        "output_dir": str(out_dir.resolve()),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    return EvalRunResponse(
        report_id=report_id,
        output_dir=str(out_dir.resolve()),
        links=_links_for(report_id),
        summary=summary,
        selected_trip_ids=selected_trip_ids,
    )


def run_eval_from_paths(
    ground_truth_path: str,
    predictions_path: str,
    iou_threshold: float,
    tolerance_ms: int,
    bins: int,
) -> EvalRunResponse:
    report_id = f"eval_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    gt_events = load_ground_truth(Path(ground_truth_path))
    pred_events = load_predictions(Path(predictions_path))
    all_trip_ids = sorted({ev.trip_id for ev in gt_events} | {ev.trip_id for ev in pred_events})
    return _run_eval(gt_events, pred_events, iou_threshold, tolerance_ms, bins, report_id, all_trip_ids)


def run_eval_for_date_range(
    db: Session,
    ground_truth_path: str,
    date_from: str | None,
    date_to: str | None,
    iou_threshold: float,
    tolerance_ms: int,
    bins: int,
) -> EvalRunResponse:
    query = select(Trip).where(Trip.status == "done", Trip.report_json_url.is_not(None))

    if date_from:
        start_dt = datetime.combine(datetime.strptime(date_from, "%Y-%m-%d").date(), time.min)
        query = query.where(Trip.created_at >= start_dt)
    if date_to:
        end_dt = datetime.combine(datetime.strptime(date_to, "%Y-%m-%d").date(), time.max)
        query = query.where(Trip.created_at <= end_dt)

    trips = db.execute(query).scalars().all()
    trip_ids = sorted({trip.id for trip in trips})

    gt_events = filter_events_by_trip_ids(load_ground_truth(Path(ground_truth_path)), set(trip_ids))
    pred_events = filter_events_by_trip_ids(load_predictions(Path(settings.report_dir)), set(trip_ids))

    report_id = f"eval_range_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    return _run_eval(gt_events, pred_events, iou_threshold, tolerance_ms, bins, report_id, trip_ids)


def list_eval_reports(limit: int = 50) -> list[EvalReportEntry]:
    root = _eval_root()
    entries: list[EvalReportEntry] = []

    for directory in sorted([p for p in root.iterdir() if p.is_dir()], reverse=True):
        summary = directory / "summary.json"
        if not summary.exists():
            continue
        created_at = datetime.utcfromtimestamp(summary.stat().st_mtime).isoformat()
        entries.append(
            EvalReportEntry(
                report_id=directory.name,
                created_at=created_at,
                summary_url=f"/reports/evaluations/{directory.name}/summary.json",
            )
        )
        if len(entries) >= limit:
            break
    return entries

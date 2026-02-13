from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

from app.eval.io import load_ground_truth, load_predictions
from app.eval.metrics import evaluate
from app.eval.plots import save_reliability_diagram, save_threshold_curve


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate DMS/ADAS event detection quality")
    parser.add_argument("--ground-truth", required=True, help="Path to ground truth JSON")
    parser.add_argument("--predictions", required=True, help="Path to predictions JSON or reports directory")
    parser.add_argument("--outdir", default="eval_reports", help="Directory where outputs are written")
    parser.add_argument("--iou-threshold", type=float, default=0.30)
    parser.add_argument("--tolerance-ms", type=int, default=1200)
    parser.add_argument("--bins", type=int, default=10)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    gt_path = Path(args.ground_truth)
    pred_path = Path(args.predictions)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.outdir) / f"eval_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    gt_events = load_ground_truth(gt_path)
    pred_events = load_predictions(pred_path)

    results = evaluate(
        gt_events=gt_events,
        pred_events=pred_events,
        iou_threshold=args.iou_threshold,
        tolerance_ms=args.tolerance_ms,
        bins=args.bins,
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
        "output_dir": str(out_dir.resolve()),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

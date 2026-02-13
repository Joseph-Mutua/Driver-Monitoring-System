from __future__ import annotations

import argparse
import json

from app.db import SessionLocal
from app.services.evaluation_service import run_eval_for_date_range


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run fleet evaluation over a date range using completed trips in DB")
    parser.add_argument("--ground-truth", required=True, help="Path to ground truth JSON")
    parser.add_argument("--date-from", default=None, help="YYYY-MM-DD")
    parser.add_argument("--date-to", default=None, help="YYYY-MM-DD")
    parser.add_argument("--iou-threshold", type=float, default=0.30)
    parser.add_argument("--tolerance-ms", type=int, default=1200)
    parser.add_argument("--bins", type=int, default=10)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    db = SessionLocal()
    try:
        out = run_eval_for_date_range(
            db=db,
            ground_truth_path=args.ground_truth,
            date_from=args.date_from,
            date_to=args.date_to,
            iou_threshold=args.iou_threshold,
            tolerance_ms=args.tolerance_ms,
            bins=args.bins,
        )
        print(out.model_dump_json(indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()

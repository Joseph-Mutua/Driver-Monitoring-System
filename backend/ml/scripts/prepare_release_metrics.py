from __future__ import annotations

import argparse
import json
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create release_metrics.json from eval + calibration outputs")
    parser.add_argument("--evaluation-json", required=True)
    parser.add_argument("--calibration-json", default=None)
    parser.add_argument("--output", default="ml/artifacts/release_metrics.json")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    eval_payload = json.loads(Path(args.evaluation_json).read_text(encoding="utf-8"))

    metrics = {
        "overall": eval_payload.get("overall", {}),
        "by_event": eval_payload.get("by_event", {}),
        "by_stream": eval_payload.get("by_stream", {}),
        "by_scenario": eval_payload.get("by_scenario", {}),
        "calibration": eval_payload.get("calibration", {}),
    }

    if args.calibration_json:
        calib = json.loads(Path(args.calibration_json).read_text(encoding="utf-8"))
        metrics["calibration_artifact"] = calib

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()

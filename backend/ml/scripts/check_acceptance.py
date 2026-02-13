from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import load_yaml


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check release metrics against acceptance gates")
    parser.add_argument("--metrics-json", required=True)
    parser.add_argument("--gates-yaml", default="ml/configs/acceptance_gates.yaml")
    return parser.parse_args()


def _get_nested(payload: dict, *keys, default=None):
    cur = payload
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def main() -> None:
    args = _parse_args()
    metrics = json.loads(Path(args.metrics_json).read_text(encoding="utf-8"))
    gates = load_yaml(Path(args.gates_yaml))

    failures: list[str] = []

    overall_req = gates.get("minimum_metrics", {}).get("overall", {})
    for key, threshold in overall_req.items():
        val = float(_get_nested(metrics, "overall", key, default=0.0))
        if val < float(threshold):
            failures.append(f"overall.{key}={val:.4f} < {threshold}")

    per_event_req = gates.get("minimum_metrics", {}).get("per_event", {})
    for event_name, req in per_event_req.items():
        for metric_name, threshold in req.items():
            val = float(_get_nested(metrics, "by_event", event_name, metric_name, default=0.0))
            if val < float(threshold):
                failures.append(f"by_event.{event_name}.{metric_name}={val:.4f} < {threshold}")

    per_scenario_req = gates.get("minimum_metrics", {}).get("per_scenario", {})
    for scenario, req in per_scenario_req.items():
        for metric_name, threshold in req.items():
            val = float(_get_nested(metrics, "by_scenario", scenario, metric_name, default=0.0))
            if val < float(threshold):
                failures.append(f"by_scenario.{scenario}.{metric_name}={val:.4f} < {threshold}")

    cal_req = gates.get("minimum_metrics", {}).get("calibration", {})
    max_ece = cal_req.get("max_ece")
    if max_ece is not None:
        ece = float(_get_nested(metrics, "calibration", "ece", default=1.0))
        if ece > float(max_ece):
            failures.append(f"calibration.ece={ece:.5f} > {max_ece}")

    max_brier = cal_req.get("max_brier")
    if max_brier is not None:
        brier = float(_get_nested(metrics, "calibration", "brier", default=1.0))
        if brier > float(max_brier):
            failures.append(f"calibration.brier={brier:.5f} > {max_brier}")

    status = "passed" if not failures else "failed"
    print(json.dumps({"status": status, "failures": failures}, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

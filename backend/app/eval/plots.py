from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt


def save_reliability_diagram(calibration: dict, out_path: Path) -> None:
    bins = calibration.get("bins", [])
    if not bins:
        return

    xs = [float(b.get("avg_conf", 0.0)) for b in bins]
    ys = [float(b.get("accuracy", 0.0)) for b in bins]
    counts = [int(b.get("count", 0)) for b in bins]

    plt.figure(figsize=(7, 6))
    plt.plot([0, 1], [0, 1], linestyle="--", color="#334155", label="Perfect calibration")
    plt.scatter(xs, ys, s=[max(20, c * 3) for c in counts], c="#0ea5e9", alpha=0.8, label="Bins")
    plt.plot(xs, ys, color="#0284c7", linewidth=1)
    plt.title("Reliability Diagram")
    plt.xlabel("Mean predicted confidence")
    plt.ylabel("Empirical accuracy")
    plt.xlim(0, 1)
    plt.ylim(0, 1)
    plt.grid(alpha=0.2)
    plt.legend(loc="lower right")
    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=150)
    plt.close()


def save_threshold_curve(threshold_rows: list[dict], out_path: Path) -> None:
    if not threshold_rows:
        return

    xs = [float(r["threshold"]) for r in threshold_rows]
    ys = [float(r.get("f1", 0.0)) for r in threshold_rows]

    plt.figure(figsize=(7, 4.5))
    plt.plot(xs, ys, color="#14b8a6", linewidth=2)
    plt.scatter(xs, ys, color="#0f766e", s=22)
    plt.title("F1 vs Confidence Threshold")
    plt.xlabel("Threshold")
    plt.ylabel("F1")
    plt.xlim(min(xs), max(xs))
    plt.ylim(0, 1)
    plt.grid(alpha=0.25)
    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=150)
    plt.close()

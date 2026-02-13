from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fit confidence calibration models")
    parser.add_argument("--predictions-csv", required=True)
    parser.add_argument("--output", default="ml/artifacts/calibration.json")
    parser.add_argument("--method", choices=["isotonic", "platt"], default="isotonic")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    df = pd.read_csv(args.predictions_csv)
    conf = df["confidence"].astype(float).to_numpy()
    y = df["matched"].astype(int).to_numpy()

    payload: dict = {"method": args.method}

    if args.method == "isotonic":
        model = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
        model.fit(conf, y)
        grid = np.linspace(0.0, 1.0, 101)
        mapped = model.predict(grid)
        payload["lookup"] = [{"raw": round(float(x), 4), "calibrated": round(float(c), 4)} for x, c in zip(grid, mapped)]
    else:
        clf = LogisticRegression(max_iter=500)
        clf.fit(conf.reshape(-1, 1), y)
        payload["coef"] = float(clf.coef_[0][0])
        payload["intercept"] = float(clf.intercept_[0])

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Calibration artifact written to {out}")


if __name__ == "__main__":
    main()

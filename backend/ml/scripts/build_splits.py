from __future__ import annotations

import argparse
import random
from collections import defaultdict
from pathlib import Path

import yaml

from common import ensure_dir, read_jsonl


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build deterministic train/val/test splits without driver leakage")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--outdir", default="ml/artifacts/splits")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train-ratio", type=float, default=0.7)
    parser.add_argument("--val-ratio", type=float, default=0.15)
    parser.add_argument("--test-ratio", type=float, default=0.15)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    rows = read_jsonl(Path(args.manifest))

    by_driver: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_driver[str(row.get("driver_id", "unknown"))].append(row)

    drivers = sorted(by_driver.keys())
    random.Random(args.seed).shuffle(drivers)

    n = len(drivers)
    n_train = int(n * args.train_ratio)
    n_val = int(n * args.val_ratio)

    train_drivers = set(drivers[:n_train])
    val_drivers = set(drivers[n_train:n_train + n_val])
    test_drivers = set(drivers[n_train + n_val:])

    split_to_paths = {"train": [], "val": [], "test": []}
    root = Path(args.manifest).parent

    for row in rows:
        driver = str(row.get("driver_id", "unknown"))
        if driver in train_drivers:
            split = "train"
        elif driver in val_drivers:
            split = "val"
        else:
            split = "test"

        image_path = str((root / row["image_path"]).resolve())
        split_to_paths[split].append(image_path)

    outdir = Path(args.outdir)
    ensure_dir(outdir)

    for split, paths in split_to_paths.items():
        (outdir / f"{split}.txt").write_text("\n".join(paths), encoding="utf-8")

    data_yaml = {
        "path": str(outdir.resolve()),
        "train": str((outdir / "train.txt").resolve()),
        "val": str((outdir / "val.txt").resolve()),
        "test": str((outdir / "test.txt").resolve()),
        "names": {
            0: "seatbelt_off",
            1: "phone_in_hand",
            2: "vehicle",
            3: "pedestrian",
            4: "motorcycle",
        },
    }
    (outdir / "data.yaml").write_text(yaml.safe_dump(data_yaml, sort_keys=False), encoding="utf-8")
    print(f"Split files written to {outdir}")


if __name__ == "__main__":
    main()

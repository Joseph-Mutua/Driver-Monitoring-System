from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path

from common import load_yaml, read_jsonl, write_json


CRITICAL_KEYS = ["sample_id", "image_path", "split", "driver_id", "vehicle_id", "stream", "scenario", "road_type", "country"]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate dataset manifest quality and leakage")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--schema", default="ml/configs/dataset.schema.yaml")
    parser.add_argument("--output", default="ml/reports/dataset_validation.json")
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    manifest_path = Path(args.manifest)
    schema = load_yaml(Path(args.schema))
    rows = read_jsonl(manifest_path)

    errors: list[str] = []
    warnings: list[str] = []

    required_fields = set(schema.get("required_fields", []))
    allowed = schema.get("allowed_values", {})

    seen_ids = set()
    split_driver: dict[str, set[str]] = defaultdict(set)
    split_vehicle: dict[str, set[str]] = defaultdict(set)
    class_counter: Counter[int] = Counter()
    split_counter: Counter[str] = Counter()
    scenario_counter: Counter[str] = Counter()

    root = manifest_path.parent

    for i, row in enumerate(rows, start=1):
        for key in required_fields:
            if key not in row or row[key] in {None, ""}:
                errors.append(f"row {i}: missing required field '{key}'")

        for key, allowed_values in allowed.items():
            if key in row and row[key] not in allowed_values:
                errors.append(f"row {i}: invalid value '{row[key]}' for {key}")

        sid = str(row.get("sample_id", ""))
        if sid in seen_ids:
            errors.append(f"row {i}: duplicate sample_id {sid}")
        seen_ids.add(sid)

        split = str(row.get("split", "unknown"))
        split_counter[split] += 1
        scenario_counter[str(row.get("scenario", "unknown"))] += 1
        split_driver[split].add(str(row.get("driver_id", "")))
        split_vehicle[split].add(str(row.get("vehicle_id", "")))

        image_path = root / str(row.get("image_path", ""))
        if not image_path.exists():
            errors.append(f"row {i}: missing image file {image_path}")

        label_rel = row.get("label_path")
        if label_rel:
            label_path = root / str(label_rel)
            if not label_path.exists():
                errors.append(f"row {i}: missing label file {label_path}")
            else:
                for line in label_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split()
                    try:
                        cls = int(parts[0])
                        class_counter[cls] += 1
                    except Exception:
                        warnings.append(f"row {i}: malformed label line '{line}'")

    for a in ["train", "val", "test"]:
        for b in ["train", "val", "test"]:
            if a >= b:
                continue
            overlap = split_driver[a] & split_driver[b]
            if overlap:
                errors.append(f"driver leakage between {a} and {b}: {len(overlap)} overlapping ids")
            veh_overlap = split_vehicle[a] & split_vehicle[b]
            if veh_overlap:
                warnings.append(f"vehicle overlap between {a} and {b}: {len(veh_overlap)} ids")

    total = max(1, len(rows))
    val_night_ratio = scenario_counter["night"] / total
    if val_night_ratio < 0.10:
        warnings.append(f"night coverage is low ({val_night_ratio:.3f})")

    result = {
        "total_samples": len(rows),
        "split_counts": dict(split_counter),
        "scenario_counts": dict(scenario_counter),
        "class_counts": {str(k): v for k, v in sorted(class_counter.items())},
        "errors": errors,
        "warnings": warnings,
        "status": "failed" if errors else "passed",
    }

    write_json(Path(args.output), result)
    print(f"Validation status: {result['status']} | errors={len(errors)} warnings={len(warnings)}")

    if args.strict and errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

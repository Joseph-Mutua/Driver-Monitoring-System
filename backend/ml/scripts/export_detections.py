from __future__ import annotations

import argparse
import csv
from pathlib import Path

import cv2
from ultralytics import YOLO

from common import read_jsonl


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export detections for calibration fitting")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", default="ml/artifacts/predictions_val.csv")
    parser.add_argument("--conf", type=float, default=0.05)
    return parser.parse_args()


def _best_iou(pred_box, gt_box) -> float:
    px1, py1, px2, py2 = pred_box
    gx1, gy1, gx2, gy2 = gt_box
    ix1, iy1 = max(px1, gx1), max(py1, gy1)
    ix2, iy2 = min(px2, gx2), min(py2, gy2)
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    p_area = max(1.0, (px2 - px1) * (py2 - py1))
    g_area = max(1.0, (gx2 - gx1) * (gy2 - gy1))
    union = p_area + g_area - inter
    return inter / union if union > 0 else 0.0


def _load_gt_boxes(label_path: Path, w: int, h: int):
    out = []
    if not label_path.exists():
        return out
    for line in label_path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) != 5:
            continue
        cls, cx, cy, bw, bh = map(float, parts)
        x1 = (cx - bw / 2) * w
        y1 = (cy - bh / 2) * h
        x2 = (cx + bw / 2) * w
        y2 = (cy + bh / 2) * h
        out.append((int(cls), (x1, y1, x2, y2)))
    return out


def main() -> None:
    args = _parse_args()
    manifest = read_jsonl(Path(args.manifest))
    model = YOLO(args.model)

    rows = []
    root = Path(args.manifest).parent

    for sample in manifest:
        if sample.get("split") != "val":
            continue
        image_path = root / sample["image_path"]
        label_path = root / sample.get("label_path", "")

        frame = cv2.imread(str(image_path))
        if frame is None:
            continue
        h, w = frame.shape[:2]
        gt_boxes = _load_gt_boxes(label_path, w, h)

        preds = model.predict(frame, verbose=False, conf=args.conf)
        for pred in preds:
            if pred.boxes is None:
                continue
            for box in pred.boxes:
                cls = int(box.cls.item())
                conf = float(box.conf.item())
                x1, y1, x2, y2 = map(float, box.xyxy[0].tolist())

                best = 0.0
                matched = 0
                for gt_cls, gt_box in gt_boxes:
                    if gt_cls != cls:
                        continue
                    iou = _best_iou((x1, y1, x2, y2), gt_box)
                    if iou > best:
                        best = iou
                if best >= 0.5:
                    matched = 1

                rows.append(
                    {
                        "sample_id": sample.get("sample_id", ""),
                        "class_id": cls,
                        "confidence": conf,
                        "matched": matched,
                        "scenario": sample.get("scenario", "unknown"),
                        "stream": sample.get("stream", "unknown"),
                    }
                )

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["sample_id", "class_id", "confidence", "matched", "scenario", "stream"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Exported {len(rows)} predictions to {out_path}")


if __name__ == "__main__":
    main()

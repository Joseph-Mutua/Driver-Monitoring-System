from __future__ import annotations

import argparse
from pathlib import Path

import yaml
from ultralytics import YOLO


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a YOLO detector from config")
    parser.add_argument("--config", default="ml/configs/train.detector.yaml")
    parser.add_argument("--override-data", default=None)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))

    model = YOLO(cfg["model"])
    data_yaml = args.override_data or cfg["data_yaml"]

    model.train(
        data=data_yaml,
        task=cfg.get("task", "detect"),
        imgsz=cfg.get("imgsz", 960),
        epochs=cfg.get("epochs", 80),
        batch=cfg.get("batch", 16),
        device=cfg.get("device", "auto"),
        patience=cfg.get("patience", 20),
        optimizer=cfg.get("optimizer", "AdamW"),
        lr0=cfg.get("lr0", 0.001),
        lrf=cfg.get("lrf", 0.01),
        weight_decay=cfg.get("weight_decay", 5e-4),
        warmup_epochs=cfg.get("warmup_epochs", 3),
        conf=cfg.get("conf", 0.001),
        iou=cfg.get("iou", 0.6),
        save_period=cfg.get("save_period", 5),
        project=cfg.get("project", "ml/artifacts"),
        name=cfg.get("name", "detector_run"),
    )


if __name__ == "__main__":
    main()

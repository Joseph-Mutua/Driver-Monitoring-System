# Model Training Pipeline (Production Scaffold)

This module provides a production-oriented training and validation scaffold for upgrading DMS/ADAS models to Kenya-specific commercial performance.

## What this includes
- Dataset manifest schema and sample records
- Dataset QA and leakage checks
- Split generation by driver/vehicle (to avoid leakage)
- YOLO detector training wrapper (phone/seatbelt/road objects)
- Detection export + confidence calibration (isotonic / platt)
- Acceptance-gate policy checks for release decisions

## Directory layout
- `ml/data/manifest.sample.jsonl`: sample metadata format
- `ml/configs/dataset.schema.yaml`: required fields and allowed values
- `ml/configs/train.detector.yaml`: training config template
- `ml/configs/acceptance_gates.yaml`: production acceptance criteria
- `ml/scripts/validate_dataset.py`: QA and leakage checks
- `ml/scripts/build_splits.py`: deterministic split builder
- `ml/scripts/train_detector.py`: Ultralytics YOLO training wrapper
- `ml/scripts/export_detections.py`: export prediction CSV for calibration
- `ml/scripts/calibrate_confidence.py`: fit calibrator + emit lookup
- `ml/scripts/check_acceptance.py`: pass/fail release gate evaluation
- `ml/scripts/run_pipeline.ps1`: orchestrated local workflow

## Quick start

### 1) Install training deps
```powershell
cd backend
.\.venv\Scripts\python -m pip install -r ml\requirements-train.txt
```

### 2) Prepare data
- Build `ml/data/manifest.jsonl` from labeled images.
- YOLO labels should exist for records with `label_path`.

### 3) Run full QA + split + train + gate checks
```powershell
cd backend
.\ml\scripts\run_pipeline.ps1 -Manifest ml\data\manifest.jsonl -OutputRoot ml\artifacts\run1
```

### 4) Evaluate against acceptance gates
```powershell
cd backend
.\.venv\Scripts\python ml\scripts\check_acceptance.py \
  --metrics-json ml\artifacts\run1\release_metrics.json \
  --gates-yaml ml\configs\acceptance_gates.yaml
```

## Recommended release flow
1. `validate_dataset.py` must pass (no critical leakage/coverage failures).
2. Train model(s) and export metrics stratified by:
   - stream (`front/rear/cabin`)
   - scenario (`day/dusk/night`)
   - road type (`highway/urban/rural`)
3. Calibrate confidence and publish calibration artifact with model.
4. Check acceptance gates before promoting to production.

## Notes
- This scaffold is intentionally model-agnostic at the orchestration level.
- You can plug in custom detector architectures while keeping the same governance checks.
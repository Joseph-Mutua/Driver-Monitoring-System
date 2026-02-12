# DMS System Design and Available Solutions

## 1) Recommended architecture for your dashcam setup
- Ingestion: upload one day folder (30-50 clips) containing front and rear MP4 files.
- Parsing: infer camera type from filename (`_rear` suffix).
- Processing: sample frames and run multi-task detectors in one pass.
- Aggregation: temporal smoothing, event de-duplication, severity scoring.
- Reporting: per-event timeline, per-clip summary, per-day KPI and risk score.

## 2) Model stack used in this implementation
- Face and head behavior: MediaPipe Face Mesh (fatigue + distraction)
- Road scene object detection: YOLOv8n (phone, vehicle-based obstruction/tailgating)
- Lane deviation: classical CV (Canny + Hough)
- Seatbelt: heuristic diagonal-line detector (flagged as non-certified)

## 3) State of currently available systems

### A) Commercial ADAS/DMS SDK vendors
- Pros: high accuracy, tested edge deployment, strong support.
- Cons: licensing cost, closed models, limited customizability.
- Fit: best when you need rapid production rollout and compliance evidence.

### B) Open-source stack (YOLO + MediaPipe + tracking)
- Pros: low cost, full control, flexible retraining.
- Cons: requires significant dataset curation and validation.
- Fit: best when you can iterate with your own fleet data.

### C) Hybrid architecture (recommended)
- Start with open-source baseline.
- Replace weakest detectors (seatbelt, phone-in-hand edge cases, nighttime fatigue) with custom trained models.
- Keep backend/API/reporting architecture stable while swapping detector modules.

## 4) Practical performance targets
- Offline day-folder analysis: 30-50 clips in <20 minutes on a mid-range GPU.
- Event precision target (phase-1): >85% for phone/tailgating/obstruction, >80% for fatigue/distraction.
- Event recall target (phase-1): >80% on balanced day/night/rain subsets.

## 5) Data strategy you should implement next
- Build labeled dataset from your own dashcam footage:
  - fatigue states (eyes closed/yawn)
  - distraction/head pose
  - seatbelt worn/not worn
  - phone in hand vs near dashboard false positives
  - lane and near-collision/tailgating examples
- Split by driver, vehicle, lighting, weather to avoid leakage.
- Track per-condition metrics (day/night/rain/highway/city).

## 6) Production improvements roadmap
- Replace seatbelt heuristic with dedicated detection model (YOLO/RT-DETR fine-tuned).
- Add multi-object tracking (ByteTrack/OC-SORT) for stable obstruction and tailgating trajectories.
- Add monocular depth or calibrated distance estimation.
- Quantize/export to ONNX/TensorRT for 2x-5x speedup.
- Move jobs to distributed workers (Celery + Redis), store reports in DB/object storage.
- Add auth, audit logs, and retention controls.

## 7) Safety note
This implementation is suitable as a strong engineering baseline and for internal evaluation. It is not safety-certified for regulatory or legal enforcement use without dedicated validation, calibration, and compliance testing.

# Driver Monitoring + ADAS Platform

This implementation now follows the trip-based architecture you specified.

## Implemented functionality
- Upload trip files (front required, rear recommended, cabin optional for strong DMS)
- Trip ingestion and assembly for segmented dashcam clips
- Front/rear/cabin stream ordering and best-effort timestamp sync
- Day/night/dusk scene profiling with adaptive detection thresholds
- DMS detections:
  - driver fatigue (PERCLOS + microsleep)
  - distracted driving
  - mobile phone use
  - seatbelt not worn (heuristic baseline)
- ADAS detections:
  - lane deviation
  - obstruction ahead
  - tailgating
  - rear obstruction behind
  - rear tailgating behind
- Event engine with debounce, min-duration, cooldown, and severity smoothing
- Scene reliability gating to suppress low-confidence events in poor visibility
- Event artifacts:
  - snapshot image
  - annotated short MP4 clip around event
- Scoring:
  - fatigue/distraction/lane/following-distance
  - overall score
- Reports:
  - JSON report
  - downloadable PDF report
- Dashboard:
  - upload + process status
  - event timeline with artifact links
  - scores
  - trip history (driver/vehicle fields supported)

## Backend stack
- FastAPI
- SQLite (via SQLAlchemy)
- OpenCV + MediaPipe + YOLOv8n
- FPDF2 (PDF report)

## Frontend stack
- Vite + React + TypeScript + Tailwind CSS

## Data schema
Implemented tables:
- `trips`
- `events`
- `scores`

## API endpoints
- `POST /api/trips`
- `POST /api/trips/{id}/complete-upload`
- `GET /api/trips`
- `GET /api/trips/{id}`
- `GET /api/trips/{id}/events`
- `GET /api/trips/{id}/scores`
- `POST /api/evaluation/run` (ground truth + predictions path)
- `POST /api/evaluation/run-range` (ground truth + DB date range selection)
- `GET /api/evaluation/reports` (recent evaluation report list)
- `POST /api/ml/pipeline/run` (start training pipeline job)
- `GET /api/ml/pipeline/jobs` (list training jobs)
- `GET /api/ml/pipeline/jobs/{id}` (job status)
- `GET /api/ml/pipeline/jobs/{id}/log` (tail logs)

Backward compatibility:
- `POST /api/analyze/day`
- `GET /api/jobs/{job_id}`
- `GET /api/reports/{job_id}`

## Run

### Backend
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend
```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Important production notes
- Seatbelt detection is currently heuristic and should be replaced with a dedicated trained model.
- If no cabin stream is provided, DMS events are approximated and should not be used for legal enforcement.
- Sync is timestamp-based MVP logic; add audio cross-correlation and GPS speed fusion for harder drift scenarios.
- For scale, replace background task execution with worker queue (Redis + RQ/Celery).

## Training and release pipeline scaffold
The repository now includes a full model-improvement scaffold under `backend/ml`:
- dataset manifest schema and sample
- dataset QA + leakage checks
- deterministic split builder
- YOLO training wrapper
- detection export + confidence calibration
- release metrics assembly + acceptance gate checks

See `backend/ml/README.md` for usage.

## UI visibility
- Dashboard now exposes:
  - rear stream upload controls
  - model insights (scene distribution, streams used, limitations, road profile)
  - a fixed bottom-left `Model Training` button that opens a dedicated training page
  - training page actions: run, cancel, retry, view logs, and download artifacts directly
## Evaluation Suite

A full offline evaluation suite is now included in `backend/app/eval`.

### Inputs
- Ground truth JSON: labeled trips/events (`backend/eval_ground_truth.sample.json` as template)
- Predictions source:
  - a JSON file with predicted events, or
  - a directory containing generated `report.json` files (for example `backend/reports`)

### Run

From `backend/`:

```powershell
.\.venv\Scripts\python -m app.eval.run --ground-truth .\eval_ground_truth.sample.json --predictions .\reports
```

Or use helper script:

```powershell
.\run_eval.ps1 -GroundTruth .\eval_ground_truth.sample.json -Predictions .\reports
```

### Outputs
Each run creates `backend/eval_reports/eval_YYYYMMDD_HHMMSS/` with:
- `evaluation.json` full result object
- `summary.json` compact summary
- `metrics_by_event.csv`
- `metrics_by_stream.csv`
- `metrics_by_scenario.csv`
- `threshold_sweep.csv`
- `reliability_diagram.png`
- `threshold_curve.png`

### Metrics included
- Overall: TP/FP/FN, precision, recall, F1
- Slices: per event type, stream (`front/rear/cabin`), scenario (`day/dusk/night`)
- Confidence calibration: ECE, Brier score, reliability bins
- Threshold optimization: global best threshold and per-event best thresholds
- Failure analysis: top FP and FN examples for error review
# Driver Monitoring + ADAS Platform

This implementation now follows the trip-based architecture you specified.

## Implemented functionality
- Upload trip files (front required, cabin optional)
- Trip ingestion and assembly for segmented dashcam clips
- Front/cabin stream ordering and best-effort timestamp sync
- DMS detections:
  - driver fatigue (PERCLOS + microsleep)
  - distracted driving
  - mobile phone use
  - seatbelt not worn (heuristic baseline)
- ADAS detections:
  - lane deviation
  - obstruction ahead
  - tailgating
- Event engine with debounce, min-duration, cooldown, and severity smoothing
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
- Sync is timestamp-based MVP logic; add audio cross-correlation for harder drift scenarios.
- For scale, replace background task execution with worker queue (Redis + RQ/Celery).

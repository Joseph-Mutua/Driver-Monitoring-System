# DMS: Run and Test Guide

This guide explains how to run and test the **Driver Monitoring + ADAS Platform** (DMS) locally.

---

## 1. Project overview

| Layer   | Stack                          | Purpose |
|---------|---------------------------------|--------|
| **Backend** | FastAPI, SQLite, OpenCV, MediaPipe, YOLOv8, FPDF2 | Trip upload, video analysis, DMS/ADAS detection, events, scores, PDF reports |
| **Frontend** | Vite, React, TypeScript, Tailwind | Upload UI, job progress, event timeline, KPI scores, trip history |

- **Backend** runs at `http://localhost:8000`.
- **Frontend** runs at `http://localhost:5173` and proxies `/api` and `/health` to the backend.

---

## 2. Prerequisites

- **Python 3.10+** (for backend)
- **Node.js 18+** and **npm** (for frontend)
- **PowerShell** (or use equivalent bash commands where applicable)

**Windows – Python not found?** If `python` opens the Microsoft Store or says "not recognized":
- Install Python from [python.org](https://www.python.org/downloads/) (3.10 or 3.11 recommended). During setup, check **"Add Python to PATH"**.
- Or use the **Python launcher**: try `py -3 -m venv .venv` (see §3.1). The `py` command is installed with Python on Windows and picks the right version.

---

## 3. Backend: setup and run

### 3.1 Create and activate virtual environment

On **Windows**, use the Python launcher if `python` is not available:

```powershell
cd d:\WORK\DMS\backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If `python` is on your PATH (e.g. after installing from python.org with "Add to PATH"):

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If you get an execution policy error:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**`pip` not recognized?** Activate the venv first (see above), then run `pip install ...`. Or run pip via the venv without activating:

```powershell
.\.venv\Scripts\pip.exe install -r requirements.txt
```

### 3.2 Install dependencies

With the venv **activated** (you should see `(.venv)` in the prompt):

```powershell
pip install -r requirements.txt
```

If you didn’t activate the venv, use the full path:

```powershell
.\.venv\Scripts\pip.exe install -r requirements.txt
```

This installs FastAPI, uvicorn, opencv-python, mediapipe, ultralytics (YOLO), scipy, sqlalchemy, fpdf2, etc. The first run may take a few minutes.

### 3.3 Run the API server

**Option A – using the script:**

```powershell
.\run.ps1
```

**Option B – direct command:**

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- API: **http://localhost:8000**
- Docs: **http://localhost:8000/docs**
- Health: **http://localhost:8000/health**

On startup the app:

- Creates `uploads/` and `reports/` if missing
- Creates SQLite DB and tables (default: `./dms.db`)

### 3.4 Optional: environment overrides

Create `backend/.env` to override defaults (see `app/core/config.py`):

```env
database_url=sqlite:///./dms.db
upload_dir=uploads
report_dir=reports
target_fps=10.0
clip_pre_event_sec=5.0
clip_post_event_sec=5.0
```

---

## 4. Frontend: setup and run

### 4.1 Install dependencies

```powershell
cd d:\WORK\DMS\frontend
npm install
```

### 4.2 Run the dev server

```powershell
npm run dev
```

- App: **http://localhost:5173**
- Vite proxies `/api` and `/health` to `http://localhost:8000`, so the UI talks to the backend without CORS issues.

### 4.3 Other scripts

- **Build for production:** `npm run build` (output in `dist/`)
- **Preview production build:** `npm run preview`

---

## 5. Running the full stack

1. **Terminal 1 – Backend**
   ```powershell
   cd d:\WORK\DMS\backend
   .\.venv\Scripts\Activate.ps1
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **Terminal 2 – Frontend**
   ```powershell
   cd d:\WORK\DMS\frontend
   npm run dev
   ```

3. Open **http://localhost:5173** in the browser.

The frontend will show the upload panel, trip list, and (after a trip is processed) progress, events, scores, and PDF report link.

---

## 6. Testing

The project does **not** include its own test suites (no pytest or Vitest config in the repo). Below: **manual testing** and **optional automated tests**.

### 6.1 Quick smoke test (backend only)

With the backend running:

```powershell
# Health check
curl http://localhost:8000/health

# Expected: {"status":"ok"}
```

Or open **http://localhost:8000/docs** and try:

- `GET /health`
- `GET /api/trips` (should return `[]` or a list of trips)

### 6.2 Manual end-to-end test (full stack)

1. Start backend and frontend as in **§5**.
2. Open **http://localhost:5173**.
3. **Upload a trip**
   - Day folder: e.g. `2025-02-12`
   - Optionally set Driver ID and Vehicle ID
   - Add **at least one front-camera MP4** (cabin MP4s optional)
   - Click **Analyze** (or equivalent CTA)
4. **Verify**
   - A new trip appears with status “processing” then “done” (or “failed” if something broke).
   - When status is “done”: events table, KPI scores, and PDF report link appear.
5. **Trip list**
   - Confirm the new trip shows in the trip history; open it and check events/scores again.

**Video format:** Any MP4 is accepted. For the legacy “analyze/day” flow, front/cabin are distinguished by filename: clips ending with `_rear.mp4` are treated as cabin; others as front. See `app/utils/file_parser.py` (e.g. pattern `HHMMSS_seq_rear.mp4`).

### 6.3 Testing the API with curl (examples)

```powershell
# List trips
curl http://localhost:8000/api/trips

# Get a specific trip (replace TRIP_ID)
curl http://localhost:8000/api/trips/TRIP_ID

# Get events for a trip
curl http://localhost:8000/api/trips/TRIP_ID/events

# Get scores for a trip
curl http://localhost:8000/api/trips/TRIP_ID/scores
```

Upload via API (multipart):

```powershell
curl -X POST http://localhost:8000/api/trips `
  -F "day_folder=2025-02-12" `
  -F "front_files=@path\to\front.mp4"
```

Then trigger processing:

```powershell
curl -X POST http://localhost:8000/api/trips/TRIP_ID/complete-upload
```

### 6.4 Adding backend tests (optional)

To add automated API tests with pytest:

```powershell
cd d:\WORK\DMS\backend
pip install pytest httpx
```

Create `backend/tests/conftest.py`:

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    return TestClient(app)
```

Create `backend/tests/test_api.py`:

```python
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}

def test_list_trips_empty(client):
    r = client.get("/api/trips")
    assert r.status_code == 200
    assert r.json() == []
```

Run:

```powershell
pytest tests/ -v
```

You can extend this with temporary DB, file uploads, and `complete-upload` + polling for status.

### 6.5 Adding frontend tests (optional)

To add unit/component tests with Vitest:

```powershell
cd d:\WORK\DMS\frontend
npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom
```

Add in `package.json` under `"scripts"`:

```json
"test": "vitest",
"test:run": "vitest run"
```

Create `frontend/vitest.config.ts` (or add in `vite.config.ts`) and run:

```powershell
npm run test
# or
npm run test:run
```

---

## 7. API endpoints summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/api/trips` | Create trip (multipart: day_folder, driver_id, vehicle_id, front_files, cabin_files) |
| POST | `/api/trips/{id}/complete-upload` | Start processing a trip |
| GET | `/api/trips` | List trips (query: `limit`) |
| GET | `/api/trips/{id}` | Get trip by id |
| GET | `/api/trips/{id}/events` | Get events for trip |
| GET | `/api/trips/{id}/scores` | Get scores for trip |
| POST | `/api/analyze/day` | Legacy: single-call analyze (day_folder + files) |
| GET | `/api/jobs/{job_id}` | Legacy: job status |
| GET | `/api/reports/{job_id}` | Legacy: JSON report |

Static files:

- `/uploads/...` – uploaded trip videos and artifacts
- `/reports/...` – generated report files (e.g. PDF)

---

## 8. Troubleshooting

| Issue | What to check |
|-------|----------------|
| Frontend shows “Trip submission failed” or network errors | Backend running on port 8000? Try http://localhost:8000/health and http://localhost:8000/docs. |
| CORS errors | Backend already allows all origins; ensure you use the Vite dev server (http://localhost:5173) so requests go through the proxy. |
| “No front MP4 files” | At least one file must have a `.mp4` extension and be sent as front (or without `_rear` in name for legacy endpoint). |
| Processing stays “processing” or fails | Check backend terminal for Python tracebacks; ensure OpenCV/MediaPipe/YOLO load (e.g. no missing DLLs on Windows). |
| Database locked / SQLite errors | Only one process should write to the DB; avoid multiple uvicorn instances pointing at the same `dms.db`. |
| Port already in use | Change port: e.g. `uvicorn app.main:app --port 8001` and update frontend proxy in `vite.config.ts` to `8001`. |

---

## 9. Summary checklist

- [ ] Python 3.10+ and Node 18+ installed  
- [ ] Backend: `cd backend` → venv → `pip install -r requirements.txt` → `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`  
- [ ] Frontend: `cd frontend` → `npm install` → `npm run dev`  
- [ ] Open http://localhost:5173  
- [ ] Smoke test: http://localhost:8000/health returns `{"status":"ok"}`  
- [ ] E2E: Upload at least one front MP4 → Analyze → wait for “done” → check events, scores, and PDF  

For more on architecture and data schema, see `README.md` and `SYSTEM_DESIGN.md`.

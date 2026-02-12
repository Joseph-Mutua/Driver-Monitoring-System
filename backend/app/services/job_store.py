from __future__ import annotations

import threading
from app.schemas.report import JobStatus


class JobStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, JobStatus] = {}

    def create(self, job_id: str, message: str = "Queued") -> JobStatus:
        status = JobStatus(job_id=job_id, status="queued", message=message, progress=0.0)
        with self._lock:
            self._jobs[job_id] = status
        return status

    def update(self, job_id: str, **kwargs) -> JobStatus | None:
        with self._lock:
            status = self._jobs.get(job_id)
            if not status:
                return None
            for key, value in kwargs.items():
                setattr(status, key, value)
            self._jobs[job_id] = status
            return status

    def get(self, job_id: str) -> JobStatus | None:
        with self._lock:
            return self._jobs.get(job_id)


job_store = JobStore()

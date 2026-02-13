from __future__ import annotations

import subprocess
import threading
import uuid
from datetime import datetime
from pathlib import Path

from app.core.config import settings
from app.schemas.ml import MlPipelineJob, MlPipelineRunRequest


class MlPipelineService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, MlPipelineJob] = {}
        self._procs: dict[str, subprocess.Popen] = {}

    def _backend_root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    def _reports_root(self) -> Path:
        root = Path(settings.report_dir) / "ml_jobs"
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _normalize_manifest(self, value: str) -> Path:
        p = Path(value)
        if not p.is_absolute():
            p = self._backend_root() / p
        return p.resolve()

    def _normalize_output_root(self, value: str) -> Path:
        p = Path(value)
        if not p.is_absolute():
            p = self._backend_root() / p
        p.mkdir(parents=True, exist_ok=True)
        return p.resolve()

    def _normalize_optional(self, value: str | None) -> Path | None:
        if not value:
            return None
        p = Path(value)
        if not p.is_absolute():
            p = self._backend_root() / p
        return p.resolve()

    def _set_job(self, job: MlPipelineJob) -> None:
        with self._lock:
            self._jobs[job.job_id] = job

    def _get_job(self, job_id: str) -> MlPipelineJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def _artifact_urls(self, job_id: str, artifacts: dict[str, str]) -> dict[str, str]:
        return {key: f"/api/ml/pipeline/jobs/{job_id}/artifacts/{key}" for key in artifacts.keys()}

    def run(self, body: MlPipelineRunRequest) -> MlPipelineJob:
        manifest = self._normalize_manifest(body.manifest)
        if not manifest.exists():
            raise FileNotFoundError(f"Manifest not found: {manifest}")

        output_root = self._normalize_output_root(body.output_root)
        ground_truth = self._normalize_optional(body.ground_truth)
        if ground_truth and not ground_truth.exists():
            raise FileNotFoundError(f"Ground truth not found: {ground_truth}")

        job_id = str(uuid.uuid4())
        started = datetime.utcnow()
        log_path = self._reports_root() / f"{job_id}.log"

        job = MlPipelineJob(
            job_id=job_id,
            status="queued",
            message="Queued for training pipeline",
            manifest=str(manifest),
            output_root=str(output_root),
            ground_truth=str(ground_truth) if ground_truth else None,
            started_at=started,
            log_url=f"/reports/ml_jobs/{job_id}.log",
        )
        self._set_job(job)

        thread = threading.Thread(
            target=self._run_job,
            args=(job_id, manifest, output_root, ground_truth, log_path),
            daemon=True,
        )
        thread.start()
        return job

    def _run_job(self, job_id: str, manifest: Path, output_root: Path, ground_truth: Path | None, log_path: Path) -> None:
        job = self._get_job(job_id)
        if not job:
            return

        job.status = "running"
        job.message = "Training pipeline started"
        self._set_job(job)

        cmd = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            "ml\\scripts\\run_pipeline.ps1",
            "-Manifest",
            str(manifest),
            "-OutputRoot",
            str(output_root),
        ]
        if ground_truth:
            cmd.extend(["-GroundTruth", str(ground_truth)])

        try:
            with log_path.open("w", encoding="utf-8") as logf:
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(self._backend_root()),
                    stdout=logf,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                with self._lock:
                    self._procs[job_id] = proc
                rc = proc.wait()

            current = self._get_job(job_id)
            cancelled = bool(current and current.status == "cancelled")
            if cancelled:
                job.status = "cancelled"
                job.message = "Pipeline cancelled"
                job.error = None
            elif rc != 0:
                job.status = "failed"
                job.message = f"Pipeline failed (exit code {rc})"
                job.error = f"Non-zero exit code: {rc}"
            else:
                artifacts = {
                    "dataset_validation": str((output_root / "dataset_validation.json").resolve()),
                    "predictions_val": str((output_root / "predictions_val.csv").resolve()),
                    "calibration": str((output_root / "calibration.json").resolve()),
                    "release_metrics": str((output_root / "release_metrics.json").resolve()),
                    "best_model": str((output_root / "detector_run" / "weights" / "best.pt").resolve()),
                }
                job.artifacts = {k: v for k, v in artifacts.items() if Path(v).exists()}
                job.artifact_urls = self._artifact_urls(job_id, job.artifacts)
                job.status = "completed"
                job.message = "Pipeline completed"
                job.error = None
        except Exception as exc:
            job.status = "failed"
            job.message = "Pipeline crashed"
            job.error = str(exc)

        job.finished_at = datetime.utcnow()
        self._set_job(job)
        with self._lock:
            self._procs.pop(job_id, None)

    def list_jobs(self) -> list[MlPipelineJob]:
        with self._lock:
            return sorted(self._jobs.values(), key=lambda j: j.started_at, reverse=True)

    def get_job(self, job_id: str) -> MlPipelineJob | None:
        return self._get_job(job_id)

    def read_log_tail(self, job_id: str, max_chars: int = 12000) -> str:
        log_path = self._reports_root() / f"{job_id}.log"
        if not log_path.exists():
            return ""
        text = log_path.read_text(encoding="utf-8", errors="ignore")
        return text[-max_chars:]

    def cancel_job(self, job_id: str) -> MlPipelineJob | None:
        job = self._get_job(job_id)
        if not job:
            return None
        if job.status in {"completed", "failed", "cancelled"}:
            return job

        proc = None
        with self._lock:
            proc = self._procs.get(job_id)

        if proc and proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass

        job.status = "cancelled"
        job.message = "Cancellation requested"
        job.finished_at = datetime.utcnow()
        self._set_job(job)
        return job

    def retry_job(self, job_id: str) -> MlPipelineJob | None:
        job = self._get_job(job_id)
        if not job:
            return None
        body = MlPipelineRunRequest(
            manifest=job.manifest,
            output_root=job.output_root,
            ground_truth=job.ground_truth,
        )
        return self.run(body)

    def artifact_path(self, job_id: str, artifact_key: str) -> Path | None:
        job = self._get_job(job_id)
        if not job:
            return None
        artifact = job.artifacts.get(artifact_key)
        if not artifact:
            return None
        p = Path(artifact)
        if not p.exists():
            return None
        return p


ml_pipeline_service = MlPipelineService()

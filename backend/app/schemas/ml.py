from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class MlPipelineRunRequest(BaseModel):
    manifest: str
    output_root: str
    ground_truth: str | None = None


class MlPipelineJob(BaseModel):
    job_id: str
    status: str
    message: str = ""
    manifest: str
    output_root: str
    ground_truth: str | None = None
    started_at: datetime
    finished_at: datetime | None = None
    log_url: str | None = None
    artifacts: dict[str, str] = Field(default_factory=dict)
    artifact_urls: dict[str, str] = Field(default_factory=dict)
    error: str | None = None


class MlPipelineJobList(BaseModel):
    jobs: list[MlPipelineJob] = Field(default_factory=list)


class MlPipelineLogResponse(BaseModel):
    job_id: str
    log_tail: str


class MlPipelineActionResponse(BaseModel):
    job_id: str
    status: str
    message: str

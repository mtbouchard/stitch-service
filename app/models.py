"""Pydantic schemas and the in-memory job model.

These are shared by the stub you implement and the reference solution, so the contract
(field names, status values) is identical either way.
"""
from enum import Enum

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class UploadResponse(BaseModel):
    id: str


class StitchRequest(BaseModel):
    # Two-or-more image ids returned by /upload. We require >= 2 to stitch.
    images: list[str] = Field(min_length=2)


class JobCreatedResponse(BaseModel):
    job_id: str
    status: JobStatus


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    error: str | None = None


class Job(BaseModel):
    id: str
    status: JobStatus = JobStatus.PENDING
    image_ids: list[str] = []
    result_path: str | None = None
    error: str | None = None

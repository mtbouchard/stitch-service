"""
Complete reference implementation of the job endpoints. This is the "fall back on" copy.

Don't read it until you've taken a real swing at app/routers/jobs.py - or run it any time
with USE_REFERENCE=1 to see the intended behavior. To hand the assignment off to this
version permanently: `cp reference/jobs_reference.py app/routers/jobs.py`.
"""
import os
import shutil
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app import compute
from app.config import settings
from app.models import (
    Job,
    JobCreatedResponse,
    JobStatus,
    JobStatusResponse,
    StitchRequest,
    UploadResponse,
)
from app.store import jobs, uploads

router = APIRouter(tags=["jobs"])


def run_stitch_job(job_id: str) -> None:
    """Runs in a threadpool (plain def background task). Does the actual stitching."""
    job = jobs.get(job_id)
    if job is None:
        return
    job.status = JobStatus.RUNNING
    try:
        paths = [uploads[i] for i in job.image_ids]
        out_path = str(settings.results_dir / f"{job_id}.jpg")
        compute.stitch_images(paths, out_path)
        job.result_path = out_path
        job.status = JobStatus.DONE
    except Exception as exc:  # noqa: BLE001 - record failure, never crash the worker
        job.status = JobStatus.FAILED
        job.error = str(exc)


@router.post("/upload", response_model=UploadResponse)
def upload_image(file: UploadFile = File(...)):
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File must be an image")

    image_id = uuid4().hex[:12]
    path = str(settings.uploads_dir / f"{image_id}.jpg")

    size = 0
    with open(path, "wb") as out:
        while chunk := file.file.read(1024 * 1024):
            size += len(chunk)
            if size > settings.max_upload_bytes:
                out.close()
                os.remove(path)
                raise HTTPException(
                    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File too large"
                )
            out.write(chunk)

    uploads[image_id] = path
    return UploadResponse(id=image_id)


@router.post(
    "/stitch",
    response_model=JobCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_stitch(req: StitchRequest, background_tasks: BackgroundTasks):
    for image_id in req.images:
        if image_id not in uploads:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Image id not found: {image_id}")

    job_id = uuid4().hex[:12]
    jobs[job_id] = Job(id=job_id, status=JobStatus.PENDING, image_ids=list(req.images))
    background_tasks.add_task(run_stitch_job, job_id)
    return JobCreatedResponse(job_id=job_id, status=JobStatus.PENDING)


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job(job_id: str):
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    return JobStatusResponse(job_id=job.id, status=job.status, error=job.error)


@router.get("/jobs/{job_id}/result")
def get_job_result(job_id: str):
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    if job.status is JobStatus.FAILED:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Job failed: {job.error}")
    if job.status is not JobStatus.DONE or job.result_path is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Job not finished (status: {job.status.value})"
        )
    return FileResponse(job.result_path, media_type="image/jpeg")

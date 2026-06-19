"""
=============================================================================
ASSIGNMENT - this is the file YOU implement. See ASSIGNMENT.md for the brief.
=============================================================================

Build four endpoints on `router`. The plumbing around you is already done:
  - app.config.settings     -> settings.uploads_dir, settings.results_dir, settings.max_upload_bytes
  - app.models              -> JobStatus, UploadResponse, StitchRequest, JobCreatedResponse,
                               JobStatusResponse, Job
  - app.store               -> uploads (dict id->path), jobs (dict id->Job)
  - app.compute             -> stitch_images(image_paths: list[str], out_path: str)

Endpoints to build:

  POST /upload   (multipart form field "file")
      - reject non-image content types with 400
      - reject files larger than settings.max_upload_bytes with 413
      - save under settings.uploads_dir as "<id>.jpg", record uploads[id] = path
      - return UploadResponse(id=...)

  POST /stitch   body: StitchRequest {"images": [id1, id2, ...]}   -> 202
      - resolve every id in uploads (404 if any is unknown)
      - create a Job (status pending), store it in jobs
      - kick off the work in the background (BackgroundTasks) so this returns immediately
      - return JobCreatedResponse(job_id=..., status=pending)

  GET /jobs/{job_id}                 -> JobStatusResponse (404 if unknown)

  GET /jobs/{job_id}/result          -> FileResponse(image/jpeg)
      - 404 unknown job; 409 if not done yet; 500 if failed

Hint: write a `run_stitch_job(job_id)` helper (a plain def, so BackgroundTasks runs it in
a threadpool) that sets status running -> calls compute.stitch_images -> sets done +
result_path, or failed + error.
"""
from fastapi import APIRouter

router = APIRouter(tags=["jobs"])

# Your code here.

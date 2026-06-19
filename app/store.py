"""In-memory stores for uploads and jobs.

This is deliberately the simplest thing that works, so the focus stays on the API shape.
Two honest limitations to call out in an interview:
  - It lives in the web process, so a restart loses everything.
  - It doesn't scale past one process/machine.
The production upgrade is Redis (or a DB) for jobs + object storage (S3/R2) for the files;
the HTTP contract stays identical. nerf-service shows that next step.
"""
from .models import Job

# image_id -> absolute path of the stored upload
uploads: dict[str, str] = {}

# job_id -> Job
jobs: dict[str, Job] = {}


def reset_state() -> None:
    uploads.clear()
    jobs.clear()

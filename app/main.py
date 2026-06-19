"""Application entrypoint.

Run locally:
    uv run uvicorn app.main:app --reload          # runs YOUR stub (app/routers/jobs.py)
    USE_REFERENCE=1 uv run uvicorn app.main:app    # runs the complete reference

On Render the start command is:
    uvicorn app.main:app --host 0.0.0.0 --port $PORT

The USE_REFERENCE toggle lets you (a) see a working version any time, and (b) deploy a
green service before you've finished the assignment. Default = your code.
"""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from .config import settings
from .routers import health

# Pick which implementation of the job endpoints to mount.
if os.environ.get("USE_REFERENCE") == "1":
    from reference import jobs_reference as jobs
else:
    from .routers import jobs

# Make sure the data dirs exist before any request touches them.
settings.uploads_dir.mkdir(parents=True, exist_ok=True)
settings.results_dir.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Upload images, stitch them into one via an async job, poll, and download.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(jobs.router)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def landing():
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{settings.app_name}</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 680px; margin: 64px auto;
         padding: 0 20px; line-height: 1.6; }}
  code, pre {{ background:#f0f0f3; padding:2px 6px; border-radius:4px; }}
  a {{ color:#2563eb; }}
</style></head>
<body>
  <h1>{settings.app_name}</h1>
  <p>Upload images, then start a job that stitches them into one panorama-style image.
     Submit returns a <code>job_id</code>; poll it, then download the result.</p>
  <ul>
    <li><a href="/docs">Interactive API docs (/docs)</a></li>
    <li><a href="/healthz">Health check (/healthz)</a></li>
  </ul>
  <pre><code>POST /upload         (multipart "file")        -> {{"id": "..."}}
POST /stitch         {{"images": [id1, id2]}}   -> 202 {{"job_id": "...", "status": "pending"}}
GET  /jobs/&lt;job_id&gt;                            -> {{"status": "done", ...}}
GET  /jobs/&lt;job_id&gt;/result                     -> image/jpeg</code></pre>
</body></html>"""

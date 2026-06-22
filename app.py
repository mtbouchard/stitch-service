"""
stitch-service — a small FastAPI service that stitches two uploaded images into one.

Upload two images, then call /stitch: the server stages them and runs an external compute
script (stitch.py) via an awaited subprocess, returning the stitched image in the same
response. solution_app.py is an equivalent reference implementation.

Run:
    uvicorn app:app --reload
    pytest
    uvicorn solution_app:app --reload
"""
import asyncio
import os
import shutil
import sys
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

# --- paths (anchored to this file, so cwd never matters) ---------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"          # saved uploads live here as <id>.jpg
STAGE_DIR = DATA_DIR / "stage"              # stitch.py reads HARDCODED names in here
STAGE1_PATH = STAGE_DIR / "s1.jpg"
STAGE2_PATH = STAGE_DIR / "s2.jpg"
OUTPUT_PATH = STAGE_DIR / "output.jpg"
SCRIPT_PATH = BASE_DIR / "stitch.py"        # the no-arg compute script
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
STAGE_DIR.mkdir(parents=True, exist_ok=True)


# --- in-memory store (id -> saved file path) ---------------------------------
uploads: dict[str, str] = {}


def reset_state() -> None:
    """Used by the tests to start each case from a clean slate."""
    uploads.clear()


# --- app ---------------------------------------------------------------------
app = FastAPI(title="Stitch Service")
app.add_middleware(
    CORSMiddleware,
    allow_origins=(os.environ.get("CORS_ALLOW_ORIGINS", "*").split(",")),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


class StitchRequest(BaseModel):
    images: list[str]


# /stitch is `async def` on purpose: awaiting create_subprocess_exec runs the compute in a
# child process without parking a worker thread or blocking the event loop.
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if file.content_type != "image/jpeg": 
        raise HTTPException(status_code=400, 
        detail="Please upload a JPEG image")
    image_id = uuid4().hex[:8]
    path = os.path.join(UPLOADS_DIR, f"{image_id}.jpg")
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    uploads[image_id] = path
    return {"id": image_id}

@app.post("/stitch")
async def stitch_images(req: StitchRequest):
    if len(req.images) != 2:
        raise HTTPException(status_code=400,
        detail="We can only stitch two images at a time currently")
    try:
        src1 = uploads[req.images[0]]
        src2 = uploads[req.images[1]]
    except KeyError as exc:
        raise HTTPException(status_code=404,
        detail=f"Can't find image with id: {exc.args[0]}")
    shutil.copyfile(src1, STAGE1_PATH)
    shutil.copyfile(src2, STAGE2_PATH)
    proc = await asyncio.create_subprocess_exec(
        sys.executable, SCRIPT_PATH,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise HTTPException(status_code=500,
        detail=f"Stitching failed: {stderr.decode().strip()}")
    if not os.path.exists(OUTPUT_PATH):
        raise HTTPException(status_code=500,
        detail="Stitching failed: no output image produced")
    return FileResponse(OUTPUT_PATH, media_type="image/jpeg")
 

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def landing():
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{app.title}</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 680px; margin: 64px auto;
         padding: 0 20px; line-height: 1.6; }}
  code, pre {{ background:#f0f0f3; padding:2px 6px; border-radius:4px; }}
  a {{ color:#2563eb; }}
</style></head>
<body>
  <h1>{app.title}</h1>
  <p>Upload two images, then call <code>/stitch</code> to combine them. The server stages
     the images and runs an external compute script via an <b>awaited subprocess</b>, then
     returns the stitched image in the same response (no polling).</p>
  <ul>
    <li><a href="/docs">Interactive API docs (/docs)</a></li>
    <li><a href="/healthz">Health check (/healthz)</a></li>
  </ul>
  <pre><code>POST /upload         (multipart "file")        -> {{"id": "..."}}
POST /stitch         {{"images": [id1, id2]}}   -> image/jpeg (in the same response)</code></pre>
</body></html>"""

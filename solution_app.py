"""
stitch-service — complete single-file reference (the fallback).

Identical scaffolding to app.py, but the two endpoints are implemented. Run it any time:
    uvicorn solution_app:app --reload
    KATA_TARGET=solution_app pytest        # all green

Key idea: `async def` + `await asyncio.create_subprocess_exec(...)` runs the heavy compute
in a child process and yields to the event loop while it runs — no blocked loop, no parked
worker thread. The image comes back in the same response (no polling).
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
UPLOADS_DIR = DATA_DIR / "uploads"
STAGE_DIR = DATA_DIR / "stage"
STAGE1_PATH = STAGE_DIR / "s1.jpg"
STAGE2_PATH = STAGE_DIR / "s2.jpg"
OUTPUT_PATH = STAGE_DIR / "output.jpg"
SCRIPT_PATH = BASE_DIR / "stitch.py"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
STAGE_DIR.mkdir(parents=True, exist_ok=True)


# --- models ------------------------------------------------------------------
class UploadResponse(BaseModel):
    id: str


class StitchRequest(BaseModel):
    images: list[str]


# --- in-memory store (id -> saved file path) ---------------------------------
uploads: dict[str, str] = {}


def reset_state() -> None:
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


@app.post("/upload", response_model=UploadResponse)
def upload_image(file: UploadFile = File(...)):
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File must be an image")

    image_id = uuid4().hex[:12]
    path = str(UPLOADS_DIR / f"{image_id}.jpg")

    size = 0
    with open(path, "wb") as out:
        while chunk := file.file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES:
                out.close()
                os.remove(path)
                raise HTTPException(
                    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File too large"
                )
            out.write(chunk)

    uploads[image_id] = path
    return UploadResponse(id=image_id)


@app.post("/stitch")
async def stitch(req: StitchRequest):
    if len(req.images) != 2:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Exactly two image ids are required")

    try:
        src1 = uploads[req.images[0]]
        src2 = uploads[req.images[1]]
    except KeyError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Image id not found: {exc.args[0]}")

    # Stage the chosen images into the hardcoded names the no-arg script reads.
    shutil.copyfile(src1, STAGE1_PATH)
    shutil.copyfile(src2, STAGE2_PATH)

    # Awaited subprocess: heavy compute runs in a child process; the loop stays free.
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        str(SCRIPT_PATH),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"Stitch failed: {stderr.decode().strip()}",
        )
    if not OUTPUT_PATH.exists():
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "Pipeline finished but no output image"
        )

    return FileResponse(str(OUTPUT_PATH), media_type="image/jpeg")


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

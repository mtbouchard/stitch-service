"""
Complete reference - synchronous response + awaited external subprocess (the interview
mechanism). Run any time with USE_REFERENCE=1, or `cp` it over app/routers/stitch.py.

Key idea: `async def` + `await asyncio.create_subprocess_exec(...)` runs the heavy compute
in a child process and yields to the event loop while it runs - no blocked loop, no parked
worker thread. The image comes back in the same response (no polling).
"""
import asyncio
import os
import shutil
import sys
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.config import settings
from app.models import StitchRequest, UploadResponse
from app.store import uploads

router = APIRouter(tags=["stitch"])


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
                raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File too large")
            out.write(chunk)

    uploads[image_id] = path
    return UploadResponse(id=image_id)


@router.post("/stitch")
async def stitch(req: StitchRequest):
    if len(req.images) != 2:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Exactly two image ids are required")

    try:
        src1 = uploads[req.images[0]]
        src2 = uploads[req.images[1]]
    except KeyError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Image id not found: {exc.args[0]}")

    # Stage the chosen images into the hardcoded names the no-arg script reads.
    shutil.copyfile(src1, settings.stage1_path)
    shutil.copyfile(src2, settings.stage2_path)

    # Awaited subprocess: heavy compute runs in a child process; the loop stays free.
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        str(settings.script_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"Stitch failed: {stderr.decode().strip()}",
        )
    if not settings.output_path.exists():
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "Pipeline finished but no output image"
        )

    return FileResponse(str(settings.output_path), media_type="image/jpeg")

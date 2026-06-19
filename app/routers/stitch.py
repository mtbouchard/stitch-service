"""
=============================================================================
ASSIGNMENT - this is the file YOU implement. See ASSIGNMENT.md for the brief.
=============================================================================

Build two endpoints on `router`. Plumbing already done for you:
  - app.config.settings  -> uploads_dir, stage_dir, stage1_path, stage2_path, output_path,
                            script_path, max_upload_bytes
  - app.models           -> UploadResponse, StitchRequest
  - app.store            -> uploads (dict id -> path)
  - stitch.py (repo root)-> the no-arg compute script that reads the staged images

  POST /upload   (multipart "file")
      - 400 if not an image; 413 if larger than settings.max_upload_bytes
      - save under settings.uploads_dir as "<id>.jpg", record uploads[id] = path
      - return UploadResponse(id=...)

  POST /stitch   body StitchRequest {"images": [id1, id2]}   -> returns the image
      - require exactly two ids (400 otherwise); resolve both in uploads (404 if unknown)
      - STAGE: copy them to settings.stage1_path and settings.stage2_path
      - run the script WITHOUT blocking the event loop:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, str(settings.script_path),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
      - if proc.returncode != 0: raise 500 with stderr.decode()
      - return FileResponse(settings.output_path, media_type="image/jpeg")

This endpoint is `async def` on purpose: awaiting create_subprocess_exec runs the heavy
compute in a child process without parking a worker thread or blocking the loop.
"""
from fastapi import APIRouter

router = APIRouter(tags=["stitch"])

# Your code here.

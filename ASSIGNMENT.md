# Assignment — implement the stitch job API

Everything around the endpoints is already built (config, models, in-memory store, the
`stitch_images` compute function, the client, the tests, Docker/Render config). Your job is
to implement the four endpoints in **`app/routers/jobs.py`**.

## What to build

| Method & path | Behavior |
|---|---|
| `POST /upload` (multipart `file`) | 400 if not an image; 413 if bigger than `settings.max_upload_bytes`; save to `settings.uploads_dir/<id>.jpg`; record `uploads[id]=path`; return `{"id": ...}` |
| `POST /stitch` (`{"images":[id1,id2,...]}`) | resolve every id (404 if any unknown); create a `Job`; run the work in the background; **return 202** `{"job_id":..,"status":"pending"}` |
| `GET /jobs/{job_id}` | `{"job_id":..,"status":..,"error":..}` (404 if unknown) |
| `GET /jobs/{job_id}/result` | `FileResponse` JPEG when done; 404 unknown; 409 if not finished; 500 if failed |

Imports you'll want are listed at the top of `app/routers/jobs.py`.

## How to work

```bash
cd stitch-service
uv run pip install -r requirements-dev.txt    # or: pip install -r requirements-dev.txt

# run YOUR code while you build
uv run uvicorn app.main:app --reload
# open http://127.0.0.1:8000/docs and poke at it

# grade yourself (red until you implement; green when done)
PYTHONPATH=. uv run pytest

# peek at a working version any time
USE_REFERENCE=1 uv run uvicorn app.main:app --reload
PYTHONPATH=. USE_REFERENCE=1 uv run pytest      # should be all green
```

## If you get stuck
- Ask me to walk through any single endpoint — I'll explain, not just paste.
- Or read `reference/jobs_reference.py` (the complete fallback).
- To hand off entirely: `cp reference/jobs_reference.py app/routers/jobs.py`.

## Design notes worth being able to explain
- **Why 202 + poll** instead of returning the image inline: keeps the request short so a
  proxy can't time out a long job. (Here the work is fast, but the *shape* is what scales.)
- **Why a plain `def` background task**: Starlette runs it in a threadpool, so blocking
  work never freezes the event loop and your `GET /jobs/...` polls stay responsive.
- **Where this breaks at scale** (and the fix): the store is in-process memory — a restart
  loses jobs and you can't run more than one instance. Swap in Redis for jobs + S3/R2 for
  files. `nerf-service` takes that next step with a real external GPU worker.

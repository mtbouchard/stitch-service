# stitch-service

A small, **real, deployable** FastAPI service that accepts image uploads and stitches them
into a single image through an **asynchronous job** (submit → poll → download). It's a
clean demonstration of the pattern behind heavier pipelines: decouple upload from compute,
return `202 Accepted` with a `job_id`, and let the client poll for the result.

> Built over a holiday as a hands-on way to learn how an upload + async-compute API is
> packaged and deployed. Its bigger sibling, `nerf-service`, runs the same pattern with a
> real GPU worker (COLMAP + NeRF) on RunPod.

## API

```
POST /upload         multipart "file"          -> {"id": "..."}
POST /stitch         {"images": [id1, id2]}    -> 202 {"job_id": "...", "status": "pending"}
GET  /jobs/{job_id}                            -> {"job_id":..,"status":"pending|running|done|failed"}
GET  /jobs/{job_id}/result                     -> image/jpeg (409 if not ready)
GET  /healthz                                  -> {"status": "ok"}
GET  /docs                                     -> interactive OpenAPI docs
```

## Architecture

```
client ──upload──▶ API (FastAPI) ──save──▶ data/uploads/<id>.jpg
client ──stitch──▶ API ──202 job_id──▶ background task ──▶ compute.stitch_images ──▶ data/results/<job>.jpg
client ──poll────▶ API (job status)
client ──result──▶ API ──FileResponse──▶ stitched image
```

Job state and uploads live in an in-memory store (`app/store.py`). That's intentional for a
demo; the README's "scaling" note and `nerf-service` show the Redis + object-storage upgrade.

## Run locally

```bash
cd stitch-service
pip install -r requirements-dev.txt          # or: uv run pip install -r requirements-dev.txt

# the working reference (green out of the box)
USE_REFERENCE=1 uvicorn app.main:app --reload

# end-to-end client demo (new terminal)
SERVER_URL=http://127.0.0.1:8000 python client/client.py   # writes client/stitched_output.jpg
```

There's also a learning **assignment**: implement the endpoints yourself in
`app/routers/jobs.py` (drop `USE_REFERENCE`). See [`ASSIGNMENT.md`](./ASSIGNMENT.md).

## Tests

```bash
PYTHONPATH=. USE_REFERENCE=1 pytest    # reference: all green
PYTHONPATH=. pytest                    # your implementation
```

## Deploy to Render

1. Push this folder to its own GitHub repo (see the top-level deploy guide).
2. In Render: **New → Blueprint**, select the repo. Render reads `render.yaml` and creates
   the web service (build `pip install -r requirements.txt`, start
   `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, health check `/healthz`).
3. It deploys with `USE_REFERENCE=1` so it's green immediately. Once you've implemented your
   own handlers, set `USE_REFERENCE` to unset/empty in the Render dashboard and redeploy.
4. Your service is live at `https://stitch-service.onrender.com` (custom domain optional —
   see the deploy guide).

> Note: Render's free plan has an **ephemeral filesystem** and sleeps when idle. Uploaded
> files and in-memory jobs don't survive a restart — fine for a demo, and exactly the
> motivation for the object-storage upgrade described above.

## Container (optional)

```bash
docker build -t stitch-service .
docker run -p 8000:8000 -e USE_REFERENCE=1 stitch-service
```

## Layout

```
stitch-service/
  app/
    main.py            # FastAPI app, landing page, CORS, mounts health + jobs routers
    config.py          # env-driven settings (pydantic-settings)
    models.py          # Job + request/response schemas
    store.py           # in-memory uploads + jobs
    compute.py         # stitch_images() — Pillow, headless-safe (the "given" compute)
    routers/
      health.py
      jobs.py          # ← the assignment (you implement)
  reference/
    jobs_reference.py  # complete fallback (USE_REFERENCE=1)
  client/
    client.py          # upload → submit → poll → download
    sample_images/     # s1.jpg, s2.jpg
  tests/               # acceptance tests (the grading rubric)
  Dockerfile  render.yaml  requirements*.txt  pytest.ini
```

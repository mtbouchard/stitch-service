# stitch-service

A small, **real, deployable** FastAPI service that accepts two image uploads and stitches
them into one image. It replicates the **interview mechanism**: the client makes a single
request and waits; the server stages the images and runs an external compute script via an
**awaited subprocess** (`asyncio.create_subprocess_exec`), returning the image in the same
response — no polling.

> Built over a holiday to practice packaging a compute step behind a FastAPI service and
> deploying it for real. Its sibling, `nerf-service`, takes the same idea to a long-running
> GPU job with the `202 + poll` pattern.

## API

```
POST /upload         multipart "file"          -> {"id": "..."}
POST /stitch         {"images": [id1, id2]}    -> image/jpeg  (returned in the same response)
GET  /healthz                                  -> {"status": "ok"}
GET  /docs                                     -> interactive OpenAPI docs
```

## How it works

```
client ──upload──▶ API ──save──▶ data/uploads/<id>.jpg
client ──stitch──▶ API ──stage──▶ data/stage/s1.jpg, s2.jpg
                       └─ await asyncio.create_subprocess_exec(python stitch.py) ─▶ data/stage/output.jpg
                       └─ FileResponse(output.jpg) ─▶ client   (one request, no polling)
```

`stitch.py` is an external, no-arg script (the "heavy compute" stand-in) that reads the
**hardcoded staged paths** — exactly like the interview's `panorama.py`. The API's job is to
stage the chosen uploads into those names, run the script without blocking the event loop,
and stream back the result.

### Why `async def` + `await create_subprocess_exec`
The heavy compute runs in a **child process**; awaiting it yields to the event loop while it
runs, so there's no blocked loop **and** no parked worker thread (more scalable than a
threadpool'd `def` under load). For a seconds-long job, returning the image inline is the
right call; minute-long jobs want `202 + poll` instead (see `nerf-service`).

## Run locally

```bash
cd stitch-service
pip install -r requirements-dev.txt

USE_REFERENCE=1 uvicorn app.main:app --reload                 # working reference
SERVER_URL=http://127.0.0.1:8000 python client/client.py      # writes client/stitched_output.jpg
```

There's a learning **assignment**: implement the two endpoints yourself in
`app/routers/stitch.py` (drop `USE_REFERENCE`). See [`ASSIGNMENT.md`](./ASSIGNMENT.md).

## Tests

```bash
PYTHONPATH=. USE_REFERENCE=1 pytest    # reference: all green
PYTHONPATH=. pytest                    # your implementation
```

## Deploy to Render

Pushed to GitHub and connected to Render via `render.yaml` (Blueprint): build
`pip install -r requirements.txt`, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`,
health check `/healthz`. It ships with `USE_REFERENCE=1` so it's green immediately; once you
implement your own handlers, blank `USE_REFERENCE` in the Render dashboard and redeploy.
Auto-deploys on every push to `main`. (Set `STITCH_DELAY` to simulate heavier compute.)

> Free plan caveats: the service sleeps when idle and the filesystem is ephemeral — fine for
> a demo. Hardcoded staging also means one stitch at a time per instance; a real system
> would pass per-request paths or a job id.

## Layout

```
stitch-service/
  stitch.py            # external no-arg compute script (reads hardcoded staged paths)
  app/
    main.py            # app, landing, CORS, mounts health + stitch routers
    config.py          # env settings + staged/script paths
    models.py          # UploadResponse, StitchRequest
    store.py           # in-memory uploads (id -> path)
    routers/
      health.py
      stitch.py        # ← the assignment (you implement)
  reference/
    stitch_reference.py  # complete fallback (USE_REFERENCE=1)
  client/
    client.py          # upload x2 -> /stitch -> save image
    sample_images/
  tests/               # acceptance tests
  Dockerfile  render.yaml  requirements*.txt  pytest.ini
```

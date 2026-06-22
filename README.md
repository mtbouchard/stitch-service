# stitch-service

A small, deployable FastAPI service that accepts two image uploads and stitches them into
one. The client makes a single request and waits: the server stages the images and runs an
external compute script via an **awaited subprocess** (`asyncio.create_subprocess_exec`),
returning the result in the same response.

Its sibling, `nerf-service`, takes the same idea to a long-running job with the `202 + poll`
pattern.

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

`stitch.py` is an external, no-arg script that reads hardcoded staged paths; the API stages
the chosen uploads into those names, runs the script without blocking the event loop, and
streams back the result.

### Why `async def` + `await create_subprocess_exec`
The compute runs in a child process; awaiting it yields to the event loop while it runs, so
there's no blocked loop and no parked worker thread. For a seconds-long job, returning the
image inline is the right call; minute-long jobs want `202 + poll` instead (see `nerf-service`).

## Run locally

```bash
cd stitch-service
pip install -r requirements-dev.txt

uvicorn app:app --reload
SERVER_URL=http://127.0.0.1:8000 python client/client.py      # writes client/stitched_output.jpg
```

`solution_app.py` is an equivalent reference implementation.

## Tests

```bash
pytest                             # app.py
APP_MODULE=solution_app pytest     # the reference implementation
```

## Deploy to Render

Connected via `render.yaml` (Blueprint): build `pip install -r requirements.txt`, start
`uvicorn $APP_MODULE:app --host 0.0.0.0 --port $PORT`, health check `/healthz`. `APP_MODULE`
selects which module to serve (`app` or `solution_app`). Auto-deploys on every push to `main`.
(Set `STITCH_DELAY` to simulate heavier compute.)

> Free-tier caveats: the service sleeps when idle and the filesystem is ephemeral — fine for a
> demo. Hardcoded staging means one stitch at a time per instance; a real system would pass
> per-request paths or a job id.

## Layout

```
stitch-service/
  app.py               # the service (/upload + /stitch)
  solution_app.py      # equivalent reference implementation
  stitch.py            # external no-arg compute script (reads hardcoded staged paths)
  client/
    client.py          # upload x2 -> /stitch -> save image
    sample_images/
  tests/               # acceptance tests
  Dockerfile  render.yaml  requirements*.txt  pytest.ini
```

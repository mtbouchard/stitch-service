# Assignment — implement the synchronous stitch API

Everything around the endpoints is built (config, models, upload store, the external
`stitch.py` compute script, the client, tests, Docker/Render config). You implement the two
endpoints in **`app/routers/stitch.py`**.

This service uses the **interview mechanism**: the client makes one request and waits; the
server stages the images and runs the heavy compute via an **awaited subprocess**, returning
the image in the same response. (No polling — that pattern lives in `nerf-service`.)

## What to build

| Method & path | Behavior |
|---|---|
| `POST /upload` (multipart `file`) | 400 if not an image; 413 if bigger than `settings.max_upload_bytes`; save to `settings.uploads_dir/<id>.jpg`; record `uploads[id]=path`; return `{"id": ...}` |
| `POST /stitch` (`{"images":[id1,id2]}`) | exactly two ids (400 else); resolve both (404 if unknown); **stage** them into `settings.stage1_path`/`stage2_path`; **`await asyncio.create_subprocess_exec(...)`** to run `settings.script_path`; 500 with stderr on non-zero exit; return `FileResponse` of `settings.output_path` |

## The mechanism (the whole point)

```python
@router.post("/stitch")
async def stitch(req: StitchRequest):
    ...
    shutil.copyfile(src1, settings.stage1_path)   # staging (script reads hardcoded names)
    shutil.copyfile(src2, settings.stage2_path)
    proc = await asyncio.create_subprocess_exec(
        sys.executable, str(settings.script_path),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()      # <-- await: loop free, no parked thread
    if proc.returncode != 0:
        raise HTTPException(500, stderr.decode().strip())
    return FileResponse(str(settings.output_path), media_type="image/jpeg")
```

Why `async def` + `await create_subprocess_exec` (and not plain `def` + `subprocess.run`)?
- It runs the heavy compute in a **child process** and yields to the event loop while it
  runs — no blocked loop **and** no parked worker thread (so the server scales better under
  load than the threadpool'd `def`).
- It's the purpose-built tool for *processes*; `run_in_threadpool(subprocess.run)` also
  works but parks a thread babysitting a process the OS already runs independently.

## How to work

```bash
cd stitch-service
uv run pip install -r requirements-dev.txt

uv run uvicorn app.main:app --reload          # YOUR code
PYTHONPATH=. uv run pytest                     # grade yourself (red until implemented)

USE_REFERENCE=1 uv run uvicorn app.main:app --reload   # see it working
PYTHONPATH=. USE_REFERENCE=1 uv run pytest             # reference: all green
```

Stuck? Ask me to walk an endpoint, read `reference/stitch_reference.py`, or
`cp reference/stitch_reference.py app/routers/stitch.py`.

## Talking points
- **Don't block the event loop**: go `async def` + `await` real async APIs, or plain `def`
  (threadpooled). Never `async def` with a blocking call inside.
- **Sync response vs poll** is a *separate* decision driven by job length: seconds → return
  inline (here); minutes → `202 + poll` (nerf-service).
- **Staging**: because the script hardcodes its input names, the API copies the chosen
  images into those names before running it.
- **Limitation**: hardcoded staging means one stitch at a time per box (concurrent calls
  would clobber `s1.jpg`). Real systems pass per-request paths/dirs or a job id.

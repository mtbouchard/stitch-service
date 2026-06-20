# Assignment — implement the synchronous stitch API

Everything lives in one file: **`app.py`**. The models, the `uploads` dict, the staged
paths, `/healthz`, and the landing page are already there. You implement the two endpoints
marked `TODO` (look for "YOUR ASSIGNMENT"). `solution_app.py` is the complete reference if
you get stuck.

This service uses the **interview mechanism**: the client makes one request and waits; the
server stages the images and runs the external `stitch.py` via an **awaited subprocess**,
returning the image in the same response. (No polling — that pattern lives in `nerf-service`.)

## What to build (in `app.py`)

| Method & path | Behavior |
|---|---|
| `POST /upload` (multipart `file`) | 400 if not an image; 413 if bigger than `MAX_UPLOAD_BYTES`; save to `UPLOADS_DIR/<id>.jpg`; record `uploads[id]=path`; return `{"id": ...}` |
| `POST /stitch` (`{"images":[id1,id2]}`) | exactly two ids (400 else); resolve both (404 if unknown); **stage** them into `STAGE1_PATH`/`STAGE2_PATH`; **`await asyncio.create_subprocess_exec(...)`** to run `SCRIPT_PATH`; 500 with stderr on non-zero exit; return `FileResponse` of `OUTPUT_PATH` |

## The mechanism (the whole point)

```python
@app.post("/stitch")
async def stitch(req: StitchRequest):
    ...
    shutil.copyfile(src1, STAGE1_PATH)   # staging (script reads hardcoded names)
    shutil.copyfile(src2, STAGE2_PATH)
    proc = await asyncio.create_subprocess_exec(
        sys.executable, str(SCRIPT_PATH),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()      # <-- await: loop free, no parked thread
    if proc.returncode != 0:
        raise HTTPException(500, stderr.decode().strip())
    return FileResponse(str(OUTPUT_PATH), media_type="image/jpeg")
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

uv run uvicorn app:app --reload               # YOUR code
uv run pytest                                  # grade yourself (red until implemented)

uv run uvicorn solution_app:app --reload       # see it working
KATA_TARGET=solution_app uv run pytest          # reference: all green
```

Stuck? Ask me to walk an endpoint, or read `solution_app.py`.

## Talking points
- **Don't block the event loop**: go `async def` + `await` real async APIs, or plain `def`
  (threadpooled). Never `async def` with a blocking call inside.
- **Sync response vs poll** is a *separate* decision driven by job length: seconds → return
  inline (here); minutes → `202 + poll` (nerf-service).
- **Staging**: because the script hardcodes its input names, the API copies the chosen
  images into those names before running it.
- **Limitation**: hardcoded staging means one stitch at a time per box (concurrent calls
  would clobber `s1.jpg`). Real systems pass per-request paths/dirs or a job id.

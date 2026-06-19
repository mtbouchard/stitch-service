"""
Stitch-service client - the full upload -> submit -> poll -> download flow. (This is the
part you asked me to implement; it mirrors the style of the interview's client stub.)

Local:
    uv run uvicorn app.main:app --reload
    SERVER_URL=http://127.0.0.1:8000 python client/client.py

Deployed:
    SERVER_URL=https://stitch-service.onrender.com python client/client.py
"""
import os
import sys
import time

import httpx

BASE_URL = os.environ.get("SERVER_URL", "http://127.0.0.1:8000")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_DIR = os.path.join(BASE_DIR, "sample_images")
OUTPUT_FILE = os.path.join(BASE_DIR, "stitched_output.jpg")
POLL_TIMEOUT_S = 120


def upload_image(client: httpx.Client, path: str) -> str:
    with open(path, "rb") as f:
        files = {"file": (os.path.basename(path), f, "image/jpeg")}
        r = client.post("/upload", files=files)
    r.raise_for_status()
    image_id = r.json()["id"]
    print(f"  uploaded {os.path.basename(path)} -> id={image_id}")
    return image_id


def main() -> int:
    print(f"Target server: {BASE_URL}")
    with httpx.Client(base_url=BASE_URL, timeout=60.0) as client:
        print("STEP 1: upload images")
        try:
            ids = [
                upload_image(client, os.path.join(SAMPLE_DIR, "s1.jpg")),
                upload_image(client, os.path.join(SAMPLE_DIR, "s2.jpg")),
            ]
        except httpx.ConnectError:
            print(f"  Could not connect to {BASE_URL}. Is the server running?")
            return 1

        print("STEP 2: POST /stitch (start job)")
        r = client.post("/stitch", json={"images": ids})
        if r.status_code != 202:
            print(f"  unexpected status {r.status_code}: {r.text}")
            return 1
        job_id = r.json()["job_id"]
        print(f"  202 Accepted -> job_id={job_id}")

        print("STEP 3: poll until done")
        deadline = time.time() + POLL_TIMEOUT_S
        job = {"status": "pending"}
        while time.time() < deadline:
            job = client.get(f"/jobs/{job_id}").json()
            print(f"  status={job['status']}")
            if job["status"] in ("done", "failed"):
                break
            time.sleep(1)

        if job["status"] != "done":
            print(f"  job did not finish cleanly: {job}")
            return 1

        print("STEP 4: download result")
        r = client.get(f"/jobs/{job_id}/result")
        r.raise_for_status()
        with open(OUTPUT_FILE, "wb") as f:
            f.write(r.content)
    print(f"  saved -> {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

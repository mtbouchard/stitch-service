"""
Stitch-service client - upload two images, then one /stitch call that returns the image
directly in the same response (the server awaits an external subprocess).

Local:
    uvicorn solution_app:app --reload        # or: uvicorn app:app (your code)
    SERVER_URL=http://127.0.0.1:8000 python client/client.py

Deployed:
    SERVER_URL=https://stitch-service.onrender.com python client/client.py
"""
import os
import sys

import httpx

BASE_URL = os.environ.get("SERVER_URL", "http://127.0.0.1:8000")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_DIR = os.path.join(BASE_DIR, "sample_images")
OUTPUT_FILE = os.path.join(BASE_DIR, "stitched_output.jpg")


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
    # Generous timeout: the single request blocks for the whole compute (that's the point).
    with httpx.Client(base_url=BASE_URL, timeout=120.0) as client:
        print("STEP 1: upload images")
        try:
            id1 = upload_image(client, os.path.join(SAMPLE_DIR, "s1.jpg"))
            id2 = upload_image(client, os.path.join(SAMPLE_DIR, "s2.jpg"))
        except httpx.ConnectError:
            print(f"  Could not connect to {BASE_URL}. Is the server running?")
            return 1

        print("STEP 2: POST /stitch (returns the image in one response)")
        r = client.post("/stitch", json={"images": [id1, id2]})
        print(f"  status={r.status_code} content-type={r.headers.get('content-type')}")
        if r.status_code != 200:
            print(f"  error: {r.text}")
            return 1

        with open(OUTPUT_FILE, "wb") as f:
            f.write(r.content)
    print(f"STEP 3: saved result -> {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

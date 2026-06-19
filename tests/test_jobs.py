"""Acceptance tests = the hidden grading rubric for the assignment."""
import io

from PIL import Image

from tests.conftest import make_jpeg


def upload(client, color=(255, 0, 0), size=(120, 90)):
    return client.post(
        "/upload", files={"file": ("s.jpg", make_jpeg(color, size), "image/jpeg")}
    )


def test_health(client):
    assert client.get("/healthz").json() == {"status": "ok"}


def test_upload_returns_id(client):
    res = upload(client)
    assert res.status_code == 200
    assert isinstance(res.json()["id"], str) and res.json()["id"]


def test_upload_rejects_non_image(client):
    res = client.post("/upload", files={"file": ("x.txt", io.BytesIO(b"hello"), "text/plain")})
    assert res.status_code == 400


def test_upload_requires_file(client):
    assert client.post("/upload").status_code == 422


def test_stitch_happy_path(client):
    id1 = upload(client, (200, 30, 30), (100, 80)).json()["id"]
    id2 = upload(client, (30, 60, 200), (140, 80)).json()["id"]

    res = client.post("/stitch", json={"images": [id1, id2]})
    assert res.status_code == 202
    job_id = res.json()["job_id"]
    assert res.json()["status"] == "pending"

    # With TestClient, the background task completes before POST returns.
    status_res = client.get(f"/jobs/{job_id}")
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "done"

    result = client.get(f"/jobs/{job_id}/result")
    assert result.status_code == 200
    assert result.headers["content-type"] == "image/jpeg"
    out = Image.open(io.BytesIO(result.content))
    assert out.width == 240 and out.height == 80  # 100 + 140 at common height 80


def test_stitch_unknown_id_404(client):
    id1 = upload(client).json()["id"]
    assert client.post("/stitch", json={"images": [id1, "nope"]}).status_code == 404


def test_stitch_requires_two_images(client):
    id1 = upload(client).json()["id"]
    assert client.post("/stitch", json={"images": [id1]}).status_code == 422


def test_status_unknown_job_404(client):
    assert client.get("/jobs/doesnotexist").status_code == 404


def test_result_unknown_job_404(client):
    assert client.get("/jobs/doesnotexist/result").status_code == 404

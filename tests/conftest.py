"""Shared fixtures. Tests run against app.main:app, which mounts either your stub or the
reference depending on USE_REFERENCE. Run the suite both ways:

    pytest                       # tests YOUR app/routers/jobs.py
    USE_REFERENCE=1 pytest       # tests the reference (should be all green)
"""
import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.store import reset_state


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def fresh_state():
    reset_state()
    yield
    reset_state()


def make_jpeg(color=(255, 0, 0), size=(120, 90)):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG")
    buf.seek(0)
    return buf

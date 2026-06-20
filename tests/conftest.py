"""Shared fixtures. Tests run against whichever module KATA_TARGET names (default: app.py,
your code). Run the suite both ways:

    pytest                          # tests YOUR app.py
    KATA_TARGET=solution_app pytest # tests the reference (should be all green)
"""
import importlib
import io
import os

import pytest
from fastapi.testclient import TestClient
from PIL import Image

target = importlib.import_module(os.environ.get("KATA_TARGET", "app"))


@pytest.fixture()
def client():
    return TestClient(target.app)


@pytest.fixture(autouse=True)
def fresh_state():
    target.reset_state()
    yield
    target.reset_state()


def make_jpeg(color=(255, 0, 0), size=(120, 90)):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG")
    buf.seek(0)
    return buf

"""The compute step. This is the 'given' part (you don't have to write it) - analogous to
the panorama.py script from the interview, but here it's a plain in-process function
because the work is light (no GPU, milliseconds). nerf-service moves the heavy compute out
to a separate GPU worker.

Pillow only - no cv2, no matplotlib - so it's headless-safe on a server (the exact lesson
from the original interview failure).
"""
import time

from PIL import Image, ImageDraw

from .config import settings


def stitch_images(image_paths: list[str], out_path: str) -> None:
    """Stitch images left-to-right onto one canvas, normalized to a common height."""
    if settings.stitch_delay_seconds:
        time.sleep(settings.stitch_delay_seconds)  # stand in for heavier work

    imgs = [Image.open(p).convert("RGB") for p in image_paths]
    target_h = min(im.height for im in imgs)

    resized = []
    for im in imgs:
        if im.height != target_h:
            new_w = max(1, round(im.width * target_h / im.height))
            im = im.resize((new_w, target_h))
        resized.append(im)

    total_w = sum(im.width for im in resized)
    canvas = Image.new("RGB", (total_w, target_h), (240, 240, 240))
    x = 0
    for im in resized:
        canvas.paste(im, (x, 0))
        x += im.width

    draw = ImageDraw.Draw(canvas)
    draw.rectangle([(0, 0), (total_w, 24)], fill=(15, 23, 42))
    draw.text((8, 7), f"stitched {len(resized)} images", fill=(255, 255, 255))

    canvas.save(out_path, "JPEG", quality=90)

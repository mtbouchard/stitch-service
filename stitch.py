"""
External compute script. It takes NO arguments and reads HARDCODED staged paths: the API
stages the two chosen images into data/stage/s1.jpg and data/stage/s2.jpg before running
this, then reads the result from data/stage/output.jpg.

Pillow only (headless-safe). Paths are anchored to __file__ so cwd never matters.
Set STITCH_DELAY (seconds) to simulate heavier compute.
"""
import os
import sys
import time

from PIL import Image, ImageDraw

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STAGE_DIR = os.path.join(BASE_DIR, "data", "stage")

IMG1_PATH = os.path.join(STAGE_DIR, "s1.jpg")
IMG2_PATH = os.path.join(STAGE_DIR, "s2.jpg")
OUT_PATH = os.path.join(STAGE_DIR, "output.jpg")

DELAY = float(os.environ.get("STITCH_DELAY", "0"))


def main() -> int:
    if not os.path.exists(IMG1_PATH) or not os.path.exists(IMG2_PATH):
        print(f"Error: expected {IMG1_PATH} and {IMG2_PATH} to exist", file=sys.stderr)
        return 1

    try:
        if DELAY:
            time.sleep(DELAY)  # simulate heavier compute

        im1 = Image.open(IMG1_PATH).convert("RGB")
        im2 = Image.open(IMG2_PATH).convert("RGB")

        height = min(im1.height, im2.height)
        if im1.height != height:
            im1 = im1.resize((round(im1.width * height / im1.height), height))
        if im2.height != height:
            im2 = im2.resize((round(im2.width * height / im2.height), height))

        canvas = Image.new("RGB", (im1.width + im2.width, height), (240, 240, 240))
        canvas.paste(im1, (0, 0))
        canvas.paste(im2, (im1.width, 0))

        draw = ImageDraw.Draw(canvas)
        draw.rectangle([(0, 0), (canvas.width, 24)], fill=(15, 23, 42))
        draw.text((8, 7), "stitched (external subprocess)", fill=(255, 255, 255))

        canvas.save(OUT_PATH, "JPEG", quality=90)
        print(f"Success: wrote {OUT_PATH}")
        return 0
    except Exception as exc:  # noqa: BLE001 - surface to caller via stderr
        print(f"Error in stitch: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Assemble a frame directory (f000.png..) into a looping GIF using its durations.json.

Companion to src/frontend/scripts/capture-architecture-gif.mjs. Pillow-only (no ffmpeg).

Usage:
  python scripts/assemble_gif.py /tmp/archmap_dark  docs/images/app/overview/architecture-map.gif
  python scripts/assemble_gif.py /tmp/archmap_light docs/images/app/overview/architecture-map-light.gif
"""
import glob
import json
import os
import sys

from PIL import Image


def build(src_dir: str, out: str, width: int = 1120, colors: int = 160) -> None:
    frames = sorted(glob.glob(f"{src_dir}/f*.png"))
    if not frames:
        raise SystemExit(f"no frames in {src_dir}")
    durations = json.load(open(f"{src_dir}/durations.json"))
    imgs = [Image.open(f).convert("RGBA") for f in frames]

    def resize(im: Image.Image) -> Image.Image:
        if im.width <= width:
            return im
        return im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)

    imgs = [resize(im).convert("P", palette=Image.ADAPTIVE, colors=colors) for im in imgs]
    imgs[0].save(out, save_all=True, append_images=imgs[1:], duration=durations,
                 loop=0, optimize=True, disposal=2)
    print("wrote", out, os.path.getsize(out), "bytes,", len(imgs), "frames")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    build(sys.argv[1], sys.argv[2])

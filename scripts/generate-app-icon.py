#!/usr/bin/env python3
"""Generate Pathline launcher icons (Linux PNG; macOS ICNS when icnsutil is available)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ICON_DIR = ROOT / "assets" / "icon"
OUT_DIR = ICON_DIR / "generated"
ICNS_PATH = OUT_DIR / "Pathline.icns"
LINUX_PNG = OUT_DIR / "pathline-256.png"


def _pillow():
    try:
        from PIL import Image, ImageDraw

        return Image, ImageDraw
    except ImportError as exc:
        raise SystemExit(
            "Pillow is required. Run: python3 -m pip install pillow"
        ) from exc


def draw_icon(size: int):
    Image, ImageDraw = _pillow()
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pad = size * 0.12
    radius = size * 0.22

    draw.rounded_rectangle(
        (pad, pad, size - pad, size - pad),
        radius=radius,
        fill=(17, 17, 17, 255),
    )

    cx = cy = size / 2
    dot_r = size * 0.094
    draw.ellipse(
        (cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r),
        fill=(245, 245, 244, 255),
    )

    stroke = max(4, int(size * 0.055))

    def arc_box(scale: float):
        return (
            cx - size * scale,
            cy - size * scale,
            cx + size * scale,
            cy + size * scale,
        )

    for scale in (0.25, 0.16, 0.09):
        draw.arc(arc_box(scale), start=200, end=340, fill=(245, 245, 244, 255), width=stroke)

    accent = (34, 211, 238, 255)
    hx = cx + size * 0.18
    hy = cy
    arm = size * 0.075
    draw.line((hx, hy - arm, hx, hy + arm), fill=accent, width=max(3, int(size * 0.047)))
    draw.line((hx - arm * 0.55, hy, hx + arm * 1.35, hy), fill=accent, width=max(3, int(size * 0.047)))

    return img


def write_linux_icon() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    draw_icon(256).save(LINUX_PNG, format="PNG", optimize=True)
    print(f"Wrote {LINUX_PNG}")


def build_icns() -> None:
    try:
        from icnsutil import IcnsFile
    except ImportError as exc:
        raise SystemExit(
            "icnsutil is required for macOS icons. Run: python3 -m pip install -r scripts/requirements-launcher.txt"
        ) from exc

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    iconset = [
        ("icon_16x16.png", 16),
        ("icon_16x16@2x.png", 32),
        ("icon_32x32.png", 32),
        ("icon_32x32@2x.png", 64),
        ("icon_128x128.png", 128),
        ("icon_128x128@2x.png", 256),
        ("icon_256x256.png", 256),
        ("icon_256x256@2x.png", 512),
        ("icon_512x512.png", 512),
        ("icon_512x512@2x.png", 1024),
    ]

    icns = IcnsFile()
    for name, size in iconset:
        png = OUT_DIR / name
        draw_icon(size).save(png, format="PNG", optimize=True)
        icns.add_media(file=str(png))

    icns.write(str(ICNS_PATH))
    print(f"Wrote {ICNS_PATH}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--png-only",
        action="store_true",
        help="Generate Linux .desktop PNG only (no icnsutil needed)",
    )
    parser.add_argument(
        "--icns-only",
        action="store_true",
        help="Generate macOS ICNS only",
    )
    args = parser.parse_args()

    if args.png_only:
        write_linux_icon()
        return
    if args.icns_only:
        build_icns()
        return

    write_linux_icon()
    try:
        build_icns()
    except SystemExit:
        print("Skipped ICNS generation (icnsutil not installed).", file=sys.stderr)


if __name__ == "__main__":
    main()

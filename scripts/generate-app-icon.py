#!/usr/bin/env python3
"""Generate PromptPath macOS/Linux launcher icons from the brand SVG."""

from __future__ import annotations

from pathlib import Path

from icnsutil import IcnsFile
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ICON_DIR = ROOT / "assets" / "icon"
OUT_DIR = ICON_DIR / "generated"
ICNS_PATH = OUT_DIR / "PromptPath.icns"
PNG_PATH = OUT_DIR / "promptpath-1024.png"


def draw_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pad = size * 0.12
    radius = size * 0.22

    # Rounded square background
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
    arc_box = lambda scale: (
        cx - size * scale,
        cy - size * scale,
        cx + size * scale,
        cy + size * scale,
    )

    for scale in (0.25, 0.16, 0.09):
        draw.arc(arc_box(scale), start=200, end=340, fill=(245, 245, 244, 255), width=stroke)

    # Accent crosshair on the right arc
    accent = (34, 211, 238, 255)
    hx = cx + size * 0.18
    hy = cy
    arm = size * 0.075
    draw.line((hx, hy - arm, hx, hy + arm), fill=accent, width=max(3, int(size * 0.047)))
    draw.line((hx - arm * 0.55, hy, hx + arm * 1.35, hy), fill=accent, width=max(3, int(size * 0.047)))

    return img


def write_png(path: Path, size: int) -> None:
    draw_icon(size).save(path, format="PNG", optimize=True)


def build_icns() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_png(PNG_PATH, 1024)

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
        image = draw_icon(size)
        image.save(png, format="PNG", optimize=True)
        icns.add_media(file=str(png))

    icns.write(str(ICNS_PATH))
    print(f"Wrote {ICNS_PATH}")


def write_linux_icon() -> None:
    """Simple 256px PNG for .desktop launchers."""
    path = OUT_DIR / "promptpath-256.png"
    write_png(path, 256)
    print(f"Wrote {path}")


if __name__ == "__main__":
    build_icns()
    write_linux_icon()

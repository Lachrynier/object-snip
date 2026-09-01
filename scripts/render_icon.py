#!/usr/bin/env python3
"""Render the ObjectSnip app icon as deterministic SVG and PNG files."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw

DEFAULT_OUTPUT_DIRECTORY = Path("src/objectsnip/assets")
DEFAULT_PALETTE = {
    "background": "#46515B",
    "capture": "#F7FAFC",
    "cube_top": "#DCE5EB",
    "cube_left": "#AEBBC5",
    "cube_right": "#7F909D",
}


def geometry(size: int) -> dict[str, object]:
    """Return icon geometry scaled from the 1024-unit design space."""
    scale = size / 1024

    def point(x: float, y: float) -> tuple[float, float]:
        return x * scale, y * scale

    edge = 240.0
    dx = edge * math.cos(math.radians(30))
    dy = edge * math.sin(math.radians(30))
    center_x, center_y = 512.0, 512.0
    top = point(center_x, center_y - dy - edge / 2)
    left = point(center_x - dx, center_y - edge / 2)
    right = point(center_x + dx, center_y - edge / 2)
    middle = point(center_x, center_y + dy - edge / 2)
    left_bottom = point(center_x - dx, center_y + edge / 2)
    right_bottom = point(center_x + dx, center_y + edge / 2)
    bottom = point(center_x, center_y + dy + edge / 2)

    return {
        "radius": 112 * scale,
        "stroke": 30 * scale,
        "capture_segments": [
            (point(170, 320), point(170, 170), point(320, 170)),
            (point(704, 170), point(854, 170), point(854, 320)),
            (point(170, 704), point(170, 854), point(320, 854)),
            (point(704, 854), point(854, 854), point(854, 704)),
        ],
        "cube_top": [top, right, middle, left],
        "cube_left": [left, middle, bottom, left_bottom],
        "cube_right": [middle, right, right_bottom, bottom],
    }


def _hex_rgb(value: str) -> tuple[int, int, int]:
    value = value.removeprefix("#")
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))


def render_png(path: Path, size: int = 512, supersample: int = 4) -> None:
    """Render a crisp antialiased PNG using Pillow."""
    canvas_size = size * supersample
    icon_geometry = geometry(canvas_size)
    palette = {name: _hex_rgb(color) for name, color in DEFAULT_PALETTE.items()}
    image = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (0, 0, canvas_size - 1, canvas_size - 1),
        radius=icon_geometry["radius"],
        fill=palette["background"] + (255,),
    )
    draw.polygon(icon_geometry["cube_left"], fill=palette["cube_left"] + (255,))
    draw.polygon(icon_geometry["cube_right"], fill=palette["cube_right"] + (255,))
    draw.polygon(icon_geometry["cube_top"], fill=palette["cube_top"] + (255,))
    for points in icon_geometry["capture_segments"]:
        draw.line(
            points,
            fill=palette["capture"] + (255,),
            width=round(icon_geometry["stroke"]),
            joint="curve",
        )
    image.resize((size, size), Image.Resampling.LANCZOS).save(path, optimize=True)


def render_svg(path: Path) -> None:
    """Write the resolution-independent source artwork."""
    palette = DEFAULT_PALETTE
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg"
  width="1024" height="1024" viewBox="0 0 1024 1024">
  <rect width="1024" height="1024" rx="112" fill="{palette["background"]}"/>
  <path d="M304.154 392 512 512 512 752 304.154 632Z" fill="{palette["cube_left"]}"/>
  <path d="M512 512 719.846 392 719.846 632 512 752Z" fill="{palette["cube_right"]}"/>
  <path d="M512 272 719.846 392 512 512 304.154 392Z" fill="{palette["cube_top"]}"/>
  <g fill="none" stroke="{palette["capture"]}" stroke-width="30"
    stroke-linecap="round" stroke-linejoin="round">
    <path d="M170 320V170H320"/><path d="M704 170H854V320"/>
    <path d="M170 704V854H320"/><path d="M704 854H854V704"/>
  </g>
</svg>
'''
    path.write_text(svg, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-directory", type=Path, default=DEFAULT_OUTPUT_DIRECTORY
    )
    parser.add_argument("--size", type=int, default=512)
    args = parser.parse_args()
    args.output_directory.mkdir(parents=True, exist_ok=True)
    render_svg(args.output_directory / "objectsnip.svg")
    render_png(args.output_directory / f"objectsnip-{args.size}.png", args.size)


if __name__ == "__main__":
    main()

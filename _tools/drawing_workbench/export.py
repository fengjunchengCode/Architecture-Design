#!/usr/bin/env python3
"""Export semantic drawings to PNG without a browser runtime."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

try:
    from .schema import normalize_drawing
except ImportError:  # pragma: no cover - supports direct script execution.
    from schema import normalize_drawing


COLORS = {
    "functional_zone": ((51, 119, 89, 210), (73, 160, 118, 88)),
    "vehicle_flow": ((249, 115, 22, 235), (249, 115, 22, 40)),
    "pedestrian_flow": ((15, 118, 110, 235), (15, 118, 110, 40)),
    "main_entrance": ((220, 38, 38, 240), (220, 38, 38, 180)),
    "label": ((17, 24, 39, 230), (17, 24, 39, 190)),
}


def export_png(drawing: dict[str, Any], *, project_dir: Path, output_path: Path) -> dict[str, Any]:
    drawing = normalize_drawing(drawing)
    base_path = (project_dir / drawing["base_image"]["path"]).resolve()
    if not base_path.exists():
        raise FileNotFoundError(f"base image not found: {base_path}")
    if project_dir.resolve() not in base_path.parents:
        raise ValueError("base image path escapes project directory")

    image = Image.open(base_path).convert("RGBA")
    overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    font_regular, font_bold = _load_fonts(image.size)

    for obj in drawing["objects"]:
        _draw_object(draw, obj, image.size, font_bold)

    composed = Image.alpha_composite(image, overlay).convert("RGB")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    composed.save(output_path, quality=95)
    return {
        "ok": True,
        "path": str(output_path),
        "width": composed.width,
        "height": composed.height,
        "object_count": len(drawing["objects"]),
        "font": getattr(font_regular, "path", "default"),
    }


def _load_fonts(size: tuple[int, int]) -> tuple[ImageFont.ImageFont, ImageFont.ImageFont]:
    base_size = max(18, min(42, int(size[0] / 70)))
    candidates = [
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ]
    for path in candidates:
        if path.exists():
            try:
                return ImageFont.truetype(str(path), base_size), ImageFont.truetype(str(path), base_size + 2)
            except OSError:
                continue
    return ImageFont.load_default(), ImageFont.load_default()


def _draw_object(
    draw: ImageDraw.ImageDraw,
    obj: dict[str, Any],
    size: tuple[int, int],
    font: ImageFont.ImageFont,
) -> None:
    stroke, fill = COLORS.get(str(obj.get("type")), COLORS["label"])
    geometry = obj["geometry"]
    kind = geometry["kind"]
    coords = [_pixel(point, size) for point in geometry["coords"]]
    label = str(obj.get("label") or "")

    if kind == "polygon":
        draw.polygon(coords, fill=fill)
        draw.line(coords + [coords[0]], fill=stroke, width=_line_width(size, 0.004), joint="curve")
        if label:
            _draw_label(draw, label, _centroid(coords), stroke, font, size)
        return

    if kind in {"polyline", "arrow"}:
        width = _line_width(size, 0.007)
        draw.line(coords, fill=stroke, width=width, joint="curve")
        if kind == "arrow" or obj.get("type") in {"vehicle_flow", "pedestrian_flow"}:
            _draw_arrow_head(draw, coords[-2], coords[-1], stroke, max(width * 2.5, 24))
        if label:
            _draw_label(draw, label, coords[len(coords) // 2], stroke, font, size)
        return

    if kind == "point":
        radius = _line_width(size, 0.012)
        x, y = coords[0]
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=fill, outline=(255, 255, 255, 230), width=4)
        if label:
            _draw_label(draw, label, (x + radius, y - radius), stroke, font, size)


def _pixel(point: list[float], size: tuple[int, int]) -> tuple[float, float]:
    return point[0] * size[0], point[1] * size[1]


def _line_width(size: tuple[int, int], ratio: float) -> int:
    return max(3, int(min(size) * ratio))


def _centroid(coords: list[tuple[float, float]]) -> tuple[float, float]:
    return (
        sum(point[0] for point in coords) / len(coords),
        sum(point[1] for point in coords) / len(coords),
    )


def _draw_arrow_head(
    draw: ImageDraw.ImageDraw,
    start: tuple[float, float],
    end: tuple[float, float],
    color: tuple[int, int, int, int],
    size: float,
) -> None:
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    left = (end[0] - size * math.cos(angle - math.pi / 6), end[1] - size * math.sin(angle - math.pi / 6))
    right = (end[0] - size * math.cos(angle + math.pi / 6), end[1] - size * math.sin(angle + math.pi / 6))
    draw.polygon([end, left, right], fill=color)


def _draw_label(
    draw: ImageDraw.ImageDraw,
    text: str,
    point: tuple[float, float],
    color: tuple[int, int, int, int],
    font: ImageFont.ImageFont,
    image_size: tuple[int, int],
) -> None:
    x, y = point
    bbox = draw.textbbox((0, 0), text, font=font)
    padding_x = 12
    padding_y = 7
    width = bbox[2] - bbox[0] + padding_x * 2
    height = bbox[3] - bbox[1] + padding_y * 2
    x = min(max(8, x + 12), max(8, image_size[0] - width - 8))
    y = min(max(8, y - height - 8), max(8, image_size[1] - height - 8))
    draw.rounded_rectangle(
        (x, y, x + width, y + height),
        radius=6,
        fill=(color[0], color[1], color[2], 218),
        outline=(255, 255, 255, 190),
        width=2,
    )
    draw.text((x + padding_x, y + padding_y - bbox[1]), text, font=font, fill=(255, 255, 255, 255))


def main() -> int:
    parser = argparse.ArgumentParser(description="Export semantic drawing JSON to PNG")
    parser.add_argument("project_dir", type=Path)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    drawing = json.loads(args.input.read_text(encoding="utf-8"))
    result = export_png(drawing, project_dir=args.project_dir, output_path=args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

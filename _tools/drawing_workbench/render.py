#!/usr/bin/env python3
"""Render semantic drawing JSON to a portable HTML/SVG sheet."""
from __future__ import annotations

import argparse
import json
from html import escape
from pathlib import Path
from typing import Any

try:
    from .schema import normalize_drawing
except ImportError:  # pragma: no cover - supports direct script execution.
    from schema import normalize_drawing


STYLE = {
    "functional_zone": {
        "stroke": "#256d4f",
        "fill": "rgba(60, 145, 110, 0.30)",
        "label_bg": "#256d4f",
    },
    "vehicle_flow": {
        "stroke": "#f97316",
        "fill": "none",
        "label_bg": "#9a3412",
    },
    "pedestrian_flow": {
        "stroke": "#0f766e",
        "fill": "none",
        "label_bg": "#0f766e",
    },
    "main_entrance": {
        "stroke": "#dc2626",
        "fill": "#dc2626",
        "label_bg": "#991b1b",
    },
    "label": {
        "stroke": "#111827",
        "fill": "#111827",
        "label_bg": "#111827",
    },
}


def render_html(drawing: dict[str, Any], *, title: str | None = None) -> str:
    drawing = normalize_drawing(drawing)
    title_text = title or f"{drawing['project_code']} {drawing['drawing_type']}"
    base_src = _relative_base_src(drawing["base_image"]["path"])
    svg = "\n".join(_render_object(obj) for obj in drawing["objects"])
    legend = "\n".join(_legend_item(obj) for obj in drawing["objects"] if obj.get("label"))
    return f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escape(title_text)}</title>
    <style>
      :root {{
        color-scheme: light;
        font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
        background: #f4f1ea;
        color: #1f2937;
      }}
      body {{
        margin: 0;
        padding: 32px;
      }}
      .sheet {{
        max-width: 1440px;
        margin: 0 auto;
        background: #fffdf8;
        border: 1px solid #d7d0c4;
        box-shadow: 0 18px 48px rgba(47, 43, 35, 0.14);
      }}
      .titlebar {{
        display: flex;
        align-items: end;
        justify-content: space-between;
        gap: 24px;
        padding: 22px 28px 18px;
        border-bottom: 1px solid #dfd7c9;
      }}
      h1 {{
        margin: 0;
        font-size: 22px;
        font-weight: 700;
        letter-spacing: 0;
      }}
      .meta {{
        font-size: 12px;
        color: #6b7280;
      }}
      .canvas {{
        position: relative;
        width: 100%;
        background: #e8e0d2;
        overflow: hidden;
      }}
      .canvas img {{
        display: block;
        width: 100%;
        height: auto;
      }}
      .overlay {{
        position: absolute;
        inset: 0;
        width: 100%;
        height: 100%;
      }}
      .legend {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 8px 16px;
        padding: 14px 28px 22px;
        font-size: 13px;
        color: #374151;
      }}
      .legend span {{
        display: inline-block;
        width: 10px;
        height: 10px;
        margin-right: 8px;
        vertical-align: middle;
      }}
    </style>
  </head>
  <body>
    <main class="sheet">
      <header class="titlebar">
        <h1>{escape(title_text)}</h1>
        <div class="meta">{escape(drawing["drawing_type"])} / {escape(drawing["created_at"])}</div>
      </header>
      <section class="canvas">
        <img src="{escape(base_src)}" alt="base drawing">
        <svg class="overlay" viewBox="0 0 1000 1000" preserveAspectRatio="none" aria-label="semantic overlay">
          <defs>
            <marker id="arrow-orange" markerWidth="14" markerHeight="14" refX="12" refY="5" orient="auto" markerUnits="strokeWidth">
              <path d="M0,0 L12,5 L0,10 Z" fill="#f97316"></path>
            </marker>
            <marker id="arrow-teal" markerWidth="14" markerHeight="14" refX="12" refY="5" orient="auto" markerUnits="strokeWidth">
              <path d="M0,0 L12,5 L0,10 Z" fill="#0f766e"></path>
            </marker>
          </defs>
{svg}
        </svg>
      </section>
      <section class="legend">{legend or '<div>No semantic objects.</div>'}</section>
    </main>
  </body>
</html>
"""


def _relative_base_src(path: str) -> str:
    base = Path(path.replace("\\", "/")).name
    return f"../base/{base}"


def _style(object_type: str) -> dict[str, str]:
    return STYLE.get(object_type, STYLE["label"])


def _points(coords: list[list[float]]) -> str:
    return " ".join(f"{x * 1000:.2f},{y * 1000:.2f}" for x, y in coords)


def _render_object(obj: dict[str, Any]) -> str:
    style = _style(str(obj.get("type")))
    geometry = obj["geometry"]
    kind = geometry["kind"]
    coords = geometry["coords"]
    label = str(obj.get("label") or "")

    if kind == "polygon":
        node = (
            f'          <polygon points="{_points(coords)}" fill="{style["fill"]}" '
            f'stroke="{style["stroke"]}" stroke-width="5"></polygon>'
        )
        return node + _render_label(label, _centroid(coords), style)
    if kind in {"polyline", "arrow"}:
        marker = ""
        if kind == "arrow" or obj.get("type") == "vehicle_flow":
            marker = ' marker-end="url(#arrow-orange)"'
        if obj.get("type") == "pedestrian_flow":
            marker = ' marker-end="url(#arrow-teal)"'
        node = (
            f'          <polyline points="{_points(coords)}" fill="none" '
            f'stroke="{style["stroke"]}" stroke-width="8" stroke-linecap="round" '
            f'stroke-linejoin="round"{marker}></polyline>'
        )
        return node + _render_label(label, _midpoint(coords), style)
    if kind == "point":
        x, y = coords[0]
        node = (
            f'          <circle cx="{x * 1000:.2f}" cy="{y * 1000:.2f}" r="16" '
            f'fill="{style["fill"]}" stroke="#fff" stroke-width="5"></circle>'
        )
        return node + _render_label(label, [x, y], style)
    return _render_label(label, coords[0], style)


def _render_label(label: str, point: list[float], style: dict[str, str]) -> str:
    if not label:
        return ""
    safe = escape(label)
    width = max(72, min(260, len(label) * 15 + 24))
    x = min(max(point[0] * 1000 + 12, 8), 1000 - width - 8)
    y = min(max(point[1] * 1000 - 12, 28), 960)
    return (
        f'\n          <g class="label">'
        f'<rect x="{x:.2f}" y="{y - 24:.2f}" width="{width}" height="30" rx="4" '
        f'fill="{style["label_bg"]}" opacity="0.88"></rect>'
        f'<text x="{x + 10:.2f}" y="{y - 4:.2f}" fill="#fff" font-size="18" '
        f'font-weight="700">{safe}</text></g>'
    )


def _centroid(coords: list[list[float]]) -> list[float]:
    return [
        sum(point[0] for point in coords) / len(coords),
        sum(point[1] for point in coords) / len(coords),
    ]


def _midpoint(coords: list[list[float]]) -> list[float]:
    return coords[len(coords) // 2]


def _legend_item(obj: dict[str, Any]) -> str:
    style = _style(str(obj.get("type")))
    return (
        f'<div><span style="background:{escape(style["stroke"])}"></span>'
        f'{escape(str(obj.get("label") or obj.get("id")))}</div>'
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Render semantic drawing JSON to HTML")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    drawing = json.loads(args.input.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_html(drawing), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

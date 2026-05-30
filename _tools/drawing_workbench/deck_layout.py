#!/usr/bin/env python3
"""Project-level PPT preview layout for drawing workbench slides."""
from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _tools.drawing_workbench.registry import DRAWING_REGISTRY, DRAWING_TYPES


SCHEMA_VERSION = "1.0"
LAYOUT_REL = Path("05_output/ppt/drawing_deck/layout.json")
SLIDE = {"aspect": "16:9", "width": 13.333, "height": 7.5}
TEMPLATE_SIDES = {"drawing_left", "drawing_right"}
DEFAULT_TEMPLATES: dict[str, dict[str, dict[str, float]]] = {
    "drawing_left": {
        "drawing_frame": {"x": 0.02, "y": 0.17, "w": 0.64, "h": 0.72},
        "info_area": {"x": 0.70, "y": 0.17, "w": 0.27, "h": 0.72},
    },
    "drawing_right": {
        "drawing_frame": {"x": 0.34, "y": 0.10, "w": 0.64, "h": 0.84},
        "info_area": {"x": 0.04, "y": 0.18, "w": 0.25, "h": 0.72},
    },
}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def deck_layout_path(project_dir: Path) -> Path:
    return project_dir / LAYOUT_REL


def layout_rel_path() -> str:
    return str(LAYOUT_REL).replace("\\", "/")


def clamp_number(value: object, fallback: float, *, minimum: float = 0.0, maximum: float = 1.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = fallback
    return round(min(maximum, max(minimum, number)), 4)


def normalize_box(raw: object, fallback: dict[str, float]) -> dict[str, float]:
    data = raw if isinstance(raw, dict) else {}
    x = clamp_number(data.get("x"), fallback["x"])
    y = clamp_number(data.get("y"), fallback["y"])
    w = clamp_number(data.get("w"), fallback["w"], minimum=0.02)
    h = clamp_number(data.get("h"), fallback["h"], minimum=0.02)
    if x + w > 1:
        w = round(max(0.02, 1 - x), 4)
    if y + h > 1:
        h = round(max(0.02, 1 - y), 4)
    return {"x": x, "y": y, "w": w, "h": h}


def boxes_intersect(a: dict[str, float], b: dict[str, float]) -> bool:
    return not (a["x"] + a["w"] <= b["x"] or b["x"] + b["w"] <= a["x"] or a["y"] + a["h"] <= b["y"] or b["y"] + b["h"] <= a["y"])


def default_title(drawing_type: str) -> str:
    info = DRAWING_REGISTRY.get(drawing_type) or {}
    return str(info.get("label") or drawing_type)


def default_deck_layout(project_code: str) -> dict[str, Any]:
    side = "drawing_left"
    frame = deepcopy(DEFAULT_TEMPLATES[side]["drawing_frame"])
    return {
        "schema_version": SCHEMA_VERSION,
        "project_code": project_code,
        "updated_at": now_iso(),
        "slide": deepcopy(SLIDE),
        "template_side": side,
        "drawing_frame_version": 1,
        "drawing_frame": frame,
        "slides": {
            drawing_type: default_slide(drawing_type, side, frame_version=1)
            for drawing_type in DRAWING_REGISTRY
        },
    }


def default_slide(drawing_type: str, template_side: str, *, frame_version: int) -> dict[str, Any]:
    return {
        "title": default_title(drawing_type),
        "text": "",
        "layout_generated_from_frame_version": frame_version,
        "needs_reflow": False,
        "manual_overrides": False,
        "elements": default_elements(template_side, supporting_images=[]),
        "layout_warnings": [],
    }


def default_elements(template_side: str, supporting_images: list[dict[str, Any]]) -> dict[str, Any]:
    info = deepcopy(DEFAULT_TEMPLATES.get(template_side, DEFAULT_TEMPLATES["drawing_left"])["info_area"])
    gap = 0.025
    legend_h = round(info["h"] * 0.36, 4)
    text_h = round(info["h"] * 0.24, 4)
    images_y = round(info["y"] + legend_h + text_h + gap * 2, 4)
    images_h = round(max(0.08, info["y"] + info["h"] - images_y), 4)
    return {
        "legend": {"x": info["x"], "y": info["y"], "w": info["w"], "h": legend_h},
        "text": {"x": info["x"], "y": round(info["y"] + legend_h + gap, 4), "w": info["w"], "h": text_h},
        "supporting_images": supporting_image_boxes(supporting_images, {"x": info["x"], "y": images_y, "w": info["w"], "h": images_h}),
    }


def supporting_image_boxes(images: list[dict[str, Any]], area: dict[str, float]) -> list[dict[str, Any]]:
    if not images:
        return []
    count = min(len(images), 6)
    cols = 1 if count == 1 else 2
    rows = (count + cols - 1) // cols
    gap = 0.012
    cell_w = (area["w"] - gap * (cols - 1)) / cols
    cell_h = (area["h"] - gap * (rows - 1)) / rows
    boxes = []
    for index, image in enumerate(images[:count]):
        col = index % cols
        row = index // cols
        boxes.append(
            {
                "id": str(image.get("id") or f"img-{index + 1}"),
                "x": round(area["x"] + col * (cell_w + gap), 4),
                "y": round(area["y"] + row * (cell_h + gap), 4),
                "w": round(max(0.02, cell_w), 4),
                "h": round(max(0.02, cell_h), 4),
            }
        )
    return boxes


def read_supporting_images(project_dir: Path, drawing_type: str) -> list[dict[str, Any]]:
    manifest_path = project_dir / "05_output" / "drawings" / "supporting" / drawing_type / "manifest.json"
    if not manifest_path.exists():
        return []
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    images = manifest.get("images")
    return images if isinstance(images, list) else []


def normalize_slide(raw: object, drawing_type: str, template_side: str, frame_version: int) -> dict[str, Any]:
    fallback = default_slide(drawing_type, template_side, frame_version=frame_version)
    data = raw if isinstance(raw, dict) else {}
    slide = {
        "title": str(data.get("title") or fallback["title"]),
        "text": str(data.get("text") or ""),
        "layout_generated_from_frame_version": int(data.get("layout_generated_from_frame_version") or fallback["layout_generated_from_frame_version"]),
        "needs_reflow": bool(data.get("needs_reflow", fallback["needs_reflow"])),
        "manual_overrides": bool(data.get("manual_overrides", fallback["manual_overrides"])),
        "elements": normalize_elements(data.get("elements"), fallback["elements"]),
        "layout_warnings": data.get("layout_warnings") if isinstance(data.get("layout_warnings"), list) else [],
    }
    if slide["layout_generated_from_frame_version"] != frame_version:
        slide["needs_reflow"] = True
    return slide


def normalize_elements(raw: object, fallback: dict[str, Any]) -> dict[str, Any]:
    data = raw if isinstance(raw, dict) else {}
    supporting_raw = data.get("supporting_images") if isinstance(data.get("supporting_images"), list) else []
    supporting_fallback = fallback.get("supporting_images") if isinstance(fallback.get("supporting_images"), list) else []
    supporting = []
    for index, item in enumerate(supporting_raw):
        item_data = item if isinstance(item, dict) else {}
        fb = supporting_fallback[index] if index < len(supporting_fallback) else {"id": f"img-{index + 1}", "x": 0.72, "y": 0.72, "w": 0.12, "h": 0.12}
        box = normalize_box(item_data, fb)
        box["id"] = str(item_data.get("id") or fb.get("id") or f"img-{index + 1}")
        supporting.append(box)
    return {
        "legend": normalize_box(data.get("legend"), fallback["legend"]),
        "text": normalize_box(data.get("text"), fallback["text"]),
        "supporting_images": supporting,
    }


def normalize_deck_layout(raw: object, project_code: str) -> dict[str, Any]:
    data = raw if isinstance(raw, dict) else {}
    side = str(data.get("template_side") or "drawing_left")
    if side not in TEMPLATE_SIDES:
        side = "drawing_left"
    frame_version = int(data.get("drawing_frame_version") or 1)
    frame = normalize_box(
        data.get("drawing_frame"),
        DEFAULT_TEMPLATES[side]["drawing_frame"],
        )
    slides_raw = data.get("slides") if isinstance(data.get("slides"), dict) else {}
    slides = {
        drawing_type: normalize_slide(slides_raw.get(drawing_type), drawing_type, side, frame_version)
        for drawing_type in DRAWING_REGISTRY
    }
    layout = {
        "schema_version": SCHEMA_VERSION,
        "project_code": project_code,
        "updated_at": str(data.get("updated_at") or now_iso()),
        "slide": deepcopy(SLIDE),
        "template_side": side,
        "drawing_frame_version": frame_version,
        "drawing_frame": frame,
        "slides": slides,
    }
    return layout


def load_deck_layout(project_dir: Path, project_code: str) -> dict[str, Any]:
    path = deck_layout_path(project_dir)
    if not path.exists():
        return default_deck_layout(project_code)
    return normalize_deck_layout(json.loads(path.read_text(encoding="utf-8")), project_code)


def save_deck_layout(project_dir: Path, layout: dict[str, Any], project_code: str) -> dict[str, Any]:
    normalized = normalize_deck_layout(layout, project_code)
    normalized["updated_at"] = now_iso()
    path = deck_layout_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return normalized


def set_template_side(layout: dict[str, Any], template_side: str) -> dict[str, Any]:
    if template_side not in TEMPLATE_SIDES:
        raise ValueError(f"template_side must be one of {sorted(TEMPLATE_SIDES)}")
    if layout.get("template_side") == template_side:
        return layout
    layout = deepcopy(layout)
    layout["template_side"] = template_side
    layout["drawing_frame"] = deepcopy(DEFAULT_TEMPLATES[template_side]["drawing_frame"])
    bump_frame_version(layout)
    return layout


def set_drawing_frame(layout: dict[str, Any], drawing_frame: dict[str, Any]) -> dict[str, Any]:
    layout = deepcopy(layout)
    side = layout.get("template_side") if layout.get("template_side") in TEMPLATE_SIDES else "drawing_left"
    next_frame = normalize_box(drawing_frame, DEFAULT_TEMPLATES[side]["drawing_frame"])
    if next_frame != layout.get("drawing_frame"):
        layout["drawing_frame"] = next_frame
        bump_frame_version(layout)
    return layout


def bump_frame_version(layout: dict[str, Any]) -> None:
    layout["drawing_frame_version"] = int(layout.get("drawing_frame_version") or 1) + 1
    for slide in (layout.get("slides") or {}).values():
        if isinstance(slide, dict):
            slide["needs_reflow"] = True


def reflow_deck(project_dir: Path, layout: dict[str, Any], *, drawing_type: str | None = None) -> dict[str, Any]:
    layout = deepcopy(layout)
    frame = layout.get("drawing_frame") or DEFAULT_TEMPLATES["drawing_left"]["drawing_frame"]
    side = layout.get("template_side") if layout.get("template_side") in TEMPLATE_SIDES else "drawing_left"
    frame_version = int(layout.get("drawing_frame_version") or 1)
    targets = [drawing_type] if drawing_type else list(DRAWING_REGISTRY)
    for target in targets:
        if target not in DRAWING_TYPES:
            raise ValueError(f"drawing_type must be one of {sorted(DRAWING_TYPES)}")
        slide = layout["slides"].get(target) or default_slide(target, side, frame_version=frame_version)
        supporting = read_supporting_images(project_dir, target)
        elements = default_elements(side, supporting)
        warnings = []
        for key in ("legend", "text"):
            if boxes_intersect(elements[key], frame):
                warnings.append(f"{key} overlaps drawing_frame")
        for item in elements.get("supporting_images", []):
            if boxes_intersect(item, frame):
                warnings.append(f"supporting image {item.get('id')} overlaps drawing_frame")
        slide["elements"] = elements
        slide["layout_generated_from_frame_version"] = frame_version
        slide["needs_reflow"] = False
        slide["manual_overrides"] = False
        slide["layout_warnings"] = warnings
        layout["slides"][target] = slide
    return layout

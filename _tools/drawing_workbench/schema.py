#!/usr/bin/env python3
"""Validation helpers for semantic drawing JSON — schema v1.2."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any

from _tools.drawing_workbench.registry import (
    DRAWING_ALIASES,
    DRAWING_REGISTRY,
    DRAWING_TYPES,
    OBJECT_TYPE_ALIASES,
    OBJECT_TYPE_REGISTRY,
    OBJECT_TYPES,
    default_object_style,
    normalize_drawing_type,
    normalize_object_type,
)

SCHEMA_VERSION = "1.2"
ACCEPTED_SCHEMA_VERSIONS = {"1.0", "1.1", "1.2"}
BASE_SOURCES = {"user_upload", "cad_export", "sat_export", "render"}
GEOMETRY_KINDS = {"path", "circle", "triangle", "point", "text"}
SEGMENT_KINDS = {"line", "quadratic"}
CONFIDENCE_LEVELS = {"low", "medium", "high"}
OBJECT_SOURCES = {"user_sketch", "agent_visual_draft", "vision_inferred", "cad_extracted"}
QUADRATIC_SAMPLE_STEPS = 16

# Legacy geometry kinds accepted on read
_LEGACY_GEOMETRY_KINDS = {"polygon", "polyline", "arrow", "point"}

# Style validation ranges
FILL_MODES = {"none", "translucent", "solid", "hatch"}
STROKE_STYLES = {"solid", "dashed"}
BORDER_STYLES = {"none", "solid", "dashed", "double"}


class DrawingValidationError(ValueError):
    """Raised when a semantic drawing payload violates the locked schema."""


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def drawing_output_paths(drawing_type: str) -> dict[str, str]:
    drawing_type = _clean_drawing_type(drawing_type)
    return {
        "semantic": f"05_output/drawings/semantic/{drawing_type}.json",
        "svg": f"05_output/drawings/svg/{drawing_type}.svg",
        "png": f"05_output/drawings/png/{drawing_type}.png",
        "pdf": f"05_output/drawings/pdf/{drawing_type}.pdf",
    }


def empty_drawing(
    *,
    project_code: str,
    drawing_type: str,
    base_path: str = "05_output/drawings/base/master_plan.jpg",
    natural_width: int = 1,
    natural_height: int = 1,
    base_source: str = "render",
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "drawing_type": _clean_drawing_type(drawing_type),
        "project_code": str(project_code).strip(),
        "base_image": {
            "path": _clean_base_path(base_path),
            "natural_width": int(natural_width),
            "natural_height": int(natural_height),
            "source": _clean_choice(base_source, BASE_SOURCES, "base_image.source"),
        },
        "created_at": now_iso(),
        "last_edited_by": "agent",
        "objects": [],
    }


def normalize_drawing(data: dict[str, Any], *, project_code: str | None = None) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise DrawingValidationError("drawing payload must be an object")
    payload = deepcopy(data)

    schema_version = str(payload.get("schema_version") or "").strip()
    if schema_version not in ACCEPTED_SCHEMA_VERSIONS:
        raise DrawingValidationError(f"schema_version must be one of {sorted(ACCEPTED_SCHEMA_VERSIONS)}")

    drawing_type = _clean_drawing_type(payload.get("drawing_type"))
    actual_project = str(payload.get("project_code") or project_code or "").strip()
    if not actual_project:
        raise DrawingValidationError("project_code is required")
    if project_code and actual_project != project_code:
        raise DrawingValidationError("project_code does not match request project")

    base_image = _normalize_base_image(payload.get("base_image"))
    created_at = str(payload.get("created_at") or now_iso()).strip()
    last_edited_by = _clean_choice(
        payload.get("last_edited_by") or "agent",
        {"user", "agent", "vision_model"},
        "last_edited_by",
    )
    objects = _normalize_objects(payload.get("objects"), drawing_type=drawing_type)

    return {
        "schema_version": SCHEMA_VERSION,
        "drawing_type": drawing_type,
        "project_code": actual_project,
        "base_image": base_image,
        "created_at": created_at,
        "last_edited_by": last_edited_by,
        "objects": objects,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _clean_drawing_type(value: object) -> str:
    text = str(value or "").strip()
    if text in DRAWING_REGISTRY:
        return text
    alias = DRAWING_ALIASES.get(text)
    if alias and alias in DRAWING_REGISTRY:
        return alias
    raise DrawingValidationError(f"drawing_type must be one of {sorted(DRAWING_TYPES)}")


def _clean_choice(value: object, allowed: set[str], field: str) -> str:
    text = str(value or "").strip()
    if text not in allowed:
        raise DrawingValidationError(f"{field} must be one of {sorted(allowed)}")
    return text


def _clean_base_path(value: object) -> str:
    text = str(value or "").replace("\\", "/").strip().lstrip("/")
    if not text:
        raise DrawingValidationError("base_image.path is required")
    path = PurePosixPath(text)
    if ".." in path.parts or path.is_absolute():
        raise DrawingValidationError("base_image.path must be a safe relative path")
    if not text.startswith("05_output/drawings/base/"):
        raise DrawingValidationError("base_image.path must be under 05_output/drawings/base/")
    return text


def _normalize_base_image(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DrawingValidationError("base_image must be an object")
    width = _positive_int(value.get("natural_width"), "base_image.natural_width")
    height = _positive_int(value.get("natural_height"), "base_image.natural_height")
    return {
        "path": _clean_base_path(value.get("path")),
        "natural_width": width,
        "natural_height": height,
        "source": _clean_choice(value.get("source"), BASE_SOURCES, "base_image.source"),
    }


def _positive_int(value: object, field: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise DrawingValidationError(f"{field} must be a positive integer") from exc
    if number <= 0:
        raise DrawingValidationError(f"{field} must be a positive integer")
    return number


def _normalize_objects(value: object, *, drawing_type: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise DrawingValidationError("objects must be an array")
    result: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, raw in enumerate(value, start=1):
        if not isinstance(raw, dict):
            raise DrawingValidationError(f"objects[{index}] must be an object")
        object_id = str(raw.get("id") or f"obj-{index:03d}").strip()
        if not object_id:
            raise DrawingValidationError(f"objects[{index}].id is required")
        if object_id in seen_ids:
            raise DrawingValidationError(f"duplicate object id: {object_id}")
        seen_ids.add(object_id)

        raw_type = str(raw.get("type") or "").strip()
        # Resolve alias
        resolved_type = OBJECT_TYPE_ALIASES.get(raw_type, raw_type)

        # Migrate old main_entrance point -> entrance_marker triangle
        geometry_raw = raw.get("geometry") or {}
        raw_kind = str(geometry_raw.get("kind") or "").strip()
        migrated_type = resolved_type
        migrated_geometry = geometry_raw
        if raw_kind == "point" and raw_type == "main_entrance":
            migrated_type = "entrance_marker"
            migrated_geometry = {
                "kind": "triangle",
                "center": geometry_raw.get("coords", [[0.5, 0.5]])[0] if geometry_raw.get("coords") else [0.5, 0.5],
                "size": 0.055,
                "rotation_deg": 0,
            }

        # Validate object type
        if migrated_type not in OBJECT_TYPE_REGISTRY:
            # Legacy: accept label and other old types if they use point geometry
            if raw_kind == "point":
                migrated_type = raw_type if raw_type else "label"
            else:
                raise DrawingValidationError(f"objects[{index}].type must be one of {sorted(OBJECT_TYPES)}")

        object_type = migrated_type
        geometry = _normalize_geometry(migrated_geometry, index, object_type=object_type)
        style_hints = _normalize_style_hints(
            raw.get("style_hints"),
            drawing_type=drawing_type,
            object_type=object_type,
            object_index=index,
        )
        result.append(
            {
                "id": object_id,
                "type": object_type,
                "geometry": geometry,
                "label": str(raw.get("label") or "").strip(),
                "confidence": _clean_choice(
                    raw.get("confidence") or "medium",
                    CONFIDENCE_LEVELS,
                    f"objects[{index}].confidence",
                ),
                "source": _clean_choice(
                    raw.get("source") or "user_sketch",
                    OBJECT_SOURCES,
                    f"objects[{index}].source",
                ),
                "style_hints": style_hints,
            }
        )
    return result


def _normalize_style_hints(
    value: object,
    *,
    drawing_type: str,
    object_type: str,
    object_index: int,
) -> dict[str, Any]:
    if value is None:
        raw: dict[str, Any] = {}
    elif isinstance(value, dict):
        raw = value
    else:
        raise DrawingValidationError(f"objects[{object_index}].style_hints must be an object")

    defaults = default_object_style(object_type)

    # Migrate legacy fill_enabled -> fill_mode
    if "fill_enabled" in raw and "fill_mode" not in raw:
        raw["fill_mode"] = "translucent" if raw["fill_enabled"] else "none"
        del raw["fill_enabled"]

    result = _merge_style(defaults, raw, object_index)

    # Validate hex colors
    for color_key in ("fill_color", "stroke_color"):
        val = result.get(color_key, "")
        if val and not _is_hex_color(val):
            raise DrawingValidationError(
                f"objects[{object_index}].style_hints.{color_key} must be #RRGGBB"
            )
        if val:
            result[color_key] = val.upper()

    return result


def _merge_style(defaults: dict[str, Any], raw: dict[str, Any], object_index: int) -> dict[str, Any]:
    result = deepcopy(defaults)
    for key, value in raw.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = {**deepcopy(result[key]), **deepcopy(value)}
        else:
            result[key] = deepcopy(value)
    return result


def _is_hex_color(value: str) -> bool:
    if len(value) != 7 or not value.startswith("#"):
        return False
    return all(char in "0123456789abcdefABCDEF" for char in value[1:])


# ---------------------------------------------------------------------------
# Geometry normalization
# ---------------------------------------------------------------------------

def _normalize_geometry(value: object, object_index: int, *, object_type: str = "") -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DrawingValidationError(f"objects[{object_index}].geometry must be an object")

    raw_kind = str(value.get("kind") or "").strip()

    # Migrate legacy kinds
    if raw_kind == "polygon":
        return _normalize_path_geometry(value, object_index, closed=True, object_type=object_type)
    elif raw_kind == "polyline" or raw_kind == "arrow":
        return _normalize_path_geometry(value, object_index, closed=False, object_type=object_type)
    elif raw_kind == "point":
        return _normalize_point_geometry(value, object_index)
    elif raw_kind == "path":
        closed = bool(value.get("closed", False))
        return _normalize_path_geometry(value, object_index, closed=closed, object_type=object_type)
    elif raw_kind == "circle":
        return _normalize_circle_geometry(value, object_index)
    elif raw_kind == "triangle":
        return _normalize_triangle_geometry(value, object_index)
    elif raw_kind == "text":
        return _normalize_text_geometry(value, object_index)
    else:
        raise DrawingValidationError(
            f"objects[{object_index}].geometry.kind must be one of {sorted(GEOMETRY_KINDS | _LEGACY_GEOMETRY_KINDS)}"
        )


def _normalize_path_geometry(value: dict, object_index: int, *, closed: bool, object_type: str) -> dict[str, Any]:
    coords = value.get("coords")
    if not isinstance(coords, list):
        raise DrawingValidationError(f"objects[{object_index}].geometry.coords must be an array")
    clean_coords = [_normalize_coord(coord, object_index) for coord in coords]
    minimum = 3 if closed else 2
    if len(clean_coords) < minimum:
        raise DrawingValidationError(
            f"objects[{object_index}].geometry.coords needs at least {minimum} points for {'closed' if closed else 'open'} path"
        )

    result: dict[str, Any] = {"kind": "path", "closed": closed, "coords": clean_coords}

    raw_segments = value.get("segments")
    if raw_segments is not None:
        segments = _normalize_segments(raw_segments, object_index, closed=closed)
        result["segments"] = segments
        result["coords"] = _sample_segments(segments, closed=closed)

    return result


def _normalize_circle_geometry(value: dict, object_index: int) -> dict[str, Any]:
    center = value.get("center")
    if not isinstance(center, (list, tuple)) or len(center) != 2:
        raise DrawingValidationError(f"objects[{object_index}].geometry.center must be [x, y]")
    try:
        cx = float(center[0])
        cy = float(center[1])
    except (TypeError, ValueError) as exc:
        raise DrawingValidationError(f"objects[{object_index}].geometry.center must be numeric") from exc
    if not (0 <= cx <= 1 and 0 <= cy <= 1):
        raise DrawingValidationError(f"objects[{object_index}].geometry.center must be normalized 0-1")

    radius = value.get("radius")
    if radius is None:
        raise DrawingValidationError(f"objects[{object_index}].geometry.radius is required")
    try:
        r = float(radius)
    except (TypeError, ValueError) as exc:
        raise DrawingValidationError(f"objects[{object_index}].geometry.radius must be numeric") from exc
    if not (0.006 <= r <= 0.25):
        raise DrawingValidationError(f"objects[{object_index}].geometry.radius must be between 0.006 and 0.25")

    return {
        "kind": "circle",
        "center": [round(cx, 6), round(cy, 6)],
        "radius": round(r, 6),
    }


def _normalize_triangle_geometry(value: dict, object_index: int) -> dict[str, Any]:
    center = value.get("center")
    if not isinstance(center, (list, tuple)) or len(center) != 2:
        raise DrawingValidationError(f"objects[{object_index}].geometry.center must be [x, y]")
    try:
        cx = float(center[0])
        cy = float(center[1])
    except (TypeError, ValueError) as exc:
        raise DrawingValidationError(f"objects[{object_index}].geometry.center must be numeric") from exc
    if not (0 <= cx <= 1 and 0 <= cy <= 1):
        raise DrawingValidationError(f"objects[{object_index}].geometry.center must be normalized 0-1")

    size = value.get("size")
    if size is None:
        raise DrawingValidationError(f"objects[{object_index}].geometry.size is required")
    try:
        s = float(size)
    except (TypeError, ValueError) as exc:
        raise DrawingValidationError(f"objects[{object_index}].geometry.size must be numeric") from exc
    if not (0.01 <= s <= 0.3):
        raise DrawingValidationError(f"objects[{object_index}].geometry.size must be between 0.01 and 0.3")

    rotation = float(value.get("rotation_deg", 0))
    rotation = rotation % 360

    return {
        "kind": "triangle",
        "center": [round(cx, 6), round(cy, 6)],
        "size": round(s, 6),
        "rotation_deg": round(rotation, 2),
    }


def _normalize_point_geometry(value: dict, object_index: int) -> dict[str, Any]:
    coords = value.get("coords")
    if not isinstance(coords, list) or len(coords) < 1:
        raise DrawingValidationError(f"objects[{object_index}].geometry.coords must have at least 1 point")
    clean_coords = [_normalize_coord(coord, object_index) for coord in coords]
    return {"kind": "point", "coords": clean_coords[:1]}


def _normalize_text_geometry(value: dict, object_index: int) -> dict[str, Any]:
    coords = value.get("coords")
    if not isinstance(coords, list) or len(coords) < 1:
        raise DrawingValidationError(f"objects[{object_index}].geometry.coords must have at least 1 point")
    clean_coords = [_normalize_coord(coord, object_index) for coord in coords]
    return {"kind": "text", "coords": clean_coords[:1]}


def _normalize_coord(value: object, object_index: int) -> list[float]:
    if not isinstance(value, list | tuple) or len(value) != 2:
        raise DrawingValidationError(f"objects[{object_index}].geometry.coords entries must be [x, y]")
    try:
        x = float(value[0])
        y = float(value[1])
    except (TypeError, ValueError) as exc:
        raise DrawingValidationError(f"objects[{object_index}].geometry.coords must be numeric") from exc
    if not (0 <= x <= 1 and 0 <= y <= 1):
        raise DrawingValidationError(
            f"objects[{object_index}].geometry.coords must be normalized between 0 and 1"
        )
    return [round(x, 6), round(y, 6)]


def _normalize_segments(value: object, object_index: int, *, closed: bool) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) == 0:
        raise DrawingValidationError(f"objects[{object_index}].geometry.segments must be a non-empty array")
    segments: list[dict[str, Any]] = []
    for seg_index, raw in enumerate(value):
        if not isinstance(raw, dict):
            raise DrawingValidationError(
                f"objects[{object_index}].geometry.segments[{seg_index}] must be an object"
            )
        kind = _clean_choice(
            raw.get("kind"),
            SEGMENT_KINDS,
            f"objects[{object_index}].geometry.segments[{seg_index}].kind",
        )
        from_pt = _normalize_coord(raw.get("from"), object_index)
        to_pt = _normalize_coord(raw.get("to"), object_index)
        segment: dict[str, Any] = {"kind": kind, "from": from_pt, "to": to_pt}
        if kind == "quadratic":
            control = _normalize_coord(raw.get("control"), object_index)
            segment["control"] = control
        segments.append(segment)

    # Chain continuity
    for i in range(len(segments) - 1):
        if segments[i]["to"] != segments[i + 1]["from"]:
            raise DrawingValidationError(
                f"objects[{object_index}].geometry.segments: discontinuous chain at segment {i} -> {i + 1}"
            )
    # Closure check for closed paths
    if closed:
        if segments[-1]["to"] != segments[0]["from"]:
            raise DrawingValidationError(
                f"objects[{object_index}].geometry.segments: ring not closed (last.to != first.from)"
            )

    return segments


def _sample_segments(segments: list[dict[str, Any]], *, closed: bool) -> list[list[float]]:
    if not segments:
        return []
    coords: list[list[float]] = [segments[0]["from"]]
    for segment in segments:
        if segment["kind"] == "line":
            coords.append(segment["to"])
        elif segment["kind"] == "quadratic":
            from_pt = segment["from"]
            control = segment["control"]
            to_pt = segment["to"]
            for i in range(1, QUADRATIC_SAMPLE_STEPS + 1):
                t = i / QUADRATIC_SAMPLE_STEPS
                mt = 1 - t
                x = mt * mt * from_pt[0] + 2 * mt * t * control[0] + t * t * to_pt[0]
                y = mt * mt * from_pt[1] + 2 * mt * t * control[1] + t * t * to_pt[1]
                coords.append([round(x, 6), round(y, 6)])
    # For open paths, remove trailing point if it matches first
    if not closed and len(coords) > 2:
        first = coords[0]
        last = coords[-1]
        if abs(first[0] - last[0]) < 1e-5 and abs(first[1] - last[1]) < 1e-5:
            coords.pop()
    return coords

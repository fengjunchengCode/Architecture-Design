#!/usr/bin/env python3
"""Validation helpers for semantic drawing JSON."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any


SCHEMA_VERSION = "1.0"
DRAWING_TYPES = {"functional_zoning", "traffic_analysis"}
BASE_SOURCES = {"user_upload", "cad_export", "sat_export", "render"}
OBJECT_TYPES = {
    "main_entrance",
    "pedestrian_flow",
    "vehicle_flow",
    "functional_zone",
    "label",
}
GEOMETRY_KINDS = {"point", "polyline", "polygon", "arrow"}
CONFIDENCE_LEVELS = {"low", "medium", "high"}
OBJECT_SOURCES = {"user_sketch", "vision_inferred", "cad_extracted"}
ZONE_BORDER_STYLES = {"solid", "dashed", "none"}
ZONE_STROKE_WIDTH_KEYS = {"thin", "medium", "bold"}
ZONE_STROKE_WIDTH_BY_KEY = {"thin": 0.002, "medium": 0.003, "bold": 0.0045}
DEFAULT_ZONE_STYLE_HINTS = {
    "fill_color": "#DCE8C8",
    "fill_enabled": True,
    "border_style": "solid",
    "stroke_width": 0.003,
}


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
    if schema_version != SCHEMA_VERSION:
        raise DrawingValidationError(f"schema_version must be {SCHEMA_VERSION}")

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


def _clean_drawing_type(value: object) -> str:
    drawing_type = str(value or "").strip()
    if drawing_type not in DRAWING_TYPES:
        raise DrawingValidationError(f"drawing_type must be one of {sorted(DRAWING_TYPES)}")
    return drawing_type


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
        object_type = _clean_choice(raw.get("type"), OBJECT_TYPES, f"objects[{index}].type")
        geometry = _normalize_geometry(raw.get("geometry"), index)
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
    if drawing_type != "functional_zoning" or object_type != "functional_zone":
        return {}
    if value is None:
        raw: dict[str, Any] = {}
    elif isinstance(value, dict):
        raw = value
    else:
        raise DrawingValidationError(f"objects[{object_index}].style_hints must be an object")

    fill_color = str(raw.get("fill_color") or DEFAULT_ZONE_STYLE_HINTS["fill_color"]).strip()
    if not _is_hex_color(fill_color):
        raise DrawingValidationError(f"objects[{object_index}].style_hints.fill_color must be #RRGGBB")
    fill_enabled = raw.get("fill_enabled", DEFAULT_ZONE_STYLE_HINTS["fill_enabled"])
    if not isinstance(fill_enabled, bool):
        raise DrawingValidationError(f"objects[{object_index}].style_hints.fill_enabled must be boolean")
    border_style = _clean_choice(
        raw.get("border_style") or DEFAULT_ZONE_STYLE_HINTS["border_style"],
        ZONE_BORDER_STYLES,
        f"objects[{object_index}].style_hints.border_style",
    )
    stroke_width = _normalize_zone_stroke_width(raw, object_index)
    return {
        "fill_color": fill_color.upper(),
        "fill_enabled": fill_enabled,
        "border_style": border_style,
        "stroke_width": stroke_width,
    }


def _normalize_zone_stroke_width(raw: dict[str, Any], object_index: int) -> float:
    if raw.get("stroke_width") is not None:
        try:
            width = float(raw.get("stroke_width"))
        except (TypeError, ValueError) as exc:
            raise DrawingValidationError(
                f"objects[{object_index}].style_hints.stroke_width must be numeric"
            ) from exc
    elif raw.get("stroke_width_key") is not None:
        key = _clean_choice(
            raw.get("stroke_width_key"),
            ZONE_STROKE_WIDTH_KEYS,
            f"objects[{object_index}].style_hints.stroke_width_key",
        )
        width = ZONE_STROKE_WIDTH_BY_KEY[key]
    else:
        width = float(DEFAULT_ZONE_STYLE_HINTS["stroke_width"])
    if not 0.001 <= width <= 0.012:
        raise DrawingValidationError(f"objects[{object_index}].style_hints.stroke_width out of range")
    return round(width, 4)


def _is_hex_color(value: str) -> bool:
    if len(value) != 7 or not value.startswith("#"):
        return False
    return all(char in "0123456789abcdefABCDEF" for char in value[1:])


def _normalize_geometry(value: object, object_index: int) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DrawingValidationError(f"objects[{object_index}].geometry must be an object")
    kind = _clean_choice(value.get("kind"), GEOMETRY_KINDS, f"objects[{object_index}].geometry.kind")
    coords = value.get("coords")
    if not isinstance(coords, list):
        raise DrawingValidationError(f"objects[{object_index}].geometry.coords must be an array")
    clean_coords = [_normalize_coord(coord, object_index) for coord in coords]
    minimum = {"point": 1, "polyline": 2, "polygon": 3, "arrow": 2}[kind]
    if len(clean_coords) < minimum:
        raise DrawingValidationError(
            f"objects[{object_index}].geometry.coords needs at least {minimum} points for {kind}"
        )
    if kind == "point" and len(clean_coords) != 1:
        raise DrawingValidationError(f"objects[{object_index}].geometry point must have exactly 1 coord")
    return {"kind": kind, "coords": clean_coords}


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

#!/usr/bin/env python3
"""Validation helpers for project-level drawing style specs."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any


SCHEMA_VERSION = "1.0"
STYLE_FIELDS = {
    "palette",
    "typography",
    "strokes",
    "arrows",
    "labels",
    "legend",
    "scale_north",
}


class StyleSpecValidationError(ValueError):
    """Raised when a style_spec payload is malformed."""


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def validate_style_spec(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise StyleSpecValidationError("style_spec must be an object")
    payload = deepcopy(data)
    schema_version = str(payload.get("schema_version") or SCHEMA_VERSION).strip()
    if schema_version != SCHEMA_VERSION:
        raise StyleSpecValidationError(f"schema_version must be {SCHEMA_VERSION}")

    result: dict[str, Any] = {"schema_version": SCHEMA_VERSION}
    for field in sorted(STYLE_FIELDS):
        result[field] = _clean_object(payload.get(field), field)

    based_on = payload.get("based_on", [])
    if based_on is None:
        based_on = []
    if not isinstance(based_on, list):
        raise StyleSpecValidationError("based_on must be an array")
    result["based_on"] = [str(item).strip() for item in based_on if str(item).strip()]

    approved_at = payload.get("approved_at")
    result["approved_at"] = str(approved_at).strip() if approved_at else None
    result["updated_at"] = str(payload.get("updated_at") or now_iso()).strip()
    notes = str(payload.get("notes") or "").strip()
    if notes:
        result["notes"] = notes
    return result


def _clean_object(value: object, field: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise StyleSpecValidationError(f"{field} must be an object")
    clean: dict[str, Any] = {}
    for key, raw_value in value.items():
        clean_key = str(key).strip()
        if not clean_key:
            continue
        clean[clean_key] = _clean_value(raw_value, f"{field}.{clean_key}")
    return clean


def _clean_value(value: object, field: str) -> object:
    if isinstance(value, dict):
        return _clean_object(value, field)
    if isinstance(value, list):
        return [_clean_value(item, field) for item in value]
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        return value
    return str(value).strip()

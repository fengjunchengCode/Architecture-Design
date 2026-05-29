#!/usr/bin/env python3
"""Unit tests for drawing workbench schema v1.2."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from _tools.drawing_workbench.registry import (
    DRAWING_TYPES,
    OBJECT_TYPES,
    OBJECT_TYPE_ALIASES,
    default_object_style,
)
from _tools.drawing_workbench.schema import (
    ACCEPTED_SCHEMA_VERSIONS,
    SCHEMA_VERSION,
    DrawingValidationError,
    normalize_drawing,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
REAL_FZ_PATH = REPO_ROOT / "projects" / "26-BQ-PARK" / "05_output" / "drawings" / "semantic" / "functional_zoning.json"


def _make_drawing(objects=None, schema_version="1.2", drawing_type="functional_zoning"):
    return {
        "schema_version": schema_version,
        "drawing_type": drawing_type,
        "project_code": "99-ZZ-TEST",
        "base_image": {
            "path": "05_output/drawings/base/master_plan.jpg",
            "natural_width": 100,
            "natural_height": 100,
            "source": "user_upload",
        },
        "created_at": "2026-01-01T00:00:00+00:00",
        "last_edited_by": "agent",
        "objects": objects or [],
    }


def _closed_path(coords=None, segments=None):
    geo = {
        "kind": "path",
        "closed": True,
        "coords": coords or [[0.1, 0.1], [0.3, 0.1], [0.3, 0.3]],
    }
    if segments is not None:
        geo["segments"] = segments
    return geo


def _open_path(coords=None, segments=None):
    geo = {
        "kind": "path",
        "closed": False,
        "coords": coords or [[0.1, 0.1], [0.3, 0.3]],
    }
    if segments is not None:
        geo["segments"] = segments
    return geo


def _circle(center=None, radius=0.035):
    return {"kind": "circle", "center": center or [0.5, 0.5], "radius": radius}


def _triangle(center=None, size=0.055, rotation_deg=0):
    return {
        "kind": "triangle",
        "center": center or [0.5, 0.5],
        "size": size,
        "rotation_deg": rotation_deg,
    }


def _point(coord=None):
    return {"kind": "point", "coords": [coord or [0.5, 0.5]]}


class TestSchemaVersion(unittest.TestCase):
    def test_schema_version_is_12(self):
        self.assertEqual(SCHEMA_VERSION, "1.2")

    def test_accepted_versions_include_all(self):
        self.assertIn("1.0", ACCEPTED_SCHEMA_VERSIONS)
        self.assertIn("1.1", ACCEPTED_SCHEMA_VERSIONS)
        self.assertIn("1.2", ACCEPTED_SCHEMA_VERSIONS)


class TestRegistry(unittest.TestCase):
    def test_drawing_types_count(self):
        self.assertEqual(len(DRAWING_TYPES), 10)

    def test_all_expected_drawing_types(self):
        expected = {
            "functional_zoning", "planting_design", "landscape_analysis",
            "traffic_analysis", "fire_route", "vertical_analysis",
            "supporting_facilities", "sponge_city", "accessibility_design",
            "civil_defense",
        }
        self.assertEqual(DRAWING_TYPES, expected)

    def test_object_types_include_all(self):
        expected = {
            "functional_zone", "planting_zone", "key_planting_zone",
            "planting_edge_line", "landscape_axis_primary", "landscape_axis_secondary",
            "landscape_node", "vehicle_flow", "pedestrian_flow", "underground_flow",
            "entrance_marker", "fire_route_line", "turning_radius",
            "elevation_marker", "slope_arrow", "facility_zone",
            "trash_collection_point", "sponge_zone", "ecological_ditch_line",
            "runoff_line", "accessible_facility_zone", "accessible_point",
            "civil_defense_zone",
        }
        self.assertTrue(expected.issubset(OBJECT_TYPES))

    def test_aliases(self):
        self.assertEqual(OBJECT_TYPE_ALIASES.get("main_entrance"), "entrance_marker")


class TestClosedPathGeometry(unittest.TestCase):
    def test_closed_path_3_coords_ok(self):
        d = _make_drawing([{"id": "o1", "type": "functional_zone", "geometry": _closed_path()}])
        result = normalize_drawing(d, project_code="99-ZZ-TEST")
        self.assertEqual(result["objects"][0]["geometry"]["kind"], "path")
        self.assertTrue(result["objects"][0]["geometry"]["closed"])

    def test_closed_path_2_coords_rejects(self):
        d = _make_drawing([{"id": "o1", "type": "functional_zone", "geometry": _closed_path([[0.1, 0.1], [0.3, 0.3]])}])
        with self.assertRaises(DrawingValidationError):
            normalize_drawing(d, project_code="99-ZZ-TEST")

    def test_closed_path_with_quadratic_segments(self):
        segs = [
            {"kind": "line", "from": [0.1, 0.1], "to": [0.3, 0.1]},
            {"kind": "quadratic", "from": [0.3, 0.1], "control": [0.36, 0.2], "to": [0.3, 0.3]},
            {"kind": "line", "from": [0.3, 0.3], "to": [0.1, 0.1]},
        ]
        d = _make_drawing([{"id": "o1", "type": "functional_zone", "geometry": _closed_path(segments=segs)}])
        result = normalize_drawing(d, project_code="99-ZZ-TEST")
        self.assertIn("segments", result["objects"][0]["geometry"])
        self.assertEqual(len(result["objects"][0]["geometry"]["segments"]), 3)


class TestOpenPathGeometry(unittest.TestCase):
    def test_open_path_2_coords_ok(self):
        d = _make_drawing([
            {"id": "o1", "type": "vehicle_flow", "geometry": _open_path()},
        ], drawing_type="traffic_analysis")
        result = normalize_drawing(d, project_code="99-ZZ-TEST")
        self.assertFalse(result["objects"][0]["geometry"]["closed"])

    def test_open_path_1_coord_rejects(self):
        d = _make_drawing([
            {"id": "o1", "type": "vehicle_flow", "geometry": _open_path([[0.5, 0.5]])},
        ], drawing_type="traffic_analysis")
        with self.assertRaises(DrawingValidationError):
            normalize_drawing(d, project_code="99-ZZ-TEST")

    def test_open_path_4_coords_ok(self):
        coords = [[0.1, 0.1], [0.2, 0.2], [0.3, 0.3], [0.4, 0.4]]
        d = _make_drawing([
            {"id": "o1", "type": "vehicle_flow", "geometry": _open_path(coords)},
        ], drawing_type="traffic_analysis")
        result = normalize_drawing(d, project_code="99-ZZ-TEST")
        self.assertEqual(len(result["objects"][0]["geometry"]["coords"]), 4)

    def test_open_path_with_quadratic_segment(self):
        segs = [
            {"kind": "line", "from": [0.1, 0.1], "to": [0.2, 0.2]},
            {"kind": "quadratic", "from": [0.2, 0.2], "control": [0.25, 0.15], "to": [0.3, 0.3]},
        ]
        d = _make_drawing([
            {"id": "o1", "type": "vehicle_flow", "geometry": _open_path(segments=segs)},
        ], drawing_type="traffic_analysis")
        result = normalize_drawing(d, project_code="99-ZZ-TEST")
        self.assertIn("segments", result["objects"][0]["geometry"])
        self.assertFalse(result["objects"][0]["geometry"]["closed"])

    def test_open_path_discontinuous_segments_rejects(self):
        segs = [
            {"kind": "line", "from": [0.1, 0.1], "to": [0.2, 0.2]},
            {"kind": "line", "from": [0.3, 0.3], "to": [0.4, 0.4]},
        ]
        d = _make_drawing([
            {"id": "o1", "type": "vehicle_flow", "geometry": _open_path(segments=segs)},
        ], drawing_type="traffic_analysis")
        with self.assertRaises(DrawingValidationError):
            normalize_drawing(d, project_code="99-ZZ-TEST")

    def test_closed_path_non_closing_segments_rejects(self):
        segs = [
            {"kind": "line", "from": [0.1, 0.1], "to": [0.3, 0.1]},
            {"kind": "line", "from": [0.3, 0.1], "to": [0.3, 0.3]},
        ]
        d = _make_drawing([{"id": "o1", "type": "functional_zone", "geometry": _closed_path(segments=segs)}])
        with self.assertRaises(DrawingValidationError):
            normalize_drawing(d, project_code="99-ZZ-TEST")


class TestCircleGeometry(unittest.TestCase):
    def test_circle_ok(self):
        d = _make_drawing([
            {"id": "o1", "type": "landscape_node", "geometry": _circle()},
        ], drawing_type="landscape_analysis")
        result = normalize_drawing(d, project_code="99-ZZ-TEST")
        self.assertEqual(result["objects"][0]["geometry"]["kind"], "circle")
        self.assertEqual(result["objects"][0]["geometry"]["radius"], 0.035)

    def test_circle_missing_radius_rejects(self):
        d = _make_drawing([
            {"id": "o1", "type": "landscape_node", "geometry": {"kind": "circle", "center": [0.5, 0.5]}},
        ], drawing_type="landscape_analysis")
        with self.assertRaises(DrawingValidationError):
            normalize_drawing(d, project_code="99-ZZ-TEST")

    def test_circle_radius_too_large_rejects(self):
        d = _make_drawing([
            {"id": "o1", "type": "landscape_node", "geometry": _circle(radius=0.5)},
        ], drawing_type="landscape_analysis")
        with self.assertRaises(DrawingValidationError):
            normalize_drawing(d, project_code="99-ZZ-TEST")

    def test_circle_radius_too_small_rejects(self):
        d = _make_drawing([
            {"id": "o1", "type": "landscape_node", "geometry": _circle(radius=0.001)},
        ], drawing_type="landscape_analysis")
        with self.assertRaises(DrawingValidationError):
            normalize_drawing(d, project_code="99-ZZ-TEST")


class TestTriangleGeometry(unittest.TestCase):
    def test_triangle_ok(self):
        d = _make_drawing([
            {"id": "o1", "type": "entrance_marker", "geometry": _triangle()},
        ], drawing_type="traffic_analysis")
        result = normalize_drawing(d, project_code="99-ZZ-TEST")
        self.assertEqual(result["objects"][0]["geometry"]["kind"], "triangle")
        self.assertEqual(result["objects"][0]["geometry"]["rotation_deg"], 0)

    def test_triangle_missing_size_rejects(self):
        d = _make_drawing([
            {"id": "o1", "type": "entrance_marker", "geometry": {"kind": "triangle", "center": [0.5, 0.5]}},
        ], drawing_type="traffic_analysis")
        with self.assertRaises(DrawingValidationError):
            normalize_drawing(d, project_code="99-ZZ-TEST")

    def test_triangle_with_rotation(self):
        d = _make_drawing([
            {"id": "o1", "type": "entrance_marker", "geometry": _triangle(rotation_deg=45)},
        ], drawing_type="traffic_analysis")
        result = normalize_drawing(d, project_code="99-ZZ-TEST")
        self.assertEqual(result["objects"][0]["geometry"]["rotation_deg"], 45)


class TestStyleHints(unittest.TestCase):
    def test_fill_enabled_migrates_to_fill_mode_translucent(self):
        d = _make_drawing([{
            "id": "o1",
            "type": "functional_zone",
            "geometry": _closed_path(),
            "style_hints": {"fill_enabled": True, "fill_color": "#DCE8C8", "border_style": "solid", "stroke_width": 0.003},
        }])
        result = normalize_drawing(d, project_code="99-ZZ-TEST")
        self.assertEqual(result["objects"][0]["style_hints"]["fill_mode"], "translucent")

    def test_fill_disabled_migrates_to_fill_mode_none(self):
        d = _make_drawing([{
            "id": "o1",
            "type": "functional_zone",
            "geometry": _closed_path(),
            "style_hints": {"fill_enabled": False, "fill_color": "#DCE8C8", "border_style": "solid", "stroke_width": 0.003},
        }])
        result = normalize_drawing(d, project_code="99-ZZ-TEST")
        self.assertEqual(result["objects"][0]["style_hints"]["fill_mode"], "none")


class TestLegacyMigration(unittest.TestCase):
    def test_old_polygon_migrates_to_path_closed_true(self):
        d = _make_drawing([{
            "id": "o1",
            "type": "functional_zone",
            "geometry": {"kind": "polygon", "coords": [[0.1, 0.1], [0.3, 0.1], [0.3, 0.3]]},
            "style_hints": {"fill_enabled": True, "fill_color": "#DCE8C8", "border_style": "solid", "stroke_width": 0.003},
        }], schema_version="1.0")
        result = normalize_drawing(d, project_code="99-ZZ-TEST")
        self.assertEqual(result["objects"][0]["geometry"]["kind"], "path")
        self.assertTrue(result["objects"][0]["geometry"]["closed"])

    def test_old_polyline_migrates_to_path_closed_false(self):
        d = _make_drawing([{
            "id": "o1",
            "type": "vehicle_flow",
            "geometry": {"kind": "polyline", "coords": [[0.1, 0.1], [0.3, 0.3]]},
        }], schema_version="1.0", drawing_type="traffic_analysis")
        result = normalize_drawing(d, project_code="99-ZZ-TEST")
        self.assertEqual(result["objects"][0]["geometry"]["kind"], "path")
        self.assertFalse(result["objects"][0]["geometry"]["closed"])

    def test_old_arrow_migrates_to_path_closed_false(self):
        d = _make_drawing([{
            "id": "o1",
            "type": "vehicle_flow",
            "geometry": {"kind": "arrow", "coords": [[0.1, 0.1], [0.3, 0.3]]},
        }], schema_version="1.0", drawing_type="traffic_analysis")
        result = normalize_drawing(d, project_code="99-ZZ-TEST")
        self.assertEqual(result["objects"][0]["geometry"]["kind"], "path")
        self.assertFalse(result["objects"][0]["geometry"]["closed"])

    def test_main_entrance_point_migrates_to_entrance_marker_triangle(self):
        d = _make_drawing([{
            "id": "o1",
            "type": "main_entrance",
            "geometry": {"kind": "point", "coords": [[0.5, 0.5]]},
        }], schema_version="1.0", drawing_type="traffic_analysis")
        result = normalize_drawing(d, project_code="99-ZZ-TEST")
        obj = result["objects"][0]
        self.assertEqual(obj["type"], "entrance_marker")
        self.assertEqual(obj["geometry"]["kind"], "triangle")
        self.assertIn("size", obj["geometry"])
        self.assertEqual(obj["geometry"]["rotation_deg"], 0)

    def test_old_label_point_preserved_as_point(self):
        d = _make_drawing([{
            "id": "o1",
            "type": "label",
            "geometry": {"kind": "point", "coords": [[0.5, 0.5]]},
        }], schema_version="1.0", drawing_type="traffic_analysis")
        result = normalize_drawing(d, project_code="99-ZZ-TEST")
        obj = result["objects"][0]
        self.assertEqual(obj["type"], "label")
        self.assertEqual(obj["geometry"]["kind"], "point")


class TestTurningRadiusDefaults(unittest.TestCase):
    def test_turning_radius_default_label_box(self):
        d = _make_drawing([{
            "id": "o1",
            "type": "turning_radius",
            "geometry": _open_path([[0.1, 0.1], [0.3, 0.3]]),
        }], drawing_type="fire_route")
        result = normalize_drawing(d, project_code="99-ZZ-TEST")
        style = result["objects"][0]["style_hints"]
        self.assertTrue(style.get("label_box", {}).get("enabled"))
        self.assertEqual(style.get("label_box", {}).get("text"), "R=9M")


class TestSlopeArrowDefaults(unittest.TestCase):
    def test_slope_arrow_default_inline_text(self):
        d = _make_drawing([{
            "id": "o1",
            "type": "slope_arrow",
            "geometry": _open_path([[0.1, 0.1], [0.3, 0.3]]),
        }], drawing_type="vertical_analysis")
        result = normalize_drawing(d, project_code="99-ZZ-TEST")
        style = result["objects"][0]["style_hints"]
        self.assertTrue(style.get("inline_text", {}).get("enabled"))
        self.assertEqual(style.get("inline_text", {}).get("text"), "0.3%")


class TestLegacyPolygonWithSegmentsRegression(unittest.TestCase):
    """Regression: real functional_zoning.json with polygon+segments must load without loss."""

    def test_real_file_loads_if_exists(self):
        if not REAL_FZ_PATH.exists():
            self.skipTest("Real functional_zoning.json not found")
        raw = json.loads(REAL_FZ_PATH.read_text(encoding="utf-8"))
        original_count = len(raw.get("objects", []))
        result = normalize_drawing(raw, project_code="26-BQ-PARK")
        self.assertEqual(len(result["objects"]), original_count)
        for obj in result["objects"]:
            self.assertEqual(obj["geometry"]["kind"], "path")
            self.assertTrue(obj["geometry"]["closed"])

    def test_save_reload_roundtrip_preserves_count(self):
        if not REAL_FZ_PATH.exists():
            self.skipTest("Real functional_zoning.json not found")
        raw = json.loads(REAL_FZ_PATH.read_text(encoding="utf-8"))
        original_count = len(raw.get("objects", []))
        result = normalize_drawing(raw, project_code="26-BQ-PARK")
        result2 = normalize_drawing(result, project_code="26-BQ-PARK")
        self.assertEqual(len(result2["objects"]), original_count)
        for obj in result2["objects"]:
            self.assertEqual(obj["geometry"]["kind"], "path")
            self.assertTrue(obj["geometry"]["closed"])


class TestOutputSchemaVersion(unittest.TestCase):
    def test_output_always_12(self):
        d = _make_drawing([{
            "id": "o1",
            "type": "functional_zone",
            "geometry": _closed_path(),
            "style_hints": {"fill_enabled": True, "fill_color": "#DCE8C8", "border_style": "solid", "stroke_width": 0.003},
        }], schema_version="1.0")
        result = normalize_drawing(d, project_code="99-ZZ-TEST")
        self.assertEqual(result["schema_version"], "1.2")


class TestDefaultObjectStyles(unittest.TestCase):
    def test_functional_zone_default(self):
        style = default_object_style("functional_zone")
        self.assertIn("fill_mode", style)
        self.assertIn("stroke_color", style)

    def test_turning_radius_default_has_label_box(self):
        style = default_object_style("turning_radius")
        self.assertTrue(style.get("label_box", {}).get("enabled"))

    def test_slope_arrow_default_has_inline_text(self):
        style = default_object_style("slope_arrow")
        self.assertTrue(style.get("inline_text", {}).get("enabled"))


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Unit tests for drawing task pack with supporting images."""
from __future__ import annotations

import json
import shutil
import unittest
from pathlib import Path

from _tools.drawing_workbench.registry import DRAWING_TYPES
from _tools.drawing_workbench.task_pack import build_task_pack

REPO_ROOT = Path(__file__).resolve().parents[2]
TEST_PROJECT = "99-ZZ-WBTEST"


def _ensure_test_project() -> Path:
    proj = REPO_ROOT / "projects" / TEST_PROJECT
    proj.mkdir(parents=True, exist_ok=True)
    (proj / "05_output" / "drawings" / "semantic").mkdir(parents=True, exist_ok=True)
    (proj / "05_output" / "drawings" / "base").mkdir(parents=True, exist_ok=True)
    base_img = proj / "05_output" / "drawings" / "base" / "master_plan.jpg"
    if not base_img.exists():
        base_img.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
    return proj


def _make_minimal_drawing(drawing_type: str) -> dict:
    obj_type_map = {
        "functional_zoning": ("functional_zone", "path", True),
        "location_analysis": ("location_road_line", "path", False),
        "planting_design": ("planting_zone", "path", True),
        "landscape_analysis": ("landscape_node", "circle", None),
        "traffic_analysis": ("vehicle_flow", "path", False),
        "fire_route": ("fire_route_line", "path", False),
        "vertical_analysis": ("slope_arrow", "path", False),
        "supporting_facilities": ("facility_zone", "path", True),
        "sponge_city": ("sponge_zone", "path", True),
        "accessibility_design": ("accessible_facility_zone", "path", True),
        "civil_defense": ("civil_defense_zone", "path", True),
    }
    otype, gkind, closed = obj_type_map[drawing_type]
    if gkind == "path":
        if closed:
            geo = {"kind": "path", "closed": True, "coords": [[0.1, 0.1], [0.3, 0.1], [0.3, 0.3]]}
        else:
            geo = {"kind": "path", "closed": False, "coords": [[0.1, 0.1], [0.3, 0.3]]}
    elif gkind == "circle":
        geo = {"kind": "circle", "center": [0.5, 0.5], "radius": 0.035}
    else:
        geo = {"kind": "path", "closed": False, "coords": [[0.1, 0.1], [0.3, 0.3]]}

    base_path = "05_output/drawings/base/civil_defense_base.jpg" if drawing_type == "civil_defense" else "05_output/drawings/base/master_plan.jpg"
    return {
        "schema_version": "1.2",
        "drawing_type": drawing_type,
        "project_code": TEST_PROJECT,
        "base_image": {"path": base_path, "natural_width": 100, "natural_height": 100, "source": "user_upload"},
        "created_at": "2026-01-01T00:00:00+00:00",
        "last_edited_by": "agent",
        "objects": [{"id": "o1", "type": otype, "geometry": geo, "label": "test", "confidence": "medium", "source": "user_sketch", "style_hints": {}}],
    }


class TestTaskPackBuildsForAllDrawingTypes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proj = _ensure_test_project()

    @classmethod
    def tearDownClass(cls):
        pass

    def _cleanup_packs(self):
        packs_dir = self.proj / "05_output" / "drawings" / "task_packs"
        if packs_dir.exists():
            shutil.rmtree(packs_dir)

    def test_builds_for_each_drawing_type(self):
        for dt in sorted(DRAWING_TYPES):
            with self.subTest(drawing_type=dt):
                self._cleanup_packs()
                semantic_dir = self.proj / "05_output" / "drawings" / "semantic"
                sketch_path = semantic_dir / f"{dt}.json"
                drawing = _make_minimal_drawing(dt)
                sketch_path.write_text(json.dumps(drawing, ensure_ascii=False, indent=2), encoding="utf-8")
                try:
                    pack_dir = build_task_pack(TEST_PROJECT, dt, sketch_path=str(sketch_path))
                    self.assertTrue(pack_dir.exists())
                    task_json = pack_dir / "task.json"
                    self.assertTrue(task_json.exists())
                    task = json.loads(task_json.read_text(encoding="utf-8"))
                    self.assertEqual(task["drawing_type"], dt)
                    self.assertIn("inputs", task)
                finally:
                    self._cleanup_packs()
                    sketch_path.unlink(missing_ok=True)

    def test_missing_supporting_manifest_gives_count_0(self):
        self._cleanup_packs()
        dt = "planting_design"
        semantic_dir = self.proj / "05_output" / "drawings" / "semantic"
        sketch_path = semantic_dir / f"{dt}.json"
        drawing = _make_minimal_drawing(dt)
        sketch_path.write_text(json.dumps(drawing, ensure_ascii=False, indent=2), encoding="utf-8")
        try:
            pack_dir = build_task_pack(TEST_PROJECT, dt, sketch_path=str(sketch_path))
            task = json.loads((pack_dir / "task.json").read_text(encoding="utf-8"))
            si = task["inputs"].get("supporting_images", {})
            self.assertEqual(si.get("count", 0), 0)
        finally:
            self._cleanup_packs()
            sketch_path.unlink(missing_ok=True)

    def test_alias_drawing_type_builds_canonical_pack(self):
        self._cleanup_packs()
        semantic_dir = self.proj / "05_output" / "drawings" / "semantic"
        sketch_path = semantic_dir / "vertical_analysis.json"
        drawing = _make_minimal_drawing("vertical_analysis")
        sketch_path.write_text(json.dumps(drawing, ensure_ascii=False, indent=2), encoding="utf-8")
        try:
            pack_dir = build_task_pack(TEST_PROJECT, "elevation", sketch_path=str(sketch_path))
            task = json.loads((pack_dir / "task.json").read_text(encoding="utf-8"))
            self.assertEqual(task["drawing_type"], "vertical_analysis")
            self.assertTrue(pack_dir.name.startswith("vertical_analysis__"))
        finally:
            self._cleanup_packs()
            sketch_path.unlink(missing_ok=True)


class TestPageIndexReferences(unittest.TestCase):
    def test_page_index_loads_without_crash(self):
        page_index = REPO_ROOT / "docs" / "reference_pdfs" / "page_index.json"
        if not page_index.exists():
            self.skipTest("page_index.json not found")
        data = json.loads(page_index.read_text(encoding="utf-8"))
        self.assertIsInstance(data, dict)


if __name__ == "__main__":
    unittest.main()

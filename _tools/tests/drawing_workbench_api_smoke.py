#!/usr/bin/env python3
"""API smoke test for drawing workbench endpoints."""
from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TEST_PROJECT = "99-ZZ-WBTEST"
PORT = 18765
BASE = f"http://127.0.0.1:{PORT}"


def api_get(path: str) -> dict:
    url = f"{BASE}{path}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def api_post(path: str, body: dict) -> dict:
    url = f"{BASE}{path}"
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def main() -> int:
    proj_dir = REPO_ROOT / "projects" / TEST_PROJECT
    if proj_dir.exists():
        shutil.rmtree(proj_dir)
    proj_dir.mkdir(parents=True)
    (proj_dir / "05_output" / "drawings" / "base").mkdir(parents=True)
    (proj_dir / "05_output" / "drawings" / "semantic").mkdir(parents=True)
    base_img = proj_dir / "05_output" / "drawings" / "base" / "master_plan.jpg"
    base_img.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    preset_src = REPO_ROOT / "_tools" / "drawing_workbench" / "style_presets.json"
    preset_test = proj_dir / "05_output" / "drawings" / "style_presets_api_smoke.json"
    shutil.copyfile(preset_src, preset_test)
    env["DRAWING_STYLE_PRESETS_PATH"] = str(preset_test)
    server = subprocess.Popen(
        [sys.executable, str(REPO_ROOT / "_tools" / "uploader" / "server.py"),
         "--port", str(PORT), "--no-browser"],
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    try:
        for _ in range(30):
            try:
                api_get("/api/projects")
                break
            except Exception:
                time.sleep(0.3)
        else:
            print("FAIL: server did not start", file=sys.stderr)
            return 1

        # Test registry endpoint
        reg = api_get("/api/drawing/registry")
        assert reg.get("ok"), f"registry not ok: {reg}"
        drawings = reg.get("drawings", {})
        expected_types = [
            "functional_zoning", "planting_design", "landscape_analysis",
            "traffic_analysis", "fire_route", "vertical_analysis",
            "supporting_facilities", "sponge_city", "accessibility_design",
            "civil_defense",
        ]
        for dt in expected_types:
            assert dt in drawings, f"missing drawing type: {dt}"
        print(f"OK: registry has {len(drawings)} drawing types")

        # Test load for each drawing type
        for dt in expected_types:
            result = api_get(f"/api/drawing/load?project={TEST_PROJECT}&drawing_type={dt}")
            assert result.get("ok"), f"load failed for {dt}: {result}"
            assert result.get("drawing"), f"no drawing for {dt}"
        print(f"OK: load works for all {len(expected_types)} drawing types")

        # Test PPT deck layout load/save/reflow
        deck = api_get(f"/api/drawing/deck-layout?project={TEST_PROJECT}")
        assert deck.get("ok"), f"deck layout load failed: {deck}"
        layout = deck.get("layout") or {}
        assert layout.get("slide", {}).get("aspect") == "16:9", f"deck layout should be 16:9: {layout}"
        assert layout.get("drawing_frame") and len(layout.get("slides", {})) == len(expected_types), (
            f"deck layout missing global frame or slides: {layout}"
        )
        saved_deck = api_post(
            "/api/drawing/deck-layout/save",
            {
                "project": TEST_PROJECT,
                "drawing_type": "functional_zoning",
                "slide": {"text": "PPT smoke text"},
            },
        )
        assert (
            saved_deck.get("layout", {})
            .get("slides", {})
            .get("functional_zoning", {})
            .get("text")
            == "PPT smoke text"
        ), f"deck slide text did not save: {saved_deck}"
        version_before = int(saved_deck.get("layout", {}).get("drawing_frame_version") or 0)
        switched = api_post(
            "/api/drawing/deck-layout/save",
            {"project": TEST_PROJECT, "template_side": "drawing_right"},
        )
        switched_layout = switched.get("layout", {})
        assert switched_layout.get("template_side") == "drawing_right", f"template side did not switch: {switched}"
        assert int(switched_layout.get("drawing_frame_version") or 0) == version_before + 1, (
            f"template switch should bump frame version: before={version_before}, after={switched_layout}"
        )
        assert all(slide.get("needs_reflow") for slide in switched_layout.get("slides", {}).values()), (
            f"template switch should mark all slides for reflow: {switched_layout}"
        )
        reflowed = api_post(
            "/api/drawing/deck-layout/reflow",
            {"project": TEST_PROJECT, "drawing_type": "functional_zoning", "scope": "current"},
        )
        reflowed_slides = reflowed.get("layout", {}).get("slides", {})
        assert reflowed_slides.get("functional_zoning", {}).get("needs_reflow") is False, (
            f"current reflow should clear current slide: {reflowed}"
        )
        assert reflowed_slides.get("traffic_analysis", {}).get("needs_reflow") is True, (
            f"current reflow should not clear other slides: {reflowed}"
        )
        print("OK: PPT deck layout load/save/template/reflow works")

        # Test save for each drawing type
        payloads = {
            "functional_zoning": {
                "type": "functional_zone",
                "geometry": {"kind": "path", "closed": True, "coords": [[0.1, 0.1], [0.3, 0.1], [0.3, 0.3]]},
                "label": "test",
            },
            "planting_design": {
                "type": "planting_zone",
                "geometry": {"kind": "path", "closed": True, "coords": [[0.1, 0.1], [0.3, 0.1], [0.3, 0.3]]},
                "label": "test",
            },
            "landscape_analysis": {
                "type": "landscape_node",
                "geometry": {"kind": "circle", "center": [0.5, 0.5], "radius": 0.035},
                "label": "test",
            },
            "traffic_analysis": {
                "type": "vehicle_flow",
                "geometry": {"kind": "path", "closed": False, "coords": [[0.1, 0.1], [0.3, 0.3]]},
                "label": "test",
            },
            "fire_route": {
                "type": "fire_route_line",
                "geometry": {"kind": "path", "closed": False, "coords": [[0.1, 0.1], [0.3, 0.3]]},
                "label": "test",
            },
            "vertical_analysis": {
                "type": "slope_arrow",
                "geometry": {"kind": "path", "closed": False, "coords": [[0.1, 0.1], [0.3, 0.3]]},
                "label": "test",
            },
            "supporting_facilities": {
                "type": "facility_zone",
                "geometry": {"kind": "path", "closed": True, "coords": [[0.1, 0.1], [0.3, 0.1], [0.3, 0.3]]},
                "label": "test",
            },
            "sponge_city": {
                "type": "sponge_zone",
                "geometry": {"kind": "path", "closed": True, "coords": [[0.1, 0.1], [0.3, 0.1], [0.3, 0.3]]},
                "label": "test",
            },
            "accessibility_design": {
                "type": "accessible_facility_zone",
                "geometry": {"kind": "path", "closed": True, "coords": [[0.1, 0.1], [0.3, 0.1], [0.3, 0.3]]},
                "label": "test",
            },
            "civil_defense": {
                "type": "civil_defense_zone",
                "geometry": {"kind": "path", "closed": True, "coords": [[0.1, 0.1], [0.3, 0.1], [0.3, 0.3]]},
                "label": "test",
            },
        }

        for dt, obj in payloads.items():
            drawing = {
                "schema_version": "1.2",
                "drawing_type": dt,
                "project_code": TEST_PROJECT,
                "base_image": {
                    "path": "05_output/drawings/base/civil_defense_base.jpg" if dt == "civil_defense" else "05_output/drawings/base/master_plan.jpg",
                    "natural_width": 100,
                    "natural_height": 100,
                    "source": "user_upload",
                },
                "created_at": "2026-01-01T00:00:00+00:00",
                "last_edited_by": "agent",
                "objects": [{"id": "o1", **obj, "confidence": "medium", "source": "user_sketch", "style_hints": {}}],
            }
            result = api_post("/api/drawing/save", {"project": TEST_PROJECT, "drawing": drawing})
            assert result.get("ok"), f"save failed for {dt}: {result}"
            saved_drawing = result.get("drawing", {})
            assert len(saved_drawing.get("objects", [])) == 1, f"object count wrong for {dt}"
        print(f"OK: save works for all {len(payloads)} drawing types")

        # Test supporting images list (empty)
        result = api_get(f"/api/drawing/supporting/list?project={TEST_PROJECT}&drawing_type=planting_design")
        assert result.get("ok"), f"supporting list failed: {result}"
        print("OK: supporting images list endpoint works")

        # Test shared style presets library
        presets = api_get("/api/drawing/style-presets")
        assert presets.get("ok"), f"style presets load failed: {presets}"
        assert any(item.get("kind") == "functional_zone" for item in presets.get("presets", [])), (
            "style presets should include functional zoning presets"
        )
        preset = {
            "id": "api-smoke-preset",
            "name": "API smoke preset",
            "kind": "functional_zone",
            "hints": {
                "fill_mode": "translucent",
                "fill_color": "#ABCDEF",
                "stroke_color": "#123456",
                "border_style": "solid",
            },
        }
        saved = api_post("/api/drawing/style-presets/save", {"preset": preset})
        assert saved.get("ok") and any(item.get("id") == "api-smoke-preset" for item in saved.get("presets", [])), (
            f"style preset save failed: {saved}"
        )
        imported = api_post(
            "/api/drawing/style-presets/import",
            {
                "library": {
                    "presets": [
                        {
                            "id": "api-import-preset",
                            "name": "API import preset",
                            "kind": "vehicle_flow",
                            "hints": {"stroke_color": "#AA3300", "stroke_width": 0.006},
                        }
                    ]
                }
            },
        )
        assert imported.get("ok") and imported.get("imported") == 1, f"style preset import failed: {imported}"
        deleted = api_post("/api/drawing/style-presets/delete", {"id": "api-smoke-preset"})
        assert deleted.get("ok") and not any(item.get("id") == "api-smoke-preset" for item in deleted.get("presets", [])), (
            f"style preset delete failed: {deleted}"
        )
        print("OK: shared style presets load/save/import/delete works")

        print("\nALL API SMOKE TESTS PASSED")
        return 0

    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
        if proj_dir.exists():
            shutil.rmtree(proj_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())

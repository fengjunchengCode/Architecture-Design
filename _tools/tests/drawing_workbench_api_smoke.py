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
import zipfile
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


def api_post_error(path: str, body: dict) -> dict:
    url = f"{BASE}{path}"
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return {"status": resp.status, "body": json.loads(resp.read())}
    except urllib.error.HTTPError as exc:
        return {"status": exc.code, "body": json.loads(exc.read())}


def boxes_intersect(a: dict, b: dict) -> bool:
    return not (
        a["x"] + a["w"] <= b["x"]
        or b["x"] + b["w"] <= a["x"]
        or a["y"] + a["h"] <= b["y"]
        or b["y"] + b["h"] <= a["y"]
    )


def write_supporting_manifest(proj_dir: Path, drawing_type: str, count: int) -> None:
    sup_dir = proj_dir / "05_output" / "drawings" / "supporting" / drawing_type
    sup_dir.mkdir(parents=True, exist_ok=True)
    images = [
        {
            "id": f"support-{index + 1}",
            "stored_name": f"support-{index + 1}.jpg",
            "original_name": f"support-{index + 1}.jpg",
            "caption": f"support {index + 1}",
        }
        for index in range(count)
    ]
    (sup_dir / "manifest.json").write_text(
        json.dumps({"images": images}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_semantic_objects(proj_dir: Path, drawing_type: str, count: int) -> None:
    semantic_dir = proj_dir / "05_output" / "drawings" / "semantic"
    semantic_dir.mkdir(parents=True, exist_ok=True)
    objects = [
        {
            "id": f"legend-{index + 1}",
            "type": "planting_line",
            "geometry": {
                "kind": "path",
                "closed": False,
                "coords": [[0.1, 0.1 + index * 0.01], [0.3, 0.1 + index * 0.01]],
            },
            "label": f"legend {index + 1}",
            "style_hints": {"legend_enabled": True, "stroke_width": 0.004, "stroke_color": "#5B8C3A"},
        }
        for index in range(count)
    ]
    payload = {
        "schema_version": "1.2",
        "drawing_type": drawing_type,
        "project_code": TEST_PROJECT,
        "objects": objects,
    }
    (semantic_dir / f"{drawing_type}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_site_context_inputs(proj_dir: Path) -> None:
    amap_dir = proj_dir / "05_output" / "amap"
    cad_dir = proj_dir / "05_output" / "cad"
    amap_dir.mkdir(parents=True, exist_ok=True)
    cad_dir.mkdir(parents=True, exist_ok=True)
    s1_context = {
        "schema_version": "1.0",
        "status": "ok",
        "project_code": TEST_PROJECT,
        "provider": {"name": "amap_webservice"},
        "location": {
            "amap_gcj02": "94.032582,31.925470",
            "source": "api_smoke",
            "confidence": "high",
        },
        "map_context": {
            "coordinate_system": "GCJ-02 / AMap",
            "regeo": {
                "formatted_address": "西藏自治区那曲市巴青县拉西镇曲登纳桥",
                "roads": [
                    {"name": "G317", "direction": "南", "distance": "40"},
                    {"name": "650乡道", "direction": "东", "distance": "130"},
                ],
                "nearby_pois": [
                    {
                        "name": "曲登纳桥",
                        "type": "地名地址信息;交通地名;桥",
                        "address": "317国道",
                        "location": "94.032245,31.926174",
                        "distance_m": "84",
                    }
                ],
            },
            "keyword_context": {
                "桥": {
                    "status": "ok",
                    "items": [
                        {
                            "name": "曲登纳桥",
                            "type": "地名地址信息;交通地名;桥",
                            "address": "317国道",
                            "location": "94.032245,31.926174",
                            "distance_m": "84",
                        }
                    ],
                }
            },
        },
        "s1_external_context_seed": {
            "external_features": {
                "primary_roads": ["G317"],
                "secondary_roads": ["650乡道"],
                "landscape_or_culture_nodes": ["曲登纳桥"],
            },
            "amap_context": {
                "roads": ["G317", "650乡道"],
                "water": ["曲登纳桥"],
                "poi_1000m": {
                    "transport": ["巴青县客运站"],
                    "education_culture": ["巴青县第一小学"],
                },
            },
        },
    }
    redline = {
        "type": "FeatureCollection",
        "name": "redline_candidate_1306",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "project": TEST_PROJECT,
                    "handle": "1306",
                    "area_xy": 15052.575,
                    "unit_note": "DXF INSUNITS=0; coordinates are CAD/projected coordinates, not WGS84.",
                    "confidence": "candidate_needs_cad_review",
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [597564.9, 3534324.3],
                        [597602.4, 3534303.4],
                        [597569.4, 3534240.6],
                        [597408.2, 3534296.9],
                        [597497.5, 3534370.6],
                        [597564.9, 3534324.3],
                    ]],
                },
            }
        ],
    }
    (amap_dir / "s1_map_context.json").write_text(json.dumps(s1_context, ensure_ascii=False, indent=2), encoding="utf-8")
    (cad_dir / "redline_candidate_1306.geojson").write_text(json.dumps(redline, ensure_ascii=False, indent=2), encoding="utf-8")


def assert_site_context_api(proj_dir: Path) -> None:
    spatial = api_get(f"/api/spatial?project={TEST_PROJECT}")
    redline = spatial.get("redline") or {}
    reliability = redline.get("coordinate_reliability") or {}
    assert redline.get("exists"), f"spatial should expose CAD redline: {spatial}"
    assert reliability.get("reliable") is False, f"CAD/projected coordinates must not be treated as WGS84: {redline}"
    assert len(redline.get("normalized_points") or []) >= 4, f"redline overlay points missing: {redline}"
    road_names = [item.get("name") for item in ((spatial.get("surroundings") or {}).get("roads") or [])]
    assert "G317" in road_names and "650乡道" in road_names, f"S1 roads not projected into S2: {road_names}"

    payload = {
        "project": TEST_PROJECT,
        "north_deg": 17.5,
        "redline_transform": {"x": 0.54, "y": 0.48, "rotation_deg": 17.5, "scale": 1.08},
        "site_polygon_geo": {
            "coordinate_system": "GCJ-02 / AMap approximate",
            "points": [
                {"lng": 94.0321, "lat": 31.9251},
                {"lng": 94.0330, "lat": 31.9252},
                {"lng": 94.0328, "lat": 31.9260},
                {"lng": 94.0321, "lat": 31.9251},
            ],
        },
        "entrances": [
            {
                "id": "ENT-1",
                "label": "主入口",
                "point_on_redline": {"lng": 94.0324, "lat": 31.9255, "edge_index": 1, "edge_t": 0.42},
                "faces_road": "G317",
            }
        ],
        "surroundings": {
            "roads": [{"name": "G317", "note": "南侧主要到达道路"}],
            "land_uses": [{"name": "巴青县第一小学", "category": "education_culture"}],
            "notes": ["入口由人工在红线边上标注"],
        },
    }
    saved = api_post("/api/site-context", payload)
    assert saved.get("ok") and saved.get("path") == "05_output/site_context/site_context.json", f"save failed: {saved}"
    written = json.loads((proj_dir / saved["path"]).read_text(encoding="utf-8"))
    assert written["north_deg"] == 17.5, f"north_deg did not persist: {written}"
    assert written["entrances"][0]["faces_road"] == "G317", f"entrance road did not persist: {written}"
    assert written["surroundings"]["roads"][0]["name"] == "G317", f"surroundings did not persist: {written}"

    invalid = dict(payload)
    invalid["entrances"] = []
    rejected = api_post_error("/api/site-context", invalid)
    assert rejected["status"] == 400 and "entrances" in json.dumps(rejected["body"], ensure_ascii=False), (
        f"site_context schema should reject missing entrances: {rejected}"
    )


def assert_reflow_adaptive(proj_dir: Path) -> None:
    drawing_type = "planting_design"
    frame = api_get(f"/api/drawing/deck-layout?project={TEST_PROJECT}")["layout"]["drawing_frame"]
    write_semantic_objects(proj_dir, drawing_type, 5)

    samples = [
        ("empty", "", 0),
        ("short", "短说明。", 1),
        ("long", "这是用于验证 PPT 自动排版的长说明文字。" * 16, 4),
    ]
    seen = {}
    for name, text, image_count in samples:
        write_supporting_manifest(proj_dir, drawing_type, image_count)
        api_post(
            "/api/drawing/deck-layout/save",
            {"project": TEST_PROJECT, "drawing_type": drawing_type, "slide": {"text": text}},
        )
        result = api_post(
            "/api/drawing/deck-layout/reflow",
            {"project": TEST_PROJECT, "drawing_type": drawing_type, "scope": "current"},
        )
        slide = result["layout"]["slides"][drawing_type]
        elements = slide["elements"]
        text_box = elements["text"]
        legend_box = elements["legend"]
        support_boxes = elements["supporting_images"]
        assert text_box["y"] < legend_box["y"], f"{name}: text should be above legend: {elements}"
        assert text_box["y"] + text_box["h"] <= legend_box["y"], f"{name}: text and legend overlap: {elements}"
        for key in ("text", "legend"):
            assert not boxes_intersect(elements[key], frame), f"{name}: {key} overlaps drawing frame: {elements[key]} vs {frame}"
        for box in support_boxes:
            assert not boxes_intersect(box, frame), f"{name}: supporting image overlaps drawing frame: {box} vs {frame}"
        assert len(support_boxes) == image_count, f"{name}: expected {image_count} supporting boxes, got {support_boxes}"
        seen[name] = elements

    assert seen["long"]["text"]["h"] > seen["short"]["text"]["h"], (
        f"long text should receive more height than short text: {seen}"
    )
    four = seen["long"]["supporting_images"]
    assert {round(box["x"], 4) for box in four[:2]} != {round(four[0]["x"], 4)}, f"four images should use a grid: {four}"
    assert {round(box["y"], 4) for box in four} and len({round(box["y"], 4) for box in four}) == 2, (
        f"four images should use two rows: {four}"
    )


def assert_pptx_rich_text_export(path: Path) -> None:
    with zipfile.ZipFile(path) as pptx:
        slide_xml = "\n".join(
            pptx.read(name).decode("utf-8", errors="ignore")
            for name in pptx.namelist()
            if name.startswith("ppt/slides/slide") and name.endswith(".xml")
        )
    assert "停车配套：" in slide_xml, "exported PPTX should include heading text"
    assert "酒店运营" in slide_xml, "exported PPTX should include brand emphasis text"
    assert "**停车配套" not in slide_xml and "*酒店运营*" not in slide_xml, (
        "exported PPTX should render lightweight markup instead of exporting literal asterisks"
    )
    assert "D9882B" in slide_xml.upper(), "exported PPTX should apply the global brand accent to marked text"


def main() -> int:
    proj_dir = REPO_ROOT / "projects" / TEST_PROJECT
    if proj_dir.exists():
        shutil.rmtree(proj_dir)
    proj_dir.mkdir(parents=True)
    (proj_dir / "05_output" / "drawings" / "base").mkdir(parents=True)
    (proj_dir / "05_output" / "drawings" / "semantic").mkdir(parents=True)
    write_site_context_inputs(proj_dir)
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
        required_types = [
            "functional_zoning", "location_analysis", "planting_design",
            "landscape_analysis", "traffic_analysis", "fire_route",
            "vertical_analysis", "supporting_facilities", "sponge_city",
            "accessibility_design", "civil_defense",
        ]
        for dt in required_types:
            assert dt in drawings, f"missing drawing type: {dt}"
        expected_types = list(drawings.keys())
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
        frame = layout["drawing_frame"]
        expected_plate_aspect = round((frame["w"] * 13.333) / (frame["h"] * 7.5), 4)
        assert layout.get("drawing_plate", {}).get("aspect_ratio") == expected_plate_aspect, (
            f"drawing_plate should match global frame ratio: {layout.get('drawing_plate')} vs {expected_plate_aspect}"
        )
        rich_text = "**停车配套：** 沿街设置 *酒店运营* 配套。"
        saved_deck = api_post(
            "/api/drawing/deck-layout/save",
            {
                "project": TEST_PROJECT,
                "drawing_type": "functional_zoning",
                "slide": {"text": rich_text},
            },
        )
        assert (
            saved_deck.get("layout", {})
            .get("slides", {})
            .get("functional_zoning", {})
            .get("text")
            == rich_text
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
        assert_reflow_adaptive(proj_dir)
        exported = api_post("/api/drawing/deck-layout/export", {"project": TEST_PROJECT})
        assert exported.get("ok") and exported.get("path", "").endswith("deck.pptx"), f"PPT export failed: {exported}"
        assert (proj_dir / exported["path"]).exists(), f"PPT export file missing: {exported}"
        assert_pptx_rich_text_export(proj_dir / exported["path"])
        inconsistent_layout = api_get(f"/api/drawing/deck-layout?project={TEST_PROJECT}")["layout"]
        inconsistent_layout["slides"]["traffic_analysis"]["drawing_frame"] = {"x": 0.12, "y": 0.2, "w": 0.52, "h": 0.7}
        api_post("/api/drawing/deck-layout/save", {"project": TEST_PROJECT, "layout": inconsistent_layout})
        rejected = api_post_error("/api/drawing/deck-layout/export", {"project": TEST_PROJECT})
        assert rejected["status"] == 400 and "traffic_analysis" in json.dumps(rejected["body"]), (
            f"export should reject per-slide frame drift: {rejected}"
        )
        print("OK: PPT deck layout load/save/template/reflow works")

        # Test save for each drawing type
        payloads = {
            "functional_zoning": {
                "type": "functional_zone",
                "geometry": {"kind": "path", "closed": True, "coords": [[0.1, 0.1], [0.3, 0.1], [0.3, 0.3]]},
                "label": "test",
            },
            "location_analysis": {
                "type": "location_road_line",
                "geometry": {"kind": "path", "closed": False, "coords": [[0.1, 0.2], [0.4, 0.35]]},
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
            base_paths = {
                "civil_defense": "05_output/drawings/base/civil_defense_base.jpg",
                "location_analysis": "05_output/drawings/base/location_analysis_2km.png",
            }
            drawing = {
                "schema_version": "1.2",
                "drawing_type": dt,
                "project_code": TEST_PROJECT,
                "base_image": {
                    "path": base_paths.get(dt, "05_output/drawings/base/master_plan.jpg"),
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

        assert_site_context_api(proj_dir)
        print("OK: S2 site context API load/save/schema works")

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

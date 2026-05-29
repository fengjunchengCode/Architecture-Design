#!/usr/bin/env python3
"""Hard browser smoke gate for the drawing workbench frontend."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[2]
TEST_PROJECT = "99-ZZ-BROWSER"
PORT = int(os.environ.get("DRAWING_BROWSER_SMOKE_PORT", "18766"))
BASE = f"http://127.0.0.1:{PORT}"


def tool_points(tool_id: str) -> list[list[float]]:
    if tool_id == "closed_path":
        return [[0.18, 0.18], [0.46, 0.2], [0.42, 0.48]]
    if tool_id in {"open_path", "turning_radius", "slope_arrow"}:
        return [[0.16, 0.62], [0.72, 0.66]]
    if tool_id in {"circle", "triangle", "elevation_marker"}:
        return [[0.54, 0.38]]
    raise AssertionError(f"no smoke payload for tool {tool_id}")


def prepare_project() -> Path:
    proj_dir = REPO_ROOT / "projects" / TEST_PROJECT
    if proj_dir.exists():
        shutil.rmtree(proj_dir)
    base_dir = proj_dir / "05_output" / "drawings" / "base"
    base_dir.mkdir(parents=True)
    Image.new("RGB", (900, 600), (245, 242, 232)).save(base_dir / "master_plan.jpg", "JPEG")
    semantic_dir = proj_dir / "05_output" / "drawings" / "semantic"
    semantic_dir.mkdir(parents=True)
    legacy_fz = {
        "schema_version": "1.0",
        "drawing_type": "functional_zoning",
        "project_code": TEST_PROJECT,
        "base_image": {
            "path": "05_output/drawings/base/master_plan.jpg",
            "natural_width": 900,
            "natural_height": 600,
            "source": "user_upload",
        },
        "created_at": "2026-01-01T00:00:00+00:00",
        "last_edited_by": "agent",
        "objects": [
            {
                "id": "obj-legacy",
                "type": "functional_zone",
                "geometry": {
                    "kind": "polygon",
                    "coords": [[0.18, 0.18], [0.46, 0.2], [0.42, 0.48]],
                    "segments": [
                        {"kind": "line", "from": [0.18, 0.18], "to": [0.46, 0.2]},
                        {"kind": "quadratic", "from": [0.46, 0.2], "control": [0.62, 0.34], "to": [0.42, 0.48]},
                        {"kind": "line", "from": [0.42, 0.48], "to": [0.18, 0.18]},
                    ],
                },
                "label": "legacy curved zone",
                "confidence": "medium",
                "source": "user_sketch",
                "style_hints": {
                    "fill_enabled": True,
                    "fill_color": "#DCE8C8",
                    "border_style": "solid",
                    "stroke_width": 0.003,
                },
            },
            {
                "id": "obj-no-fill",
                "type": "functional_zone",
                "geometry": {
                    "kind": "polygon",
                    "coords": [[0.58, 0.2], [0.78, 0.24], [0.7, 0.48]],
                },
                "label": "legacy no fill zone",
                "confidence": "medium",
                "source": "user_sketch",
                "style_hints": {
                    "fill_enabled": False,
                    "fill_color": "#C2D0DB",
                    "border_style": "solid",
                    "stroke_width": 0.003,
                },
            },
        ],
    }
    (semantic_dir / "functional_zoning.json").write_text(json.dumps(legacy_fz, ensure_ascii=False, indent=2), encoding="utf-8")
    return proj_dir


def url_json(path: str) -> dict:
    with urllib.request.urlopen(f"{BASE}{path}", timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_for_server() -> None:
    for _ in range(50):
        try:
            url_json("/api/projects")
            return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError("server did not start")


def assert_no_bad_kinds(objects: list[dict], drawing_type: str) -> None:
    for obj in objects:
        kind = ((obj.get("geometry") or {}).get("kind"))
        assert kind in {"path", "circle", "triangle"}, f"{drawing_type}: illegal geometry.kind {kind!r}"
        assert kind not in {"closed_path", "open_path"}, f"{drawing_type}: leaked tool id {kind!r}"
        if obj.get("type") == "turning_radius":
            assert ((obj.get("style_hints") or {}).get("label_box") or {}).get("enabled"), "turning_radius missing label_box"
        if obj.get("type") == "slope_arrow":
            assert ((obj.get("style_hints") or {}).get("inline_text") or {}).get("enabled"), "slope_arrow missing inline_text"


def assert_fz_regression(page) -> None:
    fill_values = page.eval_on_selector_all(
        '[data-style-segment="fill_mode"]',
        "(nodes) => nodes.map((node) => node.dataset.styleValue)",
    )
    border_values = page.eval_on_selector_all(
        '[data-style-segment="border_style"]',
        "(nodes) => nodes.map((node) => node.dataset.styleValue)",
    )
    assert fill_values == ["none", "translucent", "solid", "hatch"], f"FZ fill controls not unified: {fill_values}"
    assert border_values == ["none", "solid", "dashed", "double"], f"FZ border controls not unified: {border_values}"
    page.wait_for_function(
        "() => window.DrawingWorkbenchTest.getObjects().some((o) => o.id === 'obj-legacy')",
        timeout=15000,
    )
    assert page.locator(".zone-hit[data-object-id='obj-legacy']").count() >= 1, "FZ legacy object missing zone-hit layer"
    page.evaluate(
        """() => document.querySelector(".zone-hit[data-object-id='obj-legacy']")
          .dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }))"""
    )
    assert page.locator(".geometry-vertex-handle").count() >= 3, "FZ selected object missing vertex handles"
    assert page.locator(".zone-arc-handle").count() >= 3, "FZ selected object missing arc handles"
    with page.expect_response(lambda r: "/api/drawing/save" in r.url and r.status == 200, timeout=15000):
        page.click("#workbenchSave")
    with page.expect_response(lambda r: "/api/drawing/load" in r.url and r.status == 200, timeout=15000):
        page.click("#workbenchLoad")
    legacy = page.evaluate("window.DrawingWorkbenchTest.getObjects().find((o) => o.id === 'obj-legacy')")
    assert legacy, "FZ legacy object disappeared after reload"
    segments = ((legacy.get("geometry") or {}).get("segments") or [])
    assert any(seg.get("kind") == "quadratic" for seg in segments), "FZ quadratic segment lost after save/reload"
    visible_shapes = page.locator("#sketchOverlay path:not(.zone-hit), #sketchOverlay polygon:not(.zone-hit)")
    fills = visible_shapes.evaluate_all(
        """(nodes) => nodes.map((node) => ({
            fill: node.getAttribute("fill"),
            opacity: node.getAttribute("fill-opacity")
        }))"""
    )
    assert any(item["fill"] == "none" for item in fills), "FZ legacy fill_enabled=false does not render fill=none"
    assert any(abs(float(item["opacity"] or 0) - 0.42) < 0.001 for item in fills), (
        "FZ legacy fill_enabled=true does not render fill-opacity≈0.42"
    )


def assert_control_rules(page, drawing_type: str, tools: list[str]) -> None:
    if "closed_path" in tools and drawing_type != "functional_zoning":
        page.click('[data-tool-id="closed_path"]')
        fill_values = page.eval_on_selector_all(
            '[data-style-segment="fill_mode"]',
            "(nodes) => nodes.map((node) => node.dataset.styleValue)",
        )
        border_values = page.eval_on_selector_all(
            '[data-style-segment="border_style"]',
            "(nodes) => nodes.map((node) => node.dataset.styleValue)",
        )
        assert fill_values == ["none", "translucent", "solid", "hatch"], f"{drawing_type}: polygon fill controls differ from FZ"
        assert border_values == ["none", "solid", "dashed", "double"], f"{drawing_type}: polygon border controls differ from FZ"
        assert page.locator("#styleStartArrow").count() == 0, f"{drawing_type}: polygon shows start arrow control"
        assert page.locator("#styleEndArrow").count() == 0, f"{drawing_type}: polygon shows end arrow control"
        assert page.locator("#styleArrowSize").count() == 0, f"{drawing_type}: polygon shows arrow size control"
        assert page.locator("#styleDoubleGap").count() == 0, f"{drawing_type}: polygon shows independent double gap control"
        assert page.locator("#styleStrokeStyle").count() == 0, f"{drawing_type}: polygon shows independent stroke style control"
        assert page.locator("[data-supporting-panel='true']").count() == 0, f"{drawing_type}: supporting panel shown under polygon tool"
    for tool in [tool for tool in tools if tool not in {"supporting_images", "closed_path"}]:
        page.click(f'[data-tool-id="{tool}"]')
        assert page.locator("[data-supporting-panel='true']").count() == 0, f"{drawing_type}: supporting panel shown under {tool}"
    if "supporting_images" in tools:
        page.click('[data-tool-id="supporting_images"]')
        assert page.locator("[data-supporting-panel='true']").count() == 1, f"{drawing_type}: supporting panel not shown for supporting tool"


def assert_shared_interaction_dom(page, drawing_type: str, tool: str) -> None:
    assert page.locator(".geometry-hit").count() >= 1, f"{drawing_type}/{tool}: missing shared hit layer"
    assert page.locator(".geometry-vertex-handle").count() >= 1, f"{drawing_type}/{tool}: missing shared vertex handles"
    if tool in {"closed_path", "open_path", "turning_radius", "slope_arrow"}:
        assert page.locator(".zone-arc-handle").count() >= 1, f"{drawing_type}/{tool}: missing shared arc handles"


def assert_stroke_width_honored(page, drawing_type: str, tool: str) -> None:
    if tool not in {"closed_path", "open_path", "triangle"}:
        return
    widths = page.locator(
        "#sketchOverlay path:not(.geometry-hit):not(.zone-arc-handle), "
        "#sketchOverlay polygon:not(.geometry-hit):not(.zone-arc-handle), "
        "#sketchOverlay polyline:not(.geometry-hit):not(.zone-arc-handle)"
    ).evaluate_all(
        """(nodes) => nodes
            .map((node) => Number(node.getAttribute("stroke-width") || 0))
            .filter((value) => Number.isFinite(value) && value > 0)"""
    )
    assert any(abs(value - 0.011) < 0.0005 for value in widths), (
        f"{drawing_type}/{tool}: visible stroke-width does not honor 0.011; got {widths}"
    )


def assert_hatch_fill_renders(page, drawing_type: str, tool: str) -> None:
    if tool != "closed_path":
        return
    pattern_count = page.locator("#sketchOverlay pattern[id^='hatch-']").count()
    fills = page.locator(
        "#sketchOverlay path:not(.geometry-hit):not(.zone-arc-handle), "
        "#sketchOverlay polygon:not(.geometry-hit):not(.zone-arc-handle)"
    ).evaluate_all("(nodes) => nodes.map((node) => node.getAttribute('fill') || '')")
    assert pattern_count >= 1 and any(value.startswith("url(#hatch-") for value in fills), (
        f"{drawing_type}/{tool}: hatch fill did not render as SVG pattern; patterns={pattern_count}, fills={fills}"
    )


def click_canvas_point(page, point: list[float]) -> None:
    box = page.locator("#workbenchStage").bounding_box()
    assert box, "workbench stage has no bounding box"
    page.mouse.click(box["x"] + point[0] * box["width"], box["y"] + point[1] * box["height"])
    page.wait_for_timeout(80)


def drag_locator(page, locator, dx: float = 48, dy: float = -28) -> None:
    box = locator.bounding_box()
    assert box, "drag target has no bounding box"
    x = box["x"] + box["width"] / 2
    y = box["y"] + box["height"] / 2
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x + dx, y + dy, steps=8)
    page.mouse.up()
    page.wait_for_timeout(120)


def visible_stroke_widths(page) -> list[float]:
    return page.locator(
        "#sketchOverlay circle:not(.geometry-hit):not(.geometry-vertex-handle), "
        "#sketchOverlay path:not(.geometry-hit):not(.zone-arc-handle), "
        "#sketchOverlay polygon:not(.geometry-hit):not(.zone-arc-handle), "
        "#sketchOverlay polyline:not(.geometry-hit):not(.zone-arc-handle)"
    ).evaluate_all(
        """(nodes) => nodes
            .map((node) => Number(node.getAttribute("stroke-width") || 0))
            .filter((value) => Number.isFinite(value) && value > 0)"""
    )


def assert_line_multipoint(page, drawing_type: str) -> None:
    page.click('[data-tool-id="open_path"]')
    before = page.evaluate("window.DrawingWorkbenchTest.getObjects().length")
    points = [[0.12, 0.24], [0.32, 0.31], [0.48, 0.22], [0.66, 0.36]]
    for point in points:
        click_canvas_point(page, point)
    during = page.evaluate("window.DrawingWorkbenchTest.getObjects().length")
    assert during == before, f"{drawing_type}: open_path auto-finished before explicit Finish"
    draft_points = page.locator("#sketchOverlay polyline:not(.geometry-hit)").last.get_attribute("points") or ""
    assert len(draft_points.split()) == 4, f"{drawing_type}: draft polyline does not keep 4 points: {draft_points!r}"
    page.click("#finishObject")
    page.wait_for_function(
        "(count) => window.DrawingWorkbenchTest.getObjects().length === count + 1",
        arg=before,
        timeout=10000,
    )
    created = page.evaluate("window.DrawingWorkbenchTest.getObjects().at(-1)")
    geometry = created.get("geometry") or {}
    assert geometry.get("kind") == "path" and geometry.get("closed") is False, (
        f"{drawing_type}: finished line is not an open path: {geometry}"
    )
    assert len(geometry.get("coords") or []) == 4, f"{drawing_type}: finished line did not keep 4 points: {geometry}"


def drive_path_interaction(page, drawing_type: str, tool: str) -> None:
    if drawing_type != "functional_zoning":
        page.click(f'[data-tool-id="{tool}"]')
    before = page.evaluate("window.DrawingWorkbenchTest.getObjects().length")
    closed = tool == "closed_path"
    points = (
        [[0.18, 0.16], [0.42, 0.18], [0.38, 0.42]]
        if closed
        else [[0.15, 0.58], [0.32, 0.49], [0.5, 0.6], [0.7, 0.52]]
    )
    for point in points:
        click_canvas_point(page, point)
    if closed:
        assert page.locator(".zone-close-hit").count() >= 1, f"{drawing_type}/{tool}: missing close handle"
        page.locator(".zone-close-ring").first.click()
    else:
        assert page.locator(".zone-close-hit").count() == 0, f"{drawing_type}/{tool}: open path shows close handle"
        page.click("#finishObject")
    page.wait_for_function(
        "(count) => window.DrawingWorkbenchTest.getObjects().length === count + 1",
        arg=before,
        timeout=10000,
    )
    created = page.evaluate("window.DrawingWorkbenchTest.getObjects().at(-1)")
    obj_id = created["id"]
    geometry = created.get("geometry") or {}
    assert geometry.get("kind") == "path", f"{drawing_type}/{tool}: created geometry is not path: {geometry}"
    assert geometry.get("closed") is closed, f"{drawing_type}/{tool}: closed mismatch: {geometry}"
    assert len(geometry.get("coords") or []) == len(points), f"{drawing_type}/{tool}: point count mismatch: {geometry}"
    assert page.locator(f".geometry-hit[data-object-id='{obj_id}']").count() >= 1, f"{drawing_type}/{tool}: missing hit layer"
    assert page.locator(".geometry-vertex-handle").count() >= 3, f"{drawing_type}/{tool}: missing vertex handles"
    assert page.locator(f".zone-arc-handle[data-object-id='{obj_id}']").count() >= 1, f"{drawing_type}/{tool}: missing arc handles"
    drag_locator(page, page.locator(f".zone-arc-handle[data-object-id='{obj_id}']").first)
    page.wait_for_function(
        """(id) => {
            const obj = window.DrawingWorkbenchTest.getObjects().find((o) => o.id === id);
            return !!(obj && obj.geometry && (obj.geometry.segments || []).some((seg) => seg.kind === "quadratic"));
        }""",
        arg=obj_id,
        timeout=10000,
    )
    expected_vertices = len(points)
    actual_handles = page.locator(".geometry-vertex-handle").count()
    assert actual_handles == expected_vertices, (
        f"{drawing_type}/{tool}: arc created phantom vertex handles; expected {expected_vertices}, got {actual_handles}"
    )


def drive_marker_interaction(page, drawing_type: str, tool: str) -> None:
    page.click(f'[data-tool-id="{tool}"]')
    before = page.evaluate("window.DrawingWorkbenchTest.getObjects().length")
    click_canvas_point(page, [0.56, 0.38])
    page.wait_for_function(
        "(count) => window.DrawingWorkbenchTest.getObjects().length === count + 1",
        arg=before,
        timeout=10000,
    )
    created = page.evaluate("window.DrawingWorkbenchTest.getObjects().at(-1)")
    obj_id = created["id"]
    geometry_before = created.get("geometry") or {}
    assert page.locator(f".geometry-hit[data-object-id='{obj_id}']").count() >= 1, f"{drawing_type}/{tool}: missing hit layer"
    assert page.locator(f".geometry-vertex-handle[data-vertex-object-id='{obj_id}']").count() >= 1, (
        f"{drawing_type}/{tool}: missing draggable vertex handles"
    )
    role = "circle-radius" if tool == "circle" else "triangle-vertex"
    drag_locator(page, page.locator(f".geometry-vertex-handle[data-vertex-object-id='{obj_id}'][data-vertex-role='{role}']").first)
    changed = page.evaluate("window.DrawingWorkbenchTest.getObjects().at(-1)")
    geometry_after = changed.get("geometry") or {}
    if tool == "circle":
        assert geometry_after.get("radius") != geometry_before.get("radius"), f"{drawing_type}/{tool}: radius did not change"
    else:
        assert geometry_after.get("size") != geometry_before.get("size"), f"{drawing_type}/{tool}: size did not change"
        assert geometry_after.get("rotation_deg") != geometry_before.get("rotation_deg"), (
            f"{drawing_type}/{tool}: rotation did not change"
        )
    page.eval_on_selector(
        "#styleStrokeWidth",
        """(el) => {
            el.value = "0.011";
            el.dispatchEvent(new Event("input", { bubbles: true }));
        }""",
    )
    widths = visible_stroke_widths(page)
    assert any(abs(value - 0.011) < 0.0005 for value in widths), (
        f"{drawing_type}/{tool}: selected style change did not update visible stroke width; got {widths}"
    )


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover - this is a hard gate now.
        print(f"FAIL: Playwright is required for browser smoke: {exc}", file=sys.stderr)
        return 1

    proj_dir = prepare_project()
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    server = subprocess.Popen(
        [sys.executable, str(REPO_ROOT / "_tools" / "uploader" / "server.py"), "--port", str(PORT), "--no-browser"],
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    try:
        wait_for_server()
        registry = url_json("/api/drawing/registry")
        enabled = {
            key: value
            for key, value in registry["drawings"].items()
            if value.get("status") == "enabled"
        }
        assert len(enabled) >= 10, f"expected all drawing workbenches enabled, got {sorted(enabled)}"

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 980})
            console_errors: list[str] = []
            page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
            page.on("pageerror", lambda exc: console_errors.append(str(exc)))
            page.goto(f"{BASE}/?project={TEST_PROJECT}&page=workbench&drawing=functional_zoning", wait_until="networkidle", timeout=30000)
            page.wait_for_function("window.DrawingWorkbenchTest && document.querySelectorAll('[data-drawing-type]').length >= 10", timeout=20000)
            line_multipoint_checked = False
            interaction_checked = {"closed_path": False, "open_path": False, "circle": False, "triangle": False}

            for drawing_type, info in enabled.items():
                page.click(f'[data-drawing-type="{drawing_type}"]')
                page.wait_for_function(
                    "(dt) => window.DrawingWorkbenchTest && window.DrawingWorkbenchTest.getActiveDrawingType() === dt",
                    arg=drawing_type,
                    timeout=15000,
                )
                page.wait_for_timeout(100)
                tools = list(info.get("tools") or [])
                if drawing_type == "functional_zoning":
                    assert_fz_regression(page)
                    drive_path_interaction(page, drawing_type, "closed_path")
                if drawing_type != "functional_zoning":
                    dom_tools = page.eval_on_selector_all("[data-tool-id]", "(nodes) => nodes.map((n) => n.dataset.toolId)")
                    assert sorted(dom_tools) == sorted(tools), f"{drawing_type}: DOM tools {dom_tools} != registry {tools}"
                    assert page.locator("#geometryKind").count() == 0, f"{drawing_type}: generic geometry select still visible"
                    assert page.locator("[data-style-controls='true']").count() == 1, f"{drawing_type}: missing style controls"
                    assert page.locator("[data-supporting-panel='true']").count() == 0, f"{drawing_type}: supporting panel shown before supporting tool is active"
                    assert_control_rules(page, drawing_type, tools)
                    if not line_multipoint_checked and "open_path" in tools:
                        assert_line_multipoint(page, drawing_type)
                        line_multipoint_checked = True
                    for interaction_tool in ["closed_path", "open_path", "circle", "triangle"]:
                        if not interaction_checked[interaction_tool] and interaction_tool in tools:
                            if interaction_tool in {"closed_path", "open_path"}:
                                drive_path_interaction(page, drawing_type, interaction_tool)
                            else:
                                drive_marker_interaction(page, drawing_type, interaction_tool)
                            interaction_checked[interaction_tool] = True

                before = page.evaluate("window.DrawingWorkbenchTest.getObjects().length")
                creatable_tools = [tool for tool in tools if tool != "supporting_images"]
                for tool in creatable_tools:
                    if drawing_type != "functional_zoning":
                        page.click(f'[data-tool-id="{tool}"]')
                    if drawing_type != "functional_zoning" and tool in {"closed_path", "open_path", "triangle"}:
                        page.eval_on_selector(
                            "#styleStrokeWidth",
                            """(el) => {
                                el.value = "0.011";
                                el.dispatchEvent(new Event("input", { bubbles: true }));
                            }""",
                        )
                    if drawing_type != "functional_zoning" and tool == "closed_path":
                        page.click('[data-style-segment="fill_mode"][data-style-value="hatch"]')
                    page.evaluate(
                        "({tool, pts}) => window.DrawingWorkbenchTest.createObject(tool, pts)",
                        {"tool": tool, "pts": tool_points(tool)},
                    )
                    assert_shared_interaction_dom(page, drawing_type, tool)
                    if drawing_type != "functional_zoning":
                        assert_stroke_width_honored(page, drawing_type, tool)
                        assert_hatch_fill_renders(page, drawing_type, tool)
                after_objects = page.evaluate("window.DrawingWorkbenchTest.getObjects()")
                assert len(after_objects) == before + len(creatable_tools), (
                    f"{drawing_type}: object count did not increase by tools; before={before}, after={len(after_objects)}, tools={creatable_tools}"
                )
                assert_no_bad_kinds(after_objects, drawing_type)

                with page.expect_response(lambda r: "/api/drawing/save" in r.url and r.status == 200, timeout=15000):
                    page.click("#workbenchSave")
                with page.expect_response(lambda r: "/api/drawing/load" in r.url and r.status == 200, timeout=15000):
                    page.click("#workbenchLoad")
                page.wait_for_function(
                    "(count) => window.DrawingWorkbenchTest.getObjects().length >= count",
                    arg=len(after_objects),
                    timeout=15000,
                )
                reloaded = page.evaluate("window.DrawingWorkbenchTest.getObjects()")
                assert len(reloaded) >= len(after_objects), f"{drawing_type}: objects disappeared after reload"
                assert_no_bad_kinds(reloaded, drawing_type)
                print(f"OK {drawing_type}: tools={tools}, objects={len(reloaded)}")

            browser.close()

        assert not console_errors, "console/page errors:\n" + "\n".join(console_errors)
        print("BROWSER_SMOKE_PASSED")
        return 0

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

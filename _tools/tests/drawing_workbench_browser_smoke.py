#!/usr/bin/env python3
"""Hard browser smoke gate for the drawing workbench frontend."""
from __future__ import annotations

import json
import math
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
    if tool_id == "text_label":
        return [[0.62, 0.22]]
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
        assert kind in {"path", "circle", "triangle", "text"}, f"{drawing_type}: illegal geometry.kind {kind!r}"
        assert kind not in {"closed_path", "open_path"}, f"{drawing_type}: leaked tool id {kind!r}"
        if obj.get("type") == "turning_radius":
            assert ((obj.get("style_hints") or {}).get("label_box") or {}).get("enabled"), "turning_radius missing label_box"
        if obj.get("type") == "slope_arrow":
            assert ((obj.get("style_hints") or {}).get("inline_text") or {}).get("enabled"), "slope_arrow missing inline_text"


def assert_preset_not_pale(registry: dict) -> None:
    old_colors = {"#DCE8C8", "#7AA35A"}
    objects = registry.get("objects") or {}
    for object_type, info in objects.items():
        if object_type == "functional_zone":
            continue
        style = info.get("default_style") or {}
        stroke = str(style.get("stroke_color") or "").upper()
        fill = str(style.get("fill_color") or "").upper()
        fill_mode = style.get("fill_mode")
        assert stroke not in old_colors, f"{object_type}: default stroke still uses old pale color {stroke}"
        if fill_mode != "none" and object_type != "text_label":
            assert fill not in old_colors, f"{object_type}: default fill still uses old pale color {fill}"
    assert (objects.get("text_label", {}).get("default_style") or {}).get("stroke_color") == "#1A1A1A", (
        "text_label default should be deep readable gray"
    )


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
        "#sketchOverlay ellipse:not(.geometry-hit):not(.geometry-vertex-handle):not(.zone-close-hit):not(.zone-close-ring), "
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
    role = "circle-radius" if tool == "circle" else "triangle-size"
    drag_locator(page, page.locator(f".geometry-vertex-handle[data-vertex-object-id='{obj_id}'][data-vertex-role='{role}']").first)
    changed = page.evaluate("window.DrawingWorkbenchTest.getObjects().at(-1)")
    geometry_after = changed.get("geometry") or {}
    if tool == "circle":
        assert geometry_after.get("radius") != geometry_before.get("radius"), f"{drawing_type}/{tool}: radius did not change"
    else:
        assert geometry_after.get("size") != geometry_before.get("size"), f"{drawing_type}/{tool}: size did not change"
        assert geometry_after.get("rotation_deg") == geometry_before.get("rotation_deg"), (
            f"{drawing_type}/{tool}: size handle changed rotation"
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


def assert_triangle_rotate_no_scale(page, drawing_type: str) -> None:
    page.click('[data-tool-id="triangle"]')
    created = page.evaluate(
        """() => window.DrawingWorkbenchTest.createObject("triangle", [[0.78, 0.76]])"""
    )
    obj_id = created["id"]
    geometry_before = created.get("geometry") or {}
    size_handles = page.locator(
        f".geometry-vertex-handle[data-vertex-object-id='{obj_id}'][data-vertex-role='triangle-size']"
    ).count()
    rotate_handles = page.locator(
        f".geometry-vertex-handle[data-vertex-object-id='{obj_id}'][data-vertex-role='triangle-rotate']"
    ).count()
    assert size_handles == 3, f"{drawing_type}: triangle should expose 3 corner resize handles, got {size_handles}"
    assert rotate_handles == 1, f"{drawing_type}: triangle should expose 1 floating rotate handle, got {rotate_handles}"
    rotate_icon = page.locator(
        f".geometry-rotate-icon[data-vertex-object-id='{obj_id}'][data-vertex-role='triangle-rotate'] path"
    ).count()
    assert rotate_icon >= 1, f"{drawing_type}: triangle rotate handle should render a circular-arrow icon"
    drag_locator(page, page.locator(f".geometry-vertex-handle[data-vertex-object-id='{obj_id}'][data-vertex-role='triangle-rotate']").first)
    changed = page.evaluate("window.DrawingWorkbenchTest.getObjects().at(-1)")
    geometry_after = changed.get("geometry") or {}
    assert geometry_after.get("rotation_deg") != geometry_before.get("rotation_deg"), (
        f"{drawing_type}: triangle rotate handle did not change rotation"
    )
    assert abs(float(geometry_after.get("size")) - float(geometry_before.get("size"))) < 1e-4, (
        f"{drawing_type}: triangle rotate handle changed size; before={geometry_before}, after={geometry_after}"
    )


def assert_circle_round(page, drawing_type: str) -> None:
    page.click('[data-tool-id="circle"]')
    page.evaluate("""() => window.DrawingWorkbenchTest.createObject("circle", [[0.72, 0.3]])""")
    ellipse = page.locator("#sketchOverlay ellipse:not(.geometry-hit):not(.geometry-vertex-handle)").last
    rx = float(ellipse.get_attribute("rx") or 0)
    ry = float(ellipse.get_attribute("ry") or 0)
    stage_ratio = page.locator("#workbenchStage").evaluate(
        "(node) => node.getBoundingClientRect().width / node.getBoundingClientRect().height"
    )
    assert rx > 0 and ry > 0, f"{drawing_type}: circle did not render as ellipse with rx/ry"
    assert abs((ry / rx) - stage_ratio) / stage_ratio < 0.05, (
        f"{drawing_type}: circle aspect compensation wrong; rx={rx}, ry={ry}, stage_ratio={stage_ratio}"
    )


def assert_slope_text_upright(page, drawing_type: str) -> None:
    cases = [
        ("SMOKE-SLOPE-LR", [[0.24, 0.32], [0.66, 0.32]]),
        ("SMOKE-SLOPE-RL", [[0.66, 0.42], [0.24, 0.42]]),
        ("SMOKE-SLOPE-DIAG", [[0.72, 0.28], [0.30, 0.66]]),
    ]
    page.click('[data-tool-id="slope_arrow"]')
    for label, points in cases:
        page.eval_on_selector(
            "#objectLabel",
            """(el, value) => {
                el.value = value;
                el.dispatchEvent(new Event("input", { bubbles: true }));
            }""",
            label,
        )
        page.evaluate(
            "({ pts }) => window.DrawingWorkbenchTest.createObject('slope_arrow', pts)",
            {"pts": points},
        )
        angle = page.evaluate(
            """(label) => {
                const node = [...document.querySelectorAll("#sketchOverlay text")]
                    .find((item) => item.textContent.trim() === label);
                if (!node) throw new Error(`missing slope text ${label}`);
                const match = /rotate\\(([-0-9.]+)/.exec(node.getAttribute("transform") || "");
                return match ? Number(match[1]) : 0;
            }""",
            label,
        )
        normalized = ((float(angle) + 180) % 360) - 180
        assert -90 <= normalized <= 90, (
            f"{drawing_type}: slope text {label} is upside down; angle={angle}, normalized={normalized}"
        )


def assert_slope_text_above(page, drawing_type: str) -> None:
    cases = [
        ("SMOKE-SLOPE-ABOVE-LR", [[0.24, 0.30], [0.66, 0.30]]),
        ("SMOKE-SLOPE-ABOVE-RL", [[0.66, 0.42], [0.24, 0.42]]),
        ("SMOKE-SLOPE-ABOVE-DIAG", [[0.72, 0.28], [0.30, 0.66]]),
    ]
    page.click('[data-tool-id="slope_arrow"]')
    for label, points in cases:
        page.eval_on_selector(
            "#objectLabel",
            """(el, value) => {
                el.value = value;
                el.dispatchEvent(new Event("input", { bubbles: true }));
            }""",
            label,
        )
        page.evaluate(
            "({ pts }) => window.DrawingWorkbenchTest.createObject('slope_arrow', pts)",
            {"pts": points},
        )
        text_y = float(page.locator("#sketchOverlay text", has_text=label).last.get_attribute("y") or 0)
        mid_y = (points[0][1] + points[1][1]) / 2
        assert text_y < mid_y, f"{drawing_type}: slope text {label} is not above line; text_y={text_y}, mid_y={mid_y}"


def assert_text_tool(page, drawing_type: str) -> None:
    if page.locator('[data-tool-id="open_path"]').count() >= 1:
        page.click('[data-tool-id="open_path"]')
        page.eval_on_selector(
            "#objectLabel",
            """(el) => {
                el.value = "AUTO-LINE-LABEL-SHOULD-NOT-RENDER";
                el.dispatchEvent(new Event("input", { bubbles: true }));
            }""",
        )
        page.evaluate(
            """() => window.DrawingWorkbenchTest.createObject("open_path", [[0.18, 0.78], [0.46, 0.78]])"""
        )
        auto_labels = page.locator("#sketchOverlay text").evaluate_all(
            """(nodes) => nodes
                .map((node) => node.textContent.trim())
                .filter((text) => text === "AUTO-LINE-LABEL-SHOULD-NOT-RENDER")"""
        )
        assert not auto_labels, f"{drawing_type}: open_path still renders automatic plain label"

    assert page.locator('[data-tool-id="text_label"]').count() == 1, f"{drawing_type}: missing text_label tool"
    text_button = page.locator('[data-tool-id="text_label"]').first
    assert text_button.is_visible(), f"{drawing_type}: text_label tool is not visible"
    assert text_button.locator(".tool-icon").count() == 1, f"{drawing_type}: text_label tool lacks recognizable T icon"
    assert text_button.evaluate("(node) => node.scrollWidth <= node.clientWidth + 1"), (
        f"{drawing_type}: text_label button content is clipped"
    )
    page.click('[data-tool-id="text_label"]')
    page.eval_on_selector(
        "#textLabelContent",
        """(el) => {
            el.value = "可拖动文字";
            el.dispatchEvent(new Event("input", { bubbles: true }));
        }""",
    )
    created = page.evaluate(
        """() => window.DrawingWorkbenchTest.createObject("text_label", [[0.58, 0.58]])"""
    )
    assert created.get("type") == "text_label", f"{drawing_type}: text tool created wrong type {created}"
    geometry = created.get("geometry") or {}
    assert geometry.get("kind") == "text" and geometry.get("coords"), f"{drawing_type}: text tool geometry invalid {geometry}"
    obj_id = created["id"]
    assert page.locator("#sketchOverlay text", has_text="可拖动文字").count() >= 1, f"{drawing_type}: text object did not render"
    before = geometry["coords"][0]
    drag_locator(page, page.locator(f".geometry-vertex-handle[data-vertex-object-id='{obj_id}'][data-vertex-role='text-anchor']").first)
    after = page.evaluate(
        """(id) => {
            const obj = window.DrawingWorkbenchTest.getObjects().find((item) => item.id === id);
            return obj && obj.geometry && obj.geometry.coords && obj.geometry.coords[0];
        }""",
        obj_id,
    )
    assert after and after != before, f"{drawing_type}: text anchor drag did not move coords; before={before}, after={after}"


def assert_legend_non_fz(page, drawing_type: str) -> None:
    legend = page.locator("#zoneLegendPreview")
    assert legend.count() == 1, f"{drawing_type}: missing legend preview"
    text = legend.text_content() or ""
    assert "暂无功能分区" not in text, f"{drawing_type}: non-FZ legend still shows functional-zoning empty copy"
    entries = legend.locator(".zone-legend-item").count()
    assert entries >= 2, f"{drawing_type}: expected at least 2 legend entries, got {entries}; text={text!r}"


def assert_line_legend_straight(page, drawing_type: str) -> None:
    swatches = page.locator("#zoneLegendPreview .zone-legend-swatch")
    has_line = swatches.locator("line").count() >= 1
    curved_paths = swatches.locator("path").evaluate_all(
        """nodes => nodes.map((node) => node.getAttribute("d") || "").filter((d) => /C|Q/.test(d))"""
    )
    assert has_line, f"{drawing_type}: line legend swatch does not render a straight <line>"
    assert not curved_paths, f"{drawing_type}: line legend swatch still uses curved path(s): {curved_paths}"


def assert_non_arrow_line_presets_scoped(page, drawing_type: str) -> None:
    if drawing_type not in {"planting_design", "landscape_analysis"}:
        return
    if page.locator('[data-tool-id="open_path"]').count() == 0:
        return
    page.click('[data-tool-id="open_path"]')
    options = page.eval_on_selector_all("#objectType option", "(nodes) => nodes.map((node) => node.value)")
    forbidden_preset_ids = [
        "vehicle-orange-solid",
        "pedestrian-cobalt-solid",
        "underground-blue-dashed",
        "fire-red-line",
        "runoff-deep-blue",
    ]
    for object_type in options or [""]:
        if object_type:
            page.select_option("#objectType", object_type)
        assert page.locator("#styleStartArrow").count() == 0, f"{drawing_type}/{object_type}: start arrow control should be hidden"
        assert page.locator("#styleEndArrow").count() == 0, f"{drawing_type}/{object_type}: end arrow control should be hidden"
        for preset_id in forbidden_preset_ids:
            assert page.locator(f'[data-style-preset-apply="{preset_id}"]').count() == 0, (
                f"{drawing_type}/{object_type}: arrow preset {preset_id} leaked into non-arrow line tool"
            )
        assert page.locator("[data-style-preset-swatch] polygon").count() == 0, (
            f"{drawing_type}/{object_type}: preset preview should not draw arrowhead polygons"
        )


def assert_dash_scale(page, drawing_type: str) -> None:
    page.click('[data-tool-id="open_path"]')
    page.click('[data-style-segment="stroke_style"][data-style-value="dashed"]')
    assert page.locator("#styleDashScale").count() == 1, f"{drawing_type}: missing dash_scale control for dashed line"
    page.eval_on_selector(
        "#styleDashScale",
        """(el) => {
            el.value = "2";
            el.dispatchEvent(new Event("input", { bubbles: true }));
        }""",
    )
    created = page.evaluate(
        """() => window.DrawingWorkbenchTest.createObject("open_path", [[0.18, 0.72], [0.72, 0.74]])"""
    )
    obj_id = created["id"]
    shape = page.locator("#sketchOverlay polyline:not(.geometry-hit):not(.zone-arc-handle)").last
    dash_large = shape.get_attribute("stroke-dasharray")
    assert dash_large == "0.028 0.02", f"{drawing_type}: dash_scale=2 did not update dasharray, got {dash_large!r}"
    page.eval_on_selector(
        "#styleDashScale",
        """(el) => {
            el.value = "0.5";
            el.dispatchEvent(new Event("input", { bubbles: true }));
        }""",
    )
    dash_small = shape.get_attribute("stroke-dasharray")
    assert dash_small == "0.007 0.005", f"{drawing_type}: dash_scale=0.5 did not update selected dasharray, got {dash_small!r}"


def _parse_svg_points(value: str) -> list[list[float]]:
    points: list[list[float]] = []
    for item in (value or "").strip().split():
        xy = item.split(",")
        if len(xy) == 2:
            points.append([float(xy[0]), float(xy[1])])
    return points


def _screen_angle_deg(a: list[float], b: list[float], width: float, height: float) -> float:
    return math.degrees(math.atan2((b[1] - a[1]) * height, (b[0] - a[0]) * width))


def _angle_delta(a: float, b: float) -> float:
    return abs(((a - b + 180) % 360) - 180)


def assert_arrow_geometry(page, drawing_type: str) -> None:
    page.click('[data-tool-id="open_path"]')
    if page.locator("#objectType").count():
        page.select_option("#objectType", "vehicle_flow")
    points = [[0.20, 0.70], [0.72, 0.34]]
    created = page.evaluate(
        """(pts) => window.DrawingWorkbenchTest.createObject("open_path", pts)""",
        points,
    )
    obj_id = created["id"]
    stage = page.locator("#workbenchStage").evaluate(
        """node => {
            const rect = node.getBoundingClientRect();
            return { width: rect.width, height: rect.height };
        }"""
    )
    visible_points = _parse_svg_points(
        page.locator("#sketchOverlay polyline:not(.geometry-hit):not(.zone-arc-handle)").last.get_attribute("points") or ""
    )
    assert len(visible_points) >= 2, f"{drawing_type}: arrow line did not render as visible polyline"
    original_end = points[-1]
    rendered_end = visible_points[-1]
    full_len = math.hypot(
        (original_end[0] - points[0][0]) * stage["width"],
        (original_end[1] - points[0][1]) * stage["height"],
    )
    trimmed_len = math.hypot(
        (rendered_end[0] - points[0][0]) * stage["width"],
        (rendered_end[1] - points[0][1]) * stage["height"],
    )
    gap_to_tip = math.hypot(
        (original_end[0] - rendered_end[0]) * stage["width"],
        (original_end[1] - rendered_end[1]) * stage["height"],
    )
    assert trimmed_len < full_len and gap_to_tip > 8, (
        f"{drawing_type}: line endpoint was not trimmed for arrowhead; rendered_end={rendered_end}, original_end={original_end}"
    )
    arrow_points = _parse_svg_points(
        page.locator(f"#sketchOverlay polygon[data-object-id='{obj_id}']").first.get_attribute("points") or ""
    )
    assert len(arrow_points) == 3, f"{drawing_type}: missing arrowhead triangle"
    tip, p2, p3 = arrow_points
    base_mid = [(p2[0] + p3[0]) / 2, (p2[1] + p3[1]) / 2]
    line_angle = _screen_angle_deg(points[0], original_end, stage["width"], stage["height"])
    arrow_angle = _screen_angle_deg(base_mid, tip, stage["width"], stage["height"])
    assert _angle_delta(line_angle, arrow_angle) <= 5, (
        f"{drawing_type}: arrowhead angle off; line={line_angle:.2f}, arrow={arrow_angle:.2f}, points={arrow_points}"
    )


def assert_labelbox_white_draggable(page, drawing_type: str) -> None:
    page.click('[data-tool-id="turning_radius"]')
    page.eval_on_selector(
        "#objectLabel",
        """(el) => {
            el.value = "R=9M";
            el.dispatchEvent(new Event("input", { bubbles: true }));
        }""",
    )
    created = page.evaluate(
        """() => window.DrawingWorkbenchTest.createObject("turning_radius", [[0.26, 0.64], [0.62, 0.42]])"""
    )
    obj_id = created["id"]
    color = (created.get("style_hints") or {}).get("stroke_color", "").upper()
    rect = page.locator(f"#sketchOverlay rect[data-object-id='{obj_id}']").first
    assert rect.get_attribute("fill") == "#FFFFFF", f"{drawing_type}: label_box fill is not white"
    assert rect.get_attribute("stroke") in (None, ""), f"{drawing_type}: label_box should not have a border"
    assert (rect.get_attribute("rx") or "0") in ("0", "0.0"), f"{drawing_type}: label_box should have square corners"
    opacity = float(rect.get_attribute("fill-opacity") or 0)
    assert 0.5 <= opacity <= 0.6, f"{drawing_type}: label_box opacity should be about 0.55, got {opacity}"
    text_fill = page.locator("#sketchOverlay text", has_text="R=9M").last.get_attribute("fill")
    assert (text_fill or "").upper() == color, f"{drawing_type}: label_box text color {text_fill} != stroke {color}"
    handle = page.locator(f".geometry-vertex-handle[data-vertex-object-id='{obj_id}'][data-vertex-role='labelbox']").first
    assert handle.count() == 1, f"{drawing_type}: label_box drag handle missing"
    before = (created.get("style_hints") or {}).get("label_box", {}).get("offset")
    drag_locator(page, handle, dx=56, dy=-34)
    after = page.evaluate(
        """(id) => {
            const obj = window.DrawingWorkbenchTest.getObjects().find((item) => item.id === id);
            return obj && obj.style_hints && obj.style_hints.label_box && obj.style_hints.label_box.offset;
        }""",
        obj_id,
    )
    assert after and after != before, f"{drawing_type}: label_box offset did not change after drag; before={before}, after={after}"


def assert_label_persists(page, drawing_type: str) -> None:
    if page.locator('[data-tool-id="triangle"]').count() == 0:
        return
    label = "\u4e3b\u5165\u53e3"
    page.click('[data-tool-id="triangle"]')
    page.fill("#objectLabel", label)
    created = page.evaluate(
        "({tool, pts}) => window.DrawingWorkbenchTest.createObject(tool, pts)",
        {"tool": "triangle", "pts": tool_points("triangle")},
    )
    assert created.get("label") == label, f"{drawing_type}: created label not set"
    page.eval_on_selector(
        "#styleFillColor",
        """(el) => {
            el.value = "#D94B35";
            el.dispatchEvent(new Event("change", { bubbles: true }));
        }""",
    )
    page.wait_for_timeout(50)
    obj = page.evaluate(
        "(id) => window.DrawingWorkbenchTest.getObjects().find((o) => o.id === id)",
        created["id"],
    )
    assert obj and obj.get("label") == label, f"{drawing_type}: label lost after style change"
    input_value = page.eval_on_selector("#objectLabel", "(el) => el.value")
    assert input_value == label, f"{drawing_type}: label input did not rehydrate, got {input_value!r}"


def _legend_entries(page) -> list[dict[str, str]]:
    return page.eval_on_selector_all(
        ".zone-legend-item",
        """(nodes) => nodes.map((node) => ({
            label: (node.querySelector(".zone-legend-label") || {}).textContent?.trim() || "",
            count: (node.querySelector(".zone-legend-count") || {}).textContent?.trim() || "",
        }))""",
    )


def _polygon_area(points: list[list[float]]) -> float:
    area = 0.0
    for index, point in enumerate(points):
        next_point = points[(index + 1) % len(points)]
        area += point[0] * next_point[1] - next_point[0] * point[1]
    return abs(area) / 2.0


def assert_legend_by_label(page, drawing_type: str) -> None:
    if page.locator('[data-tool-id="open_path"]').count() == 0 or page.locator("#objectType").count() == 0:
        return
    label = "\u8f66\u884c"
    page.click('[data-tool-id="open_path"]')
    options = page.eval_on_selector_all("#objectType option", "(nodes) => nodes.map((node) => node.value)")
    assert len(options) >= 2, f"{drawing_type}: need at least two object types for legend grouping"
    created_ids: list[str] = []
    for object_type in options[:2]:
        page.select_option("#objectType", object_type)
        page.fill("#objectLabel", label)
        page.eval_on_selector(
            "#styleStrokeColor",
            """(el) => {
                el.value = "#B23A2E";
                el.dispatchEvent(new Event("change", { bubbles: true }));
            }""",
        )
        page.eval_on_selector(
            "#styleStrokeWidth",
            """(el) => {
                el.value = "0.006";
                el.dispatchEvent(new Event("input", { bubbles: true }));
            }""",
        )
        created = page.evaluate(
            "({tool, pts}) => window.DrawingWorkbenchTest.createObject(tool, pts)",
            {"tool": "open_path", "pts": tool_points("open_path")},
        )
        created_ids.append(created["id"])
    page.wait_for_timeout(50)
    matching = [entry for entry in _legend_entries(page) if entry["label"] == label]
    assert len(matching) == 1, f"{drawing_type}: same style+label legend should merge once, got {matching}"
    assert matching[0]["count"] == "x 2", f"{drawing_type}: merged legend count should be x 2, got {matching}"

    page.click(f'.object-row[data-object-id="{created_ids[0]}"]')
    page.select_option("#objectType", options[0])
    page.eval_on_selector(
        "#styleStrokeWidth",
        """(el) => {
            el.value = "0.012";
            el.dispatchEvent(new Event("input", { bubbles: true }));
        }""",
    )
    page.wait_for_timeout(50)
    split = [entry for entry in _legend_entries(page) if entry["label"] == label]
    assert len(split) == 2, f"{drawing_type}: changed style should split legend into two rows, got {split}"


def assert_arrow_scales(page, drawing_type: str) -> None:
    if page.locator('[data-tool-id="open_path"]').count() == 0:
        return
    page.click('[data-tool-id="open_path"]')
    if page.locator("#objectType").count():
        options = page.eval_on_selector_all("#objectType option", "(nodes) => nodes.map((node) => node.value)")
        if options:
            page.select_option("#objectType", options[0])
    areas: list[float] = []
    for width in ("0.002", "0.012"):
        page.eval_on_selector(
            "#styleStrokeWidth",
            """(el, value) => {
                el.value = value;
                el.dispatchEvent(new Event("input", { bubbles: true }));
            }""",
            width,
        )
        if page.locator("#styleEndArrow").count():
            page.eval_on_selector(
                "#styleEndArrow",
                """(el) => {
                    if (!el.checked) {
                        el.checked = true;
                        el.dispatchEvent(new Event("input", { bubbles: true }));
                    }
                }""",
            )
        created = page.evaluate(
            "({tool, pts}) => window.DrawingWorkbenchTest.createObject(tool, pts)",
            {"tool": "open_path", "pts": [[0.18, 0.55], [0.74, 0.56]]},
        )
        points = _parse_svg_points(
            page.locator(f"#sketchOverlay polygon[data-object-id='{created['id']}']").last.get_attribute("points") or ""
        )
        assert len(points) == 3, f"{drawing_type}: missing arrowhead for width {width}"
        areas.append(_polygon_area(points))
    assert areas[1] > areas[0] * 4, f"{drawing_type}: thick arrowhead should be much larger; areas={areas}"


def assert_move_and_paste(page, drawing_type: str) -> None:
    if page.locator('[data-tool-id="open_path"]').count() == 0:
        return
    page.click('[data-tool-id="open_path"]')
    created = page.evaluate(
        "({tool, pts}) => window.DrawingWorkbenchTest.createObject(tool, pts)",
        {"tool": "open_path", "pts": [[0.22, 0.32], [0.48, 0.34]]},
    )
    obj_id = created["id"]
    before = [point[:] for point in (created.get("geometry") or {}).get("coords", [])]
    stage = page.locator("#workbenchStage").bounding_box()
    assert stage, f"{drawing_type}: stage missing for move test"
    start = [
        before[0][0] + (before[1][0] - before[0][0]) * 0.25,
        before[0][1] + (before[1][1] - before[0][1]) * 0.25,
    ]
    sx = stage["x"] + start[0] * stage["width"]
    sy = stage["y"] + start[1] * stage["height"]
    page.mouse.move(sx, sy)
    page.mouse.down()
    page.mouse.move(sx + 72, sy + 38, steps=8)
    page.mouse.up()
    page.wait_for_timeout(120)
    moved = page.evaluate(
        "(id) => window.DrawingWorkbenchTest.getObjects().find((obj) => obj.id === id)",
        obj_id,
    )
    moved_coords = (moved.get("geometry") or {}).get("coords", [])
    assert len(moved_coords) == len(before) >= 2, f"{drawing_type}: moved object coords missing"
    dx = moved_coords[0][0] - before[0][0]
    dy = moved_coords[0][1] - before[0][1]
    assert abs(dx) > 0.02 and abs(dy) > 0.02, f"{drawing_type}: drag did not move object enough; dx={dx}, dy={dy}"
    for old, new in zip(before, moved_coords):
        assert abs((new[0] - old[0]) - dx) < 0.002 and abs((new[1] - old[1]) - dy) < 0.002, (
            f"{drawing_type}: drag did not translate all coordinates uniformly"
        )

    count_before = page.evaluate("window.DrawingWorkbenchTest.getObjects().length")
    page.keyboard.press("Control+C")
    page.keyboard.press("Control+V")
    page.wait_for_timeout(100)
    objects = page.evaluate("window.DrawingWorkbenchTest.getObjects()")
    assert len(objects) == count_before + 1, f"{drawing_type}: paste should add one object"
    pasted = objects[-1]
    assert pasted["id"] != obj_id, f"{drawing_type}: pasted object should get a new id"
    pasted_coords = (pasted.get("geometry") or {}).get("coords", [])
    assert len(pasted_coords) == len(moved_coords), f"{drawing_type}: pasted coords missing"
    assert abs((pasted_coords[0][0] - moved_coords[0][0]) - 0.02) < 0.004, (
        f"{drawing_type}: pasted object x offset wrong"
    )
    assert abs((pasted_coords[0][1] - moved_coords[0][1]) - 0.02) < 0.004, (
        f"{drawing_type}: pasted object y offset wrong"
    )


def assert_style_presets(page, drawing_type: str) -> None:
    if page.locator('[data-tool-id="open_path"]').count() == 0:
        return
    page.click('[data-tool-id="open_path"]')
    assert page.locator("[data-style-presets='true']").count() == 1, f"{drawing_type}: style presets panel missing"
    assert page.locator("#stylePresetImportFile").count() == 0, f"{drawing_type}: preset import picker should not render"
    assert page.locator("[data-style-preset-apply][data-preset-source='repo']").count() >= 1, (
        f"{drawing_type}: repo presets missing"
    )
    assert page.locator("[data-style-preset-delete]").count() >= 1, f"{drawing_type}: repo presets should be deletable"
    assert page.locator("[data-style-preset-swatch]").count() >= 1, f"{drawing_type}: preset swatches missing"
    page.eval_on_selector(
        "#styleStrokeColor",
        """(el) => {
            el.value = "#123456";
            el.dispatchEvent(new Event("change", { bubbles: true }));
        }""",
    )
    page.fill("#stylePresetName", "Smoke preset")
    page.click("#saveStylePreset")
    page.wait_for_function(
        "() => [...document.querySelectorAll('[data-style-preset-apply]')].some((node) => node.dataset.presetName === 'Smoke preset')",
        timeout=10000,
    )
    stored = page.evaluate(
        "() => fetch('/api/drawing/style-presets').then((r) => r.json())"
    )
    encoded = json.dumps(stored, ensure_ascii=False)
    assert "Smoke preset" in encoded and "#123456" in encoded, f"{drawing_type}: preset not saved to repo JSON: {stored}"
    page.eval_on_selector(
        "#styleStrokeColor",
        """(el) => {
            el.value = "#654321";
            el.dispatchEvent(new Event("change", { bubbles: true }));
        }""",
    )
    page.click("[data-style-preset-apply][data-preset-name='Smoke preset']")
    value = page.eval_on_selector("#styleStrokeColor", "(el) => el.value.toUpperCase()")
    assert value == "#123456", f"{drawing_type}: applying saved preset did not restore color, got {value}"
    page.evaluate("() => window.DrawingWorkbenchTest.reloadStylePresets()")
    page.click(f'[data-drawing-type="{drawing_type}"]')
    page.click('[data-tool-id="open_path"]')
    assert page.locator("[data-style-preset-apply][data-preset-name='Smoke preset']").count() == 1, (
        f"{drawing_type}: user preset did not reload from repo JSON"
    )
    page.evaluate(
        "({tool, pts}) => window.DrawingWorkbenchTest.createObject(tool, pts)",
        {"tool": "open_path", "pts": [[0.2, 0.28], [0.5, 0.3]]},
    )


def assert_functional_zone_style_presets(page) -> None:
    assert page.locator("[data-style-presets='true']").count() == 1, "functional_zoning: style presets panel missing"
    assert page.locator("#stylePresetImportFile").count() == 0, "functional_zoning: preset import picker should not render"
    assert page.locator("[data-style-preset-apply][data-preset-source='repo']").count() >= 1, (
        "functional_zoning: repo presets missing"
    )
    assert page.locator("[data-style-preset-delete]").count() >= 1, "functional_zoning: repo presets should be deletable"
    page.eval_on_selector(
        "#styleFillColor",
        """(el) => {
            el.value = "#ABCDEF";
            el.dispatchEvent(new Event("change", { bubbles: true }));
        }""",
    )
    page.fill("#stylePresetName", "FZ smoke preset")
    page.click("#saveStylePreset")
    page.wait_for_function(
        "() => [...document.querySelectorAll('[data-style-preset-apply]')].some((node) => node.dataset.presetName === 'FZ smoke preset')",
        timeout=10000,
    )
    page.eval_on_selector(
        "#styleFillColor",
        """(el) => {
            el.value = "#654321";
            el.dispatchEvent(new Event("change", { bubbles: true }));
        }""",
    )
    page.click("[data-style-preset-apply][data-preset-name='FZ smoke preset']")
    value = page.eval_on_selector("#styleFillColor", "(el) => el.value.toUpperCase()")
    assert value == "#ABCDEF", f"functional_zoning: applying saved preset did not restore fill color, got {value}"


def assert_ppt_preview_basics(page) -> None:
    text = "PPT smoke text"
    page.fill("#pptSlideText", text)
    page.click("#savePptSlideText")
    page.wait_for_function(
        """({project, expected}) =>
            fetch(`/api/drawing/deck-layout?project=${project}`)
              .then((r) => r.json())
              .then((data) => data.layout.slides.functional_zoning.text === expected)
        """,
        arg={"project": TEST_PROJECT, "expected": text},
        timeout=10000,
    )
    page.click("#togglePptPreview")
    assert page.locator("#pptPreviewPanel").is_visible(), "PPT preview panel should become visible"
    box = page.locator("#pptSlidePreview").bounding_box()
    assert box and abs((box["width"] / box["height"]) - (16 / 9)) < 0.03, f"PPT slide ratio should be 16:9, got {box}"
    assert page.locator("[data-ppt-drawing-frame='true']").count() == 1, "PPT preview should render one global drawing frame"
    assert page.locator("[data-ppt-element='text']", has_text=text).count() == 1, "PPT preview should render saved slide text"
    media = page.locator("[data-ppt-drawing-frame='true'] [data-ppt-drawing-media='true']")
    assert media.count() == 1, "PPT preview should mark drawing media for contain checks"
    object_fit = media.evaluate("(node) => getComputedStyle(node).objectFit")
    assert object_fit == "contain", f"PPT drawing preview should use object-fit: contain, got {object_fit}"
    assert_title_and_accent_global(page)
    dialogs: list[str] = []

    def handle_dialog(dialog) -> None:
        dialogs.append(dialog.message)
        dialog.dismiss()

    page.on("dialog", handle_dialog)
    page.click('[data-ppt-template="drawing_right"]')
    page.wait_for_timeout(100)
    assert dialogs and "全部图纸页" in dialogs[-1], f"global frame warning missing expected copy: {dialogs!r}"
    page.remove_listener("dialog", handle_dialog)
    assert_layout_warnings_visible(page)
    assert_reflow_guard(page)
    assert not page.locator("#pptPreviewPanel").is_visible(), "PPT preview panel should hide when returning to drawing mode"


def assert_layout_warnings_visible(page) -> None:
    page.evaluate(
        """async (project) => {
            const current = await fetch(`/api/drawing/deck-layout?project=${project}`).then((r) => r.json());
            const layout = current.layout;
            layout.slides.functional_zoning.layout_warnings = ['warning smoke: info column compressed'];
            await fetch('/api/drawing/deck-layout/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ project, layout }),
            });
        }""",
        TEST_PROJECT,
    )
    page.reload(wait_until="domcontentloaded")
    page.wait_for_function("window.DrawingWorkbenchTest && document.querySelectorAll('[data-drawing-type]').length >= 10", timeout=20000)
    page.click("#togglePptPreview")
    assert page.locator("[data-ppt-layout-warning='true']", has_text="warning smoke").count() == 1, (
        "PPT preview should surface layout_warnings"
    )
    page.click("#togglePptPreview")
    page.wait_for_function("document.querySelector('#pptPreviewPanel')?.hidden === true", timeout=5000)


def assert_title_and_accent_global(page) -> None:
    heading_text = "车行流线设置：主入口与慢行系统分离。"
    page.fill("#pptSlideText", heading_text)
    page.click("#savePptSlideText")
    page.wait_for_function(
        """({project, expected}) =>
            fetch(`/api/drawing/deck-layout?project=${project}`)
              .then((r) => r.json())
              .then((data) => data.layout.slides.functional_zoning.text === expected)
        """,
        arg={"project": TEST_PROJECT, "expected": heading_text},
        timeout=10000,
    )
    layout = page.evaluate(
        """async (project) => fetch(`/api/drawing/deck-layout?project=${project}`)
            .then((r) => r.json())
            .then((data) => data.layout)""",
        TEST_PROJECT,
    )
    accent = (layout.get("typography_accent") or "").upper()
    assert accent == "#D9882B", f"typography_accent should default to amber orange, got {accent}"
    assert page.locator("[data-ppt-title='true']").count() == 1, "PPT title should render as an independent header"
    assert page.locator("[data-ppt-element='text'] [data-ppt-title='true']").count() == 0, (
        "PPT title must not be nested in the text box"
    )
    title_style = page.locator("[data-ppt-title='true']").evaluate(
        """(node) => {
            const style = getComputedStyle(node);
            return {
                fontFamily: style.fontFamily,
                fontSize: style.fontSize,
                color: style.color,
                fontWeight: style.fontWeight,
            };
        }"""
    )
    heading_color = page.locator("[data-ppt-text-heading='true']").first.evaluate("(node) => getComputedStyle(node).color")
    assert heading_color == "rgb(217, 136, 43)", f"heading accent should use global amber, got {heading_color}"

    page.evaluate("() => window.DrawingWorkbenchTest.switchDrawingType('traffic_analysis')")
    page.wait_for_function(
        "() => window.DrawingWorkbenchTest && window.DrawingWorkbenchTest.getActiveDrawingType() === 'traffic_analysis'",
        timeout=15000,
    )
    page.fill("#pptSlideText", "交通组织：车行与人行路径清晰。")
    page.click("#savePptSlideText")
    page.wait_for_function(
        """({project}) =>
            fetch(`/api/drawing/deck-layout?project=${project}`)
              .then((r) => r.json())
              .then((data) => data.layout.slides.traffic_analysis.text.includes('交通组织'))
        """,
        arg={"project": TEST_PROJECT},
        timeout=10000,
    )
    other_title_style = page.locator("[data-ppt-title='true']").evaluate(
        """(node) => {
            const style = getComputedStyle(node);
            return {
                fontFamily: style.fontFamily,
                fontSize: style.fontSize,
                color: style.color,
                fontWeight: style.fontWeight,
            };
        }"""
    )
    other_heading_color = page.locator("[data-ppt-text-heading='true']").first.evaluate("(node) => getComputedStyle(node).color")
    assert other_title_style == title_style, f"title style must be deck-global: {title_style} vs {other_title_style}"
    assert other_heading_color == heading_color, f"heading accent must be deck-global: {heading_color} vs {other_heading_color}"
    page.evaluate("() => window.DrawingWorkbenchTest.switchDrawingType('functional_zoning')")
    page.wait_for_function(
        "() => window.DrawingWorkbenchTest && window.DrawingWorkbenchTest.getActiveDrawingType() === 'functional_zoning'",
        timeout=15000,
    )
    page.reload(wait_until="domcontentloaded")
    page.wait_for_function(
        "() => window.DrawingWorkbenchTest && window.DrawingWorkbenchTest.getActiveDrawingType() === 'functional_zoning'",
        timeout=20000,
    )
    page.click("#togglePptPreview")
    assert page.locator("#pptPreviewPanel").is_visible(), "PPT preview should reopen after typography comparison"


def assert_reflow_guard(page) -> None:
    manual_x = 0.731
    page.evaluate(
        """async ({project, manualX}) => {
            const current = await fetch(`/api/drawing/deck-layout?project=${project}`).then((r) => r.json());
            const layout = current.layout;
            const slide = layout.slides.functional_zoning;
            slide.manual_overrides = true;
            slide.elements.text.x = manualX;
            slide.elements.text.y = 0.211;
            await fetch('/api/drawing/deck-layout/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ project, layout }),
            });
        }""",
        {"project": TEST_PROJECT, "manualX": manual_x},
    )
    page.reload(wait_until="domcontentloaded")
    page.wait_for_function("window.DrawingWorkbenchTest && document.querySelectorAll('[data-drawing-type]').length >= 10", timeout=20000)
    page.click("#togglePptPreview")
    assert page.locator("#pptPreviewPanel").is_visible(), "PPT preview should reopen for reflow guard"
    dialogs: list[str] = []

    def dismiss_dialog(dialog) -> None:
        dialogs.append(dialog.message)
        dialog.dismiss()

    page.on("dialog", dismiss_dialog)
    page.click("#pptReflowCurrent")
    page.wait_for_timeout(200)
    page.remove_listener("dialog", dismiss_dialog)
    assert dialogs and "手动调整" in dialogs[-1], f"manual reflow warning missing: {dialogs!r}"
    layout = page.evaluate(
        """async (project) => fetch(`/api/drawing/deck-layout?project=${project}`)
            .then((r) => r.json())
            .then((data) => data.layout)""",
        TEST_PROJECT,
    )
    slide = layout["slides"]["functional_zoning"]
    assert slide["manual_overrides"] is True, f"cancelled reflow should keep manual flag: {slide}"
    assert abs(slide["elements"]["text"]["x"] - manual_x) < 0.0001, f"cancelled reflow moved text box: {slide}"
    page.click("#togglePptPreview")
    page.wait_for_function("document.querySelector('#pptPreviewPanel')?.hidden === true", timeout=5000)


def assert_elevation_inverted(page, drawing_type: str) -> None:
    if page.locator('[data-tool-id="elevation_marker"]').count() == 0:
        return
    label = "+12.30"
    page.click('[data-tool-id="elevation_marker"]')
    page.fill("#objectLabel", label)
    page.eval_on_selector(
        "#styleStrokeColor",
        """(el) => {
            el.value = "#8B2CF5";
            el.dispatchEvent(new Event("change", { bubbles: true }));
        }""",
    )
    created = page.evaluate(
        "({tool, pts}) => window.DrawingWorkbenchTest.createObject(tool, pts)",
        {"tool": "elevation_marker", "pts": tool_points("elevation_marker")},
    )
    geo = created.get("geometry") or {}
    assert int(round(float(geo.get("rotation_deg", 0)))) == 180, (
        f"{drawing_type}: elevation default rotation should be 180, got {geo.get('rotation_deg')}"
    )
    obj_id = created["id"]
    rect_box = page.locator(f"#sketchOverlay rect[data-object-id='{obj_id}']").first.bounding_box()
    marker_box = page.locator(f"#sketchOverlay polygon[data-object-id='{obj_id}']").first.bounding_box()
    assert rect_box and marker_box and rect_box["y"] + rect_box["height"] <= marker_box["y"], (
        f"{drawing_type}: elevation label box should sit above inverted triangle; rect={rect_box}, marker={marker_box}"
    )
    item = page.locator(".zone-legend-item", has_text=label).last
    assert item.locator("svg polygon").count() >= 1, f"{drawing_type}: elevation legend missing triangle"
    assert item.locator("svg rect").count() >= 1, f"{drawing_type}: elevation legend missing label box"


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover - this is a hard gate now.
        print(f"FAIL: Playwright is required for browser smoke: {exc}", file=sys.stderr)
        return 1

    proj_dir = prepare_project()
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    preset_src = REPO_ROOT / "_tools" / "drawing_workbench" / "style_presets.json"
    preset_test = proj_dir / "05_output" / "drawings" / "style_presets_smoke.json"
    shutil.copyfile(preset_src, preset_test)
    env["DRAWING_STYLE_PRESETS_PATH"] = str(preset_test)
    server = subprocess.Popen(
        [sys.executable, str(REPO_ROOT / "_tools" / "uploader" / "server.py"), "--port", str(PORT), "--no-browser"],
        cwd=str(REPO_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
    )

    try:
        wait_for_server()
        registry = url_json("/api/drawing/registry")
        assert_preset_not_pale(registry)
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
                    assert_functional_zone_style_presets(page)
                    assert_ppt_preview_basics(page)
                    drive_path_interaction(page, drawing_type, "closed_path")
                if drawing_type != "functional_zoning":
                    dom_tools = page.eval_on_selector_all("[data-tool-id]", "(nodes) => nodes.map((n) => n.dataset.toolId)")
                    assert sorted(dom_tools) == sorted(tools), f"{drawing_type}: DOM tools {dom_tools} != registry {tools}"
                    assert page.locator("#geometryKind").count() == 0, f"{drawing_type}: generic geometry select still visible"
                    assert page.locator("#objectSource").count() == 0, f"{drawing_type}: meaningless source dropdown still visible"
                    assert page.locator("[data-style-controls='true']").count() == 1, f"{drawing_type}: missing style controls"
                    assert page.locator("[data-supporting-panel='true']").count() == 0, f"{drawing_type}: supporting panel shown before supporting tool is active"
                    assert_control_rules(page, drawing_type, tools)
                    if not line_multipoint_checked and "open_path" in tools:
                        assert_line_multipoint(page, drawing_type)
                        line_multipoint_checked = True
                    if "slope_arrow" in tools:
                        assert_slope_text_upright(page, drawing_type)
                        assert_slope_text_above(page, drawing_type)
                    for interaction_tool in ["closed_path", "open_path", "circle", "triangle"]:
                        if not interaction_checked[interaction_tool] and interaction_tool in tools:
                            if interaction_tool in {"closed_path", "open_path"}:
                                drive_path_interaction(page, drawing_type, interaction_tool)
                            else:
                                drive_marker_interaction(page, drawing_type, interaction_tool)
                                if interaction_tool == "circle":
                                    assert_circle_round(page, drawing_type)
                                if interaction_tool == "triangle":
                                    assert_triangle_rotate_no_scale(page, drawing_type)
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
                if drawing_type == "planting_design":
                    assert_non_arrow_line_presets_scoped(page, drawing_type)
                    assert_dash_scale(page, drawing_type)
                    after_objects = page.evaluate("window.DrawingWorkbenchTest.getObjects()")
                    assert_no_bad_kinds(after_objects, drawing_type)
                    assert_legend_non_fz(page, drawing_type)
                    assert_line_legend_straight(page, drawing_type)
                if drawing_type == "landscape_analysis":
                    assert_non_arrow_line_presets_scoped(page, drawing_type)
                if drawing_type == "planting_design":
                    assert_text_tool(page, drawing_type)
                    after_objects = page.evaluate("window.DrawingWorkbenchTest.getObjects()")
                    assert_no_bad_kinds(after_objects, drawing_type)
                if drawing_type == "traffic_analysis":
                    assert_arrow_geometry(page, drawing_type)
                    assert_label_persists(page, drawing_type)
                    assert_legend_by_label(page, drawing_type)
                    assert_arrow_scales(page, drawing_type)
                    assert_move_and_paste(page, drawing_type)
                    assert_style_presets(page, drawing_type)
                    after_objects = page.evaluate("window.DrawingWorkbenchTest.getObjects()")
                    assert_no_bad_kinds(after_objects, drawing_type)
                if drawing_type == "fire_route":
                    assert_labelbox_white_draggable(page, drawing_type)
                    after_objects = page.evaluate("window.DrawingWorkbenchTest.getObjects()")
                    assert_no_bad_kinds(after_objects, drawing_type)
                if drawing_type == "vertical_analysis":
                    assert_elevation_inverted(page, drawing_type)
                    after_objects = page.evaluate("window.DrawingWorkbenchTest.getObjects()")
                    assert_no_bad_kinds(after_objects, drawing_type)

                save_result = page.evaluate("() => window.DrawingWorkbenchTest.saveCurrentDrawing()")
                assert save_result and save_result.get("ok"), f"{drawing_type}: save hook failed: {save_result}"
                page.evaluate("() => window.DrawingWorkbenchTest.loadCurrentDrawing()")
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

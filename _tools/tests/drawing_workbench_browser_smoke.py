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

            for drawing_type, info in enabled.items():
                page.click(f'[data-drawing-type="{drawing_type}"]')
                page.wait_for_function(
                    "(dt) => window.DrawingWorkbenchTest && window.DrawingWorkbenchTest.getActiveDrawingType() === dt",
                    arg=drawing_type,
                    timeout=15000,
                )
                page.wait_for_timeout(100)
                tools = list(info.get("tools") or [])
                if drawing_type != "functional_zoning":
                    dom_tools = page.eval_on_selector_all("[data-tool-id]", "(nodes) => nodes.map((n) => n.dataset.toolId)")
                    assert sorted(dom_tools) == sorted(tools), f"{drawing_type}: DOM tools {dom_tools} != registry {tools}"
                    assert page.locator("#geometryKind").count() == 0, f"{drawing_type}: generic geometry select still visible"
                    assert page.locator("[data-style-controls='true']").count() == 1, f"{drawing_type}: missing style controls"
                    if "supporting_images" in tools:
                        assert page.locator("[data-supporting-panel='true']").count() == 1, f"{drawing_type}: missing supporting panel"

                before = page.evaluate("window.DrawingWorkbenchTest.getObjects().length")
                creatable_tools = [tool for tool in tools if tool != "supporting_images"]
                for tool in creatable_tools:
                    page.evaluate(
                        "({tool, pts}) => window.DrawingWorkbenchTest.createObject(tool, pts)",
                        {"tool": tool, "pts": tool_points(tool)},
                    )
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

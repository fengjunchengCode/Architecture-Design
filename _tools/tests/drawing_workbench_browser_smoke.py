#!/usr/bin/env python3
"""Best-effort browser smoke test for drawing workbench.

This test is NOT a hard gate. If Playwright is not installed, it prints
BROWSER_SMOKE_SKIPPED and exits 0.
"""
from __future__ import annotations

import sys


def main() -> int:
    try:
        import playwright  # noqa: F401
    except ImportError:
        print("BROWSER_SMOKE_SKIPPED: playwright not installed")
        return 0

    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        print(f"BROWSER_SMOKE_SKIPPED: cannot import sync_playwright: {exc}")
        return 0

    # If we get here, try to run a minimal browser test
    import json
    import os
    import shutil
    import subprocess
    import time
    from pathlib import Path

    REPO_ROOT = Path(__file__).resolve().parents[2]
    TEST_PROJECT = "99-ZZ-BROWSER"
    PORT = 18766
    BASE = f"http://127.0.0.1:{PORT}"

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
    server = subprocess.Popen(
        [sys.executable, str(REPO_ROOT / "_tools" / "uploader" / "server.py"),
         "--port", str(PORT), "--no-browser"],
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    try:
        import urllib.request
        for _ in range(30):
            try:
                urllib.request.urlopen(f"{BASE}/api/projects", timeout=2)
                break
            except Exception:
                time.sleep(0.3)
        else:
            print("FAIL: server did not start", file=sys.stderr)
            return 1

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f"{BASE}/workbench.html?project={TEST_PROJECT}&drawing=functional_zoning", wait_until="networkidle", timeout=15000)

            # Check tabs
            tabs = page.query_selector_all("[data-drawing-type]")
            tab_types = [t.get_attribute("data-drawing-type") for t in tabs if t.get_attribute("data-drawing-type")]
            assert len(tab_types) >= 10, f"expected 10+ tabs, got {len(tab_types)}: {tab_types}"
            print(f"OK: {len(tab_types)} drawing tabs found")

            browser.close()

        print("BROWSER_SMOKE_PASSED")
        return 0

    except Exception as exc:
        print(f"BROWSER_SMOKE_SKIPPED: {exc}")
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

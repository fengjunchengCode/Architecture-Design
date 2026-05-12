#!/usr/bin/env python3
"""Check whether the repository is ready for agent-driven workflows."""
from __future__ import annotations

import argparse
import importlib.util
import json
import py_compile
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Check:
    name: str
    ok: bool
    detail: str


def check_file(path: str) -> Check:
    full = REPO_ROOT / path
    return Check(path, full.exists(), "exists" if full.exists() else "missing")


def check_python() -> Check:
    version = sys.version_info
    ok = version >= (3, 10)
    detail = f"{version.major}.{version.minor}.{version.micro}"
    return Check("python>=3.10", ok, detail)


def check_module(module: str) -> Check:
    spec = importlib.util.find_spec(module)
    return Check(f"module:{module}", spec is not None, "installed" if spec else "missing")


def check_compile(path: str) -> Check:
    full = REPO_ROOT / path
    if not full.exists():
        return Check(f"compile:{path}", False, "missing")
    try:
        py_compile.compile(str(full), doraise=True)
    except Exception as exc:
        return Check(f"compile:{path}", False, str(exc))
    return Check(f"compile:{path}", True, "ok")


def run_checks() -> list[Check]:
    checks = [
        check_python(),
        check_module("yaml"),
        check_file("requirements.txt"),
        check_file("AGENTS.md"),
        check_file("_schema/record.schema.md"),
        check_file("_schema/folder.convention.md"),
        check_file("_schema/folder.convention.yaml"),
        check_file("_tools/init_project/scaffold.py"),
        check_file("_tools/validate_record.py"),
        check_file("_tools/inventory.py"),
        check_file("_tools/uploader/server.py"),
        check_file("_tools/uploader/static/index.html"),
        check_file("skills/S0_project_intake/SKILL.md"),
    ]
    (REPO_ROOT / "projects").mkdir(exist_ok=True)
    checks.append(check_file("projects"))
    checks.extend(
        [
            check_compile("_tools/init_project/scaffold.py"),
            check_compile("_tools/validate_record.py"),
            check_compile("_tools/inventory.py"),
            check_compile("_tools/uploader/server.py"),
        ]
    )
    return checks


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Repository self-check for agents")
    parser.add_argument("--json", action="store_true", help="Print machine-readable output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    checks = run_checks()
    ok = all(check.ok for check in checks)

    if args.json:
        out: dict[str, Any] = {
            "repo_root": str(REPO_ROOT),
            "ok": ok,
            "checks": [asdict(check) for check in checks],
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(f"== selfcheck :: {REPO_ROOT}")
        for check in checks:
            status = "OK" if check.ok else "FAIL"
            print(f"  [{status}] {check.name}: {check.detail}")

    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Check whether the repository is ready for agent-driven workflows."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import py_compile
import shutil
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


def check_optional_module(module: str, purpose: str) -> Check:
    spec = importlib.util.find_spec(module)
    detail = "installed" if spec else f"missing optional dependency for {purpose}"
    return Check(f"optional-module:{module}", True, detail)


def check_optional_oda_file_converter() -> Check:
    candidates: list[Path] = []
    for env_name in ("ODA_FILE_CONVERTER", "ODAFC_PATH", "ODA_FILE_CONVERTER_EXE"):
        value = os.environ.get(env_name)
        if value:
            candidates.append(Path(value.strip().strip('"')).expanduser())
    found = shutil.which("ODAFileConverter") or shutil.which("ODAFileConverter.exe")
    if found:
        candidates.append(Path(found))
    try:
        import ezdxf
        from ezdxf.addons import odafc

        candidates.append(Path(odafc.get_win_exec_path()))
    except Exception:
        pass
    for env_name in ("LOCALAPPDATA", "ProgramFiles", "ProgramFiles(x86)"):
        value = os.environ.get(env_name)
        if not value:
            continue
        root = Path(value)
        if not root.exists():
            continue
        for pattern in (
            "ODAFC*/ODAFileConverter.exe",
            "ODA/ODAFileConverter*/ODAFileConverter.exe",
            "ODAFileConverter*/ODAFileConverter.exe",
        ):
            candidates.extend(root.glob(pattern))
    for candidate in candidates:
        if candidate.is_file():
            return Check("optional-tool:ODAFileConverter", True, str(candidate))
    return Check(
        "optional-tool:ODAFileConverter",
        True,
        "missing optional tool for S2 DWG conversion; install ODA File Converter or run _tools/dwg_probe.py for guidance",
    )


def check_compile(path: str) -> Check:
    full = REPO_ROOT / path
    if not full.exists():
        return Check(f"compile:{path}", False, "missing")
    try:
        py_compile.compile(str(full), doraise=True)
    except Exception as exc:
        return Check(f"compile:{path}", False, str(exc))
    return Check(f"compile:{path}", True, "ok")


def check_skill_frontmatter(path: str) -> Check:
    full = REPO_ROOT / path
    if not full.exists():
        return Check(f"skill-frontmatter:{path}", False, "missing")
    text = full.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return Check(f"skill-frontmatter:{path}", False, "missing frontmatter")
    end = text.find("\n---\n", 4)
    if end == -1:
        return Check(f"skill-frontmatter:{path}", False, "unclosed frontmatter")
    frontmatter = text[4:end]
    has_name = any(line.startswith("name:") and line[5:].strip() for line in frontmatter.splitlines())
    has_description = any(
        line.startswith("description:") and line[12:].strip() for line in frontmatter.splitlines()
    )
    ok = has_name and has_description
    detail = "ok" if ok else "requires name and description"
    return Check(f"skill-frontmatter:{path}", ok, detail)


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
        check_file("_tools/extract_text.py"),
        check_file("_tools/vision_route.py"),
        check_file("_tools/dwg_probe.py"),
        check_file("_tools/uploader/server.py"),
        check_file("_tools/uploader/static/index.html"),
        check_file("SKILL.md"),
        check_file("skills/_shared/record_contract.md"),
        check_file("skills/_shared/marker_contract.md"),
        check_file("skills/_shared/folder_contract.md"),
        check_file("skills/_shared/confidence_contract.md"),
        check_file("skills/_shared/output_style.md"),
        check_file("skills/S0_project_intake/SKILL.md"),
        check_file("skills/S0_project_intake/user_guidance.md"),
        check_file("skills/S1_site_analysis/SKILL.md"),
        check_file("skills/S2_dwg_parse/SKILL.md"),
        check_file("skills/S3_area_and_massing/SKILL.md"),
        check_file("skills/S4_questions_summary/SKILL.md"),
        check_file("skills/S9_report_outline/SKILL.md"),
    ]
    (REPO_ROOT / "projects").mkdir(exist_ok=True)
    checks.append(check_file("projects"))
    skill_paths = [
        "SKILL.md",
        "skills/S0_project_intake/SKILL.md",
        "skills/S1_site_analysis/SKILL.md",
        "skills/S2_dwg_parse/SKILL.md",
        "skills/S3_area_and_massing/SKILL.md",
        "skills/S4_questions_summary/SKILL.md",
        "skills/S9_report_outline/SKILL.md",
    ]
    checks.extend(check_skill_frontmatter(path) for path in skill_paths)
    checks.extend(
        [
            check_compile("_tools/init_project/scaffold.py"),
            check_compile("_tools/validate_record.py"),
            check_compile("_tools/inventory.py"),
            check_compile("_tools/extract_text.py"),
            check_compile("_tools/vision_route.py"),
            check_compile("_tools/dwg_probe.py"),
            check_compile("_tools/uploader/server.py"),
        ]
    )
    checks.extend(
        [
            check_optional_module("ezdxf", "S2 DWG/DXF parsing"),
            check_optional_oda_file_converter(),
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

#!/usr/bin/env python3
"""Scan project input files and report deterministic facts for S0."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECTS_DIR = REPO_ROOT / "projects"

INPUT_DIRS = [
    "01_briefing",
    "02_site/区位图",
    "02_site/地形图",
    "02_site/现场照片",
    "03_references",
    "04_chat",
]

LOCATION_EXTS = {".png", ".jpg", ".jpeg", ".pdf"}
DIRECT_TEXT_EXTS = {".txt", ".md", ".html", ".htm", ".csv", ".json", ".yaml", ".yml"}
DOCUMENT_EXTRACT_EXTS = {".docx", ".pdf"}
VISUAL_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
LEGACY_WORD_EXTS = {".doc"}
BINARY_INDEX_ONLY_EXTS = {".dwg", ".dxf", ".skp", ".psd", ".heic"}


@dataclass
class FileRecord:
    path: str
    size_bytes: int
    sha1: str
    bucket: str
    ext: str
    read_policy: str
    requires_conversion: bool
    agent_note: str


def sha1_file(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def classify(rel_path: str) -> str:
    normalized = rel_path.replace("\\", "/")
    if normalized.startswith("01_briefing/"):
        return "briefing"
    if normalized.startswith("02_site/区位图/"):
        return "location_map"
    if normalized.startswith("02_site/地形图/"):
        return "topography"
    if normalized.startswith("02_site/现场照片/"):
        return "site_photo"
    if normalized.startswith("03_references/"):
        return "reference"
    if normalized.startswith("04_chat/"):
        return "chat"
    return "other"


def read_policy_for(path: Path) -> tuple[str, bool, str]:
    ext = path.suffix.lower()
    if ext in DIRECT_TEXT_EXTS:
        return ("direct_text", False, "Safe to read as UTF-8/HTML text if size is reasonable.")
    if ext in DOCUMENT_EXTRACT_EXTS:
        return ("document_extract", False, "Use a dedicated document/PDF extractor or renderer; do not read raw bytes.")
    if ext in VISUAL_EXTS:
        return (
            "visual_asset",
            False,
            "Route only through _tools/vision_route.py. Do not read image content with the active chat model or ask the user to switch models.",
        )
    if ext in LEGACY_WORD_EXTS:
        return (
            "legacy_word_conversion_required",
            True,
            "Legacy .doc binary: inventory only. Convert to .docx, PDF, or TXT before semantic extraction; do not use strings/cat/raw reads.",
        )
    if ext in BINARY_INDEX_ONLY_EXTS:
        return (
            "binary_index_only",
            False,
            "Binary/CAD asset: record path/hash only. For S2 DWG/DXF facts, use _tools/dwg_probe.py; do not read raw bytes.",
        )
    return ("unknown_index_only", False, "Unknown extension: record path/hash only until a reader is explicitly chosen.")


def iter_input_files(project_dir: Path) -> list[FileRecord]:
    records: list[FileRecord] = []
    for input_dir in INPUT_DIRS:
        root = project_dir / input_dir
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.name == ".gitkeep":
                continue
            rel = path.relative_to(project_dir).as_posix()
            read_policy, requires_conversion, agent_note = read_policy_for(path)
            records.append(
                FileRecord(
                    path=rel,
                    size_bytes=path.stat().st_size,
                    sha1=sha1_file(path),
                    bucket=classify(rel),
                    ext=path.suffix.lower(),
                    read_policy=read_policy,
                    requires_conversion=requires_conversion,
                    agent_note=agent_note,
                )
            )
    return sorted(records, key=lambda item: item.path)


def has_location_map(records: list[FileRecord]) -> bool:
    return any(
        record.bucket == "location_map" and Path(record.path).suffix.lower() in LOCATION_EXTS
        for record in records
    )


def resolve_project(code_or_path: str) -> Path:
    direct = Path(code_or_path).expanduser()
    if direct.exists():
        return direct.resolve()
    return PROJECTS_DIR / code_or_path


def write_report(project_dir: Path, report: dict[str, Any]) -> Path:
    out_dir = project_dir / "05_output"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / "inventory.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan project files for S0")
    parser.add_argument("project", help="Project code or path")
    parser.add_argument("--json", action="store_true", help="Print JSON only")
    parser.add_argument("--write", action="store_true", help="Write 05_output/inventory.json")
    parser.add_argument("--require-s0-ready", action="store_true", help="Exit 2 if location map is missing")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_dir = resolve_project(args.project)
    if not project_dir.exists():
        print(f"ERROR: project not found: {project_dir}", file=sys.stderr)
        return 3

    records = iter_input_files(project_dir)
    s0_ready = has_location_map(records)
    conversion_required = [record.path for record in records if record.requires_conversion]
    warnings = []
    if conversion_required:
        warnings.append(
            "Legacy .doc files require conversion to .docx, PDF, or TXT before semantic extraction. "
            "Agents must not use strings/cat/raw binary reads as a fallback."
        )
    report: dict[str, Any] = {
        "project_dir": str(project_dir),
        "project_code": project_dir.name,
        "s0_ready": s0_ready,
        "required_missing": [] if s0_ready else ["02_site/区位图/*.{png,jpg,jpeg,pdf}"],
        "conversion_required": conversion_required,
        "warnings": warnings,
        "files": [asdict(record) for record in records],
        "counts": {
            "total": len(records),
            "conversion_required": len(conversion_required),
            "briefing": sum(1 for record in records if record.bucket == "briefing"),
            "location_map": sum(1 for record in records if record.bucket == "location_map"),
            "topography": sum(1 for record in records if record.bucket == "topography"),
            "site_photo": sum(1 for record in records if record.bucket == "site_photo"),
            "reference": sum(1 for record in records if record.bucket == "reference"),
            "chat": sum(1 for record in records if record.bucket == "chat"),
        },
    }

    if args.write:
        report["written_to"] = str(write_report(project_dir, report))

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"== inventory :: {project_dir}")
        print(f"  s0_ready: {s0_ready}")
        if report["required_missing"]:
            print(f"  missing: {', '.join(report['required_missing'])}")
        if conversion_required:
            print("  conversion_required:")
            for path in conversion_required:
                print(f"    - {path}")
        for key, value in report["counts"].items():
            print(f"  {key}: {value}")

    if args.require_s0_ready and not s0_ready:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

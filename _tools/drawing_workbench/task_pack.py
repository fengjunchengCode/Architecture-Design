#!/usr/bin/env python3
"""Build task packs for agent-authored drawing overlays."""
from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _tools.drawing_workbench.pdf_page_extract import extract_page
from _tools.drawing_workbench.registry import DRAWING_TYPES, default_base_path_for
from _tools.drawing_workbench.schema import drawing_output_paths, normalize_drawing


REPO_ROOT = Path(__file__).resolve().parents[2]
PROJECTS_DIR = REPO_ROOT / "projects"
PAGE_INDEX = REPO_ROOT / "docs" / "reference_pdfs" / "page_index.json"
CODE_REGEX = re.compile(r"^\d{2}-[A-Z]{2,3}-[A-Za-z0-9]{2,8}$")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def safe_project(code: str) -> str:
    code = code.strip()
    if not CODE_REGEX.match(code):
        raise ValueError("项目代号格式应为 26-SZ-NSXX")
    return code


def project_dir(code: str) -> Path:
    path = (PROJECTS_DIR / safe_project(code)).resolve()
    if PROJECTS_DIR.resolve() not in path.parents:
        raise ValueError("项目路径越界")
    return path


def build_task_pack(
    project_code: str,
    drawing_type: str,
    sketch_path: str | Path | None = None,
    user_notes: str = "",
) -> Path:
    code = safe_project(project_code)
    if drawing_type not in DRAWING_TYPES:
        raise ValueError(f"drawing_type must be one of {sorted(DRAWING_TYPES)}")
    proj = project_dir(code)
    rels = drawing_output_paths(drawing_type)
    sketch_rel = str(sketch_path or rels["semantic"]).replace("\\", "/").lstrip("/")
    sketch_abs = (proj / sketch_rel).resolve()
    if proj.resolve() not in sketch_abs.parents:
        raise ValueError("sketch_path must stay inside the project")
    if not sketch_abs.exists():
        raise FileNotFoundError(sketch_abs)

    drawing = normalize_drawing(json.loads(sketch_abs.read_text(encoding="utf-8")), project_code=code)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    task_id = f"{drawing_type}__{timestamp}"
    pack_dir = proj / "05_output" / "drawings" / "task_packs" / task_id
    pack_dir = _unique_dir(pack_dir)
    pack_dir.mkdir(parents=True, exist_ok=False)

    shutil.copy2(sketch_abs, pack_dir / "sketch.json")
    base_rel = str(drawing["base_image"]["path"])
    base_abs = (proj / base_rel).resolve()
    base_copy_rel = None
    if proj.resolve() in base_abs.parents and base_abs.exists():
        base_target = pack_dir / f"base_image{base_abs.suffix.lower() or '.img'}"
        shutil.copy2(base_abs, base_target)
        base_copy_rel = base_target.name

    style_source = proj / "05_output" / "style" / "style_spec.json"
    style_target = pack_dir / "style_spec.json"
    if style_source.exists():
        shutil.copy2(style_source, style_target)
    else:
        style_target.write_text(json.dumps({"exists": False}, ensure_ascii=False, indent=2), encoding="utf-8")

    context_dir = pack_dir / "context"
    context_dir.mkdir(exist_ok=True)
    context_files = _write_record_context(proj, context_dir)

    reference_files, reference_errors = _write_reference_pages(pack_dir, drawing_type)

    # Supporting images
    supporting_images = _copy_supporting_images(proj, pack_dir, drawing_type)

    task = {
        "schema_version": "1.1",
        "task_id": task_id,
        "created_at": now_iso(),
        "project_code": code,
        "drawing_type": drawing_type,
        "user_notes": str(user_notes or "").strip(),
        "output_target": rels["svg"],
        "inputs": {
            "sketch": "sketch.json",
            "base_image": base_copy_rel,
            "base_image_source": base_rel,
            "style_spec": "style_spec.json",
            "context": context_files,
            "references": reference_files,
            "supporting_images": supporting_images,
        },
    }
    if reference_errors:
        task["reference_errors"] = reference_errors
    (pack_dir / "task.json").write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")
    return pack_dir


def _copy_supporting_images(proj: Path, pack_dir: Path, drawing_type: str) -> dict[str, Any]:
    manifest_path = proj / "05_output" / "drawings" / "supporting" / drawing_type / "manifest.json"
    if not manifest_path.exists():
        return {"manifest": None, "images_dir": None, "count": 0}

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    images = manifest.get("images", [])
    if not images:
        return {"manifest": None, "images_dir": None, "count": 0}

    sup_dir = pack_dir / "supporting"
    sup_dir.mkdir(exist_ok=True)
    images_dir = sup_dir / "images"
    images_dir.mkdir(exist_ok=True)

    copied = 0
    for img in images:
        file_rel = img.get("file", "")
        src = (proj / file_rel).resolve()
        if proj.resolve() in src.parents and src.exists():
            shutil.copy2(src, images_dir / src.name)
            copied += 1

    (sup_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {"manifest": "supporting/manifest.json", "images_dir": "supporting/images", "count": copied}


def _write_record_context(proj: Path, context_dir: Path) -> dict[str, str | None]:
    record = proj / "05_output" / "record.md"
    files: dict[str, str | None] = {"s1_registration": None, "s2_alignment": None}
    if not record.exists():
        return files
    text = record.read_text(encoding="utf-8")
    marker_map = {
        "s1_registration": "s1_site_analysis",
        "s2_alignment": "s2_dwg_parse",
    }
    for name, marker in marker_map.items():
        out = context_dir / f"{name}.json"
        out.write_text(
            json.dumps(
                {
                    "source": "05_output/record.md",
                    "marker": marker,
                    "content": _extract_marker(text, marker),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        files[name] = f"context/{out.name}"
    return files


def _unique_dir(path: Path) -> Path:
    if not path.exists():
        return path
    index = 1
    while True:
        candidate = path.with_name(f"{path.name}-{index}")
        if not candidate.exists():
            return candidate
        index += 1


def _extract_marker(text: str, marker: str) -> str:
    begin = f"<!-- BEGIN:{marker} -->"
    end = f"<!-- END:{marker} -->"
    start = text.find(begin)
    finish = text.find(end)
    if start < 0 or finish < 0 or finish < start:
        return ""
    return text[start + len(begin) : finish].strip()


def _write_reference_pages(pack_dir: Path, drawing_type: str) -> tuple[list[str], list[dict[str, Any]]]:
    references: list[str] = []
    errors: list[dict[str, Any]] = []
    if not PAGE_INDEX.exists():
        return references, errors
    manifest = json.loads(PAGE_INDEX.read_text(encoding="utf-8"))
    ref_dir = pack_dir / "references"
    ref_dir.mkdir(exist_ok=True)
    for key, item in sorted(manifest.items()):
        if not isinstance(item, dict):
            continue
        pdf_rel = str(item.get("pdf") or "").strip()
        pages = ((item.get("drawings") or {}).get(drawing_type) or []) if isinstance(item.get("drawings"), dict) else []
        if not pdf_rel or not isinstance(pages, list):
            continue
        pdf_path = (REPO_ROOT / pdf_rel).resolve()
        for page in pages:
            try:
                page_no = int(page)
                out = ref_dir / f"{key}__p{page_no:03d}.png"
                extract_page(pdf_path, page_no, out, dpi=200)
                references.append(f"references/{out.name}")
            except Exception as exc:  # keep task_pack usable even when a reference tool is missing
                errors.append({"source": key, "page": page, "error": str(exc)})
    return references, errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a drawing task pack for agent handoff.")
    parser.add_argument("project")
    parser.add_argument("drawing_type", choices=sorted(DRAWING_TYPES))
    parser.add_argument("--sketch-path", default=None)
    parser.add_argument("--user-notes", default="")
    args = parser.parse_args()
    path = build_task_pack(args.project, args.drawing_type, args.sketch_path, args.user_notes)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

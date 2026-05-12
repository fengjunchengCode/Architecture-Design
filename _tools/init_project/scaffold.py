#!/usr/bin/env python3
"""
_tools/init_project/scaffold.py

S0 阶段 1：脚手架。创建项目文件夹骨架 + 占位 record.md + 项目级 .uploader.yaml。
使用：
    python _tools/init_project/scaffold.py 26-SZ-NSXX \\
        --type school --name "深圳南山某小学"
退出码：
    0  成功
    10 代号格式不合
    11 项目已存在且未 --resume
    40 其他 IO 错误
"""
from __future__ import annotations

import argparse
import datetime
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    sys.stderr.write("ERROR: missing PyYAML. Run: python -m pip install -r requirements.txt\n")
    sys.exit(40)

## ---------- 常量 ----------
EXIT_OK = 0
EXIT_BAD_CODE = 10
EXIT_EXISTS = 11
EXIT_IO = 40

CODE_REGEX = re.compile(r"^\d{2}-[A-Z]{2,3}-[A-Za-z0-9]{2,8}$")
SCHEMA_VERSION = "1.0"
REPO_ROOT = Path(__file__).resolve().parents[2]
FOLDER_CONFIG = REPO_ROOT / "_schema" / "folder.convention.yaml"

## 11 种 type。与 record.schema.md § 3.1 保持一致。
VALID_TYPES = {
    "school", "residential", "commercial", "park", "street_scape",
    "renovation", "hospital", "cultural", "industrial",
    "cultural_tourism", "unknown",
}

## 骨架文件夹（与 folder.convention.md § 1 保持一致）
SKELETON_DIRS = [
    "01_briefing",
    "02_site/区位图",
    "02_site/地形图",
    "02_site/现场照片",
    "03_references",
    "04_chat",
    "05_output",
]

## type 覆盖项：某些 type 额外要求的子文件夹（为空表示无额外）
TYPE_EXTRA_DIRS: dict[str, list[str]] = {
    "renovation": ["02_site/现状测绘"],
    "cultural_tourism": ["02_site/所广区范围"],
}


def load_layout() -> tuple[list[str], dict[str, list[str]]]:
    if not FOLDER_CONFIG.exists():
        return SKELETON_DIRS, TYPE_EXTRA_DIRS
    with FOLDER_CONFIG.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    folders = [
        folder["path"]
        for folder in data.get("folders", [])
        if folder.get("path")
    ] or SKELETON_DIRS
    overrides = data.get("project_type_overrides", {}) or {}
    extra_dirs: dict[str, list[str]] = {}
    for project_type, config in overrides.items():
        extra_dirs[project_type] = list(config.get("extra_dirs") or [])
    return folders, extra_dirs or TYPE_EXTRA_DIRS

## ---------- 主逻辑 ----------
def validate_code(code: str) -> None:
    if not CODE_REGEX.match(code):
        sys.stderr.write(
            f"ERROR: 代号格式不合 '{code}'\n"
            f"期望正则: {CODE_REGEX.pattern}\n"
            f"例: 26-SZ-NSXX\n"
        )
        sys.exit(EXIT_BAD_CODE)

def ensure_project_dir(code: str, resume: bool) -> Path:
    proj = REPO_ROOT / "projects" / code
    if proj.exists() and not resume:
        sys.stderr.write(
            f"ERROR: 项目已存在 {proj}\n"
            f"请重命名代号或使用 --resume\n"
        )
        sys.exit(EXIT_EXISTS)
    proj.mkdir(parents=True, exist_ok=True)
    return proj

def create_subdirs(proj: Path, project_type: str, skeleton_dirs: list[str], type_extra_dirs: dict[str, list[str]]) -> list[str]:
    created = []
    dirs = skeleton_dirs + type_extra_dirs.get(project_type, [])
    for d in dirs:
        full = proj / d
        if not full.exists():
            full.mkdir(parents=True, exist_ok=True)
            ## .gitkeep 留住空文件夹
            (full / ".gitkeep").touch()
            created.append(str(full.relative_to(REPO_ROOT)))
    return created

def build_record(code: str, name: str, project_type: str) -> dict[str, Any]:
    now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    return {
        "schema_version": SCHEMA_VERSION,
        "project": {
            "code": code,
            "name": name,
            "client": None,
            "type": project_type,
            "scale": None,
            "stage": "待放置文件",
            "updated_at": now,
        },
        "site": {
            "address": None,
            "coords": None,
            "area_sqm": None,
            "far_max": None,
            "height_limit_m": None,
            "setback": None,
            "has_elevation_diff": None,
            "boundary_shape": None,
        },
        "style_preferences": {
            "keywords": None,
            "references": None,
            "client_raw_quotes": None,
        },
        "brief": {"summary": None},
        "pending_questions": [],
        "low_confidence_fields": [],
        "completeness": {
            "filled_required_pct": 0,
            "ready_for": [],
            "blocked": [
                {"skill": "S0", "reason": "尚未投递区位图"},
            ],
        },
        "files_indexed": [],
    }

MARKER_TEMPLATE = """\
# 项目档案：{code} {name}

<!-- BEGIN:s0_parsed -->
_pending: 等 S0 写入_
<!-- END:s0_parsed -->

<!-- BEGIN:s1_site_analysis -->
_pending: 等 S1 写入_
<!-- END:s1_site_analysis -->

<!-- BEGIN:s2_dwg_parse -->
_pending: 等 S2 写入_
<!-- END:s2_dwg_parse -->

<!-- BEGIN:s3_area_calc -->
_pending: 等 S3 写入_
<!-- END:s3_area_calc -->

<!-- BEGIN:s4_questions_summary -->
_pending: 等 S4 写入_
<!-- END:s4_questions_summary -->

<!-- BEGIN:s9_report_outline -->
_pending: 等 S9 写入_
<!-- END:s9_report_outline -->
"""

def write_record_md(proj: Path, record: dict[str, Any]) -> Path:
    out = proj / "05_output" / "record.md"
    if out.exists():
        ## --resume 下已存在不覆盖
        return out
    with out.open("w", encoding="utf-8") as f:
        f.write("---\n")
        yaml.safe_dump(record, f, allow_unicode=True, sort_keys=False, width=120)
        f.write("---\n\n")
        f.write(MARKER_TEMPLATE.format(**record["project"]))
    return out

UPLOADER_YAML_TEMPLATE = """\
## 项目级投递助手配置；仅 S0 读它作为就绪检查。人工可改。
project_code: "{code}"
project_type: "{type}"
s0_ready_gate:
  ## 区位图是 S0 硬门槛；缺失时 agent 只做收件检查，不进入解析。
  required:
    - "02_site/区位图/**/*"
  ## 以下路径推荐但不是硬门槛。
  recommended:
    - "01_briefing/**/*"
    - "02_site/现场照片/**/*"
    - "04_chat/**/*"
port: 8765
"""

def write_uploader_yaml(proj: Path, code: str, project_type: str) -> Path:
    out = proj / ".uploader.yaml"
    if out.exists():
        return out
    out.write_text(
        UPLOADER_YAML_TEMPLATE.format(code=code, type=project_type),
        encoding="utf-8",
    )
    return out

## ---------- CLI ----------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="S0 脚手架")
    p.add_argument("code", help="项目代号，如 26-SZ-NSXX")
    p.add_argument("--type", dest="project_type", default="unknown",
                   choices=sorted(VALID_TYPES))
    p.add_argument("--name", required=False, default="")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--dry-run", action="store_true",
                   help="不创建、仅输出将执行的动作")
    return p.parse_args()

def main() -> int:
    args = parse_args()
    validate_code(args.code)
    skeleton_dirs, type_extra_dirs = load_layout()

    name = args.name or args.code
    if not args.name:
        sys.stderr.write("WARN: 未提供 --name，使用代号作名。请后期手改 record.md\n")

    if args.dry_run:
        sys.stderr.write("[dry-run] 将创建以下路径:\n")
        proj = REPO_ROOT / "projects" / args.code
        for d in skeleton_dirs + type_extra_dirs.get(args.project_type, []):
            sys.stderr.write(f"  - {(proj / d).relative_to(REPO_ROOT)}/\n")
        sys.stderr.write(f"  - {(proj / '05_output' / 'record.md').relative_to(REPO_ROOT)}\n")
        sys.stderr.write(f"  - {(proj / '.uploader.yaml').relative_to(REPO_ROOT)}\n")
        return EXIT_OK

    try:
        proj = ensure_project_dir(args.code, args.resume)
        created_dirs = create_subdirs(proj, args.project_type, skeleton_dirs, type_extra_dirs)
        record = build_record(args.code, name, args.project_type)
        record_path = write_record_md(proj, record)
        uploader_path = write_uploader_yaml(proj, args.code, args.project_type)
    except OSError as e:
        sys.stderr.write(f"ERROR: IO 失败 {e}\n")
        return EXIT_IO

    ## stdout = 成果清单（供上游调用者读）
    print(f"project_dir: {proj.relative_to(REPO_ROOT)}")
    print(f"record_md: {record_path.relative_to(REPO_ROOT)}")
    print(f"uploader_yaml: {uploader_path.relative_to(REPO_ROOT)}")
    print(f"created_dirs: {len(created_dirs)}")
    for d in created_dirs:
        print(f"  - {d}/")
    return EXIT_OK

if __name__ == "__main__":
    sys.exit(main())

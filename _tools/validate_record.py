#!/usr/bin/env python3
"""
_tools/validate_record.py

校验项目 record.md 是否符合 schema v1.0。
使用：
    python _tools/validate_record.py 26-SZ-NSXX
    python _tools/validate_record.py 26-SZ-NSXX --json   ## 输出机器可读报表
    python _tools/validate_record.py --path projects/26-SZ-NSXX/05_output/record.md
退出码：
    0  OK（可能有 WARN/INFO，但无 FATAL）
    2  FATAL（骨架不合）
    3  文件不存在 / 读取失败
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

try:
    import yaml
except ImportError:
    sys.stderr.write("ERROR: missing PyYAML. Run: python -m pip install -r requirements.txt\n")
    sys.exit(3)

## ---------- 常量 ----------
EXIT_OK = 0
EXIT_FATAL = 2
EXIT_IO = 3

REPO_ROOT = Path(__file__).resolve().parents[1]
CODE_REGEX = re.compile(r"^\d{2}-[A-Z]{2,3}-[A-Za-z0-9]{2,8}$")
SUPPORTED_SCHEMA = {"1.0"}
VALID_TYPES = {
    "school", "residential", "commercial", "park", "street_scape",
    "renovation", "hospital", "cultural", "industrial",
    "cultural_tourism", "unknown",
}
REQUIRED_MARKERS = [
    "s0_parsed",
    "s1_site_analysis",
    "s2_dwg_parse",
    "s3_area_calc",
    "s4_questions_summary",
    "s9_report_outline",
]
VALID_STATUS = {"待问", "已问", "已答", "已归档"}
VALID_RAISED_BY = {"S0", "S1", "S2", "S3", "S4", "S9", "用户"}

## ---------- 报告类型 ----------
@dataclass
class Issue:
    level: str   ## FATAL / WARN / INFO
    code: str
    msg: str

@dataclass
class Report:
    path: str
    issues: list[Issue] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    @property
    def fatal_count(self) -> int:
        return sum(1 for i in self.issues if i.level == "FATAL")

    @property
    def warn_count(self) -> int:
        return sum(1 for i in self.issues if i.level == "WARN")

    def add(self, level: str, code: str, msg: str) -> None:
        self.issues.append(Issue(level, code, msg))

## ---------- 读取 ----------
def read_frontmatter(text: str) -> tuple[dict | None, str]:
    """分离 YAML frontmatter 与正文。失败返回 (None, original)。"""
    if not text.startswith("---"):
        return None, text
    end = text.find("\n---", 3)
    if end < 0:
        return None, text
    yaml_text = text[3:end].lstrip("\n")
    body = text[end + 4:].lstrip("\n")
    try:
        return yaml.safe_load(yaml_text), body
    except Exception:
        return None, body

## ---------- 校验 ----------
def check_required_fields(data: dict, path: Path, rpt: Report) -> None:
    if data.get("schema_version") not in SUPPORTED_SCHEMA:
        rpt.add("FATAL", "SCHEMA_VERSION",
                f"schema_version={data.get('schema_version')} 不受支持。需跱 migrate_schema.py")

    proj = data.get("project") or {}
    if not proj.get("code"):
        rpt.add("FATAL", "REQ_CODE", "project.code 不可为空")
    elif not CODE_REGEX.match(str(proj["code"])):
        rpt.add("FATAL", "BAD_CODE",
                f"project.code='{proj['code']}' 不匹配 {CODE_REGEX.pattern}")
    else:
        project_dir = path.parent.parent.name if path.name == "record.md" and path.parent.name == "05_output" else None
        if project_dir and proj["code"] != project_dir:
            rpt.add("FATAL", "CODE_FOLDER",
                    f"project.code='{proj['code']}' 必须等于项目文件夹名 '{project_dir}'")

    if not proj.get("name"):
        rpt.add("FATAL", "REQ_NAME", "project.name 不可为空")

    if proj.get("type") and proj["type"] not in VALID_TYPES:
        rpt.add("FATAL", "BAD_TYPE",
                f"project.type='{proj['type']}' 不在白名单 {sorted(VALID_TYPES)}")

def check_markers(body: str, rpt: Report) -> None:
    for m in REQUIRED_MARKERS:
        begin = f"<!-- BEGIN:{m} -->"
        end = f"<!-- END:{m} -->"
        begin_count = body.count(begin)
        end_count = body.count(end)
        if begin_count == 0:
            rpt.add("FATAL", "MARKER_MISSING", f"缺少 {begin}")
        if end_count == 0:
            rpt.add("FATAL", "MARKER_MISSING", f"缺少 {end}")
        if begin_count > 1 or end_count > 1:
            rpt.add("FATAL", "MARKER_DUPLICATE",
                    f"{m} marker 必须唯一，当前 BEGIN={begin_count}, END={end_count}")
        if begin_count == 1 and end_count == 1:
            if body.index(begin) > body.index(end):
                rpt.add("FATAL", "MARKER_ORDER", f"{m} BEGIN 在 END 之后")

def check_pending_questions(data: dict, rpt: Report) -> None:
    pq = data.get("pending_questions") or []
    if not isinstance(pq, list):
        rpt.add("FATAL", "PQ_TYPE", "pending_questions 应为 list")
        return
    seen_ids: set[str] = set()
    for i, q in enumerate(pq):
        if not isinstance(q, dict):
            rpt.add("FATAL", "PQ_ITEM", f"pending_questions[{i}] 不是 dict")
            continue
        for required in ("id", "question", "raised_by", "status"):
            if not q.get(required):
                rpt.add("WARN", "PQ_FIELD",
                        f"pending_questions[{i}] 缺少 {required}")
        qid = q.get("id")
        if qid:
            if not re.match(r"^q\d{3}$", str(qid)):
                rpt.add("WARN", "PQ_ID_FORMAT",
                        f"pending_questions[{i}].id={qid} 建议使用 qNNN 格式")
            if qid in seen_ids:
                rpt.add("FATAL", "PQ_DUPID", f"pending_questions[{i}].id={qid} 重复")
            seen_ids.add(qid)
        if q.get("status") and q["status"] not in VALID_STATUS:
            rpt.add("WARN", "PQ_STATUS",
                    f"pending_questions[{i}].status='{q['status']}' 不在 {sorted(VALID_STATUS)}")
        if q.get("raised_by") and q["raised_by"] not in VALID_RAISED_BY:
            rpt.add("WARN", "PQ_RAISED_BY",
                    f"pending_questions[{i}].raised_by='{q['raised_by']}' 不在 {sorted(VALID_RAISED_BY)}")

def check_files_indexed(data: dict, rpt: Report) -> None:
    fi = data.get("files_indexed") or []
    if not isinstance(fi, list):
        rpt.add("FATAL", "FI_TYPE", "files_indexed 应为 list")
        return
    for i, f in enumerate(fi):
        if not isinstance(f, dict):
            rpt.add("FATAL", "FI_ITEM", f"files_indexed[{i}] 不是 dict")
            continue
        for required in ("path", "sha1"):
            if not f.get(required):
                rpt.add("WARN", "FI_FIELD",
                        f"files_indexed[{i}] 缺少 {required}")

def check_completeness(data: dict, rpt: Report) -> None:
    c = data.get("completeness") or {}
    pct = c.get("filled_required_pct")
    if pct is not None and not (isinstance(pct, int) and 0 <= pct <= 100):
        rpt.add("WARN", "COMP_PCT",
                f"completeness.filled_required_pct={pct} 应为 0–100 整数")


def check_soft_guidance(data: dict, rpt: Report) -> None:
    proj = data.get("project") or {}
    if proj.get("type") == "unknown":
        rpt.add("WARN", "TYPE_UNKNOWN", "project.type=unknown，建议 S0 后尽快确定项目类型")
    brief = data.get("brief") or {}
    if not brief.get("summary"):
        rpt.add("WARN", "BRIEF_SUMMARY", "brief.summary 缺失，建议 S0 至少写一句项目目标")
    low_confidence = data.get("low_confidence_fields") or []
    if isinstance(low_confidence, list) and len(low_confidence) > 5:
        rpt.add("WARN", "LOW_CONFIDENCE_MANY", "low_confidence_fields 超过 5 项，建议集中人工复核")


def check_legacy_fields(data: dict, rpt: Report) -> None:
    if "notion" in data:
        rpt.add("WARN", "LEGACY_NOTION",
                "notion 已从核心 schema 移除；如需外部同步，请放入后续 integrations/ 投影器")

def compute_stats(data: dict, rpt: Report) -> None:
    c = data.get("completeness") or {}
    rpt.stats.update({
        "filled_required_pct": c.get("filled_required_pct"),
        "ready_for": c.get("ready_for"),
        "blocked": c.get("blocked"),
        "pending_count": len(data.get("pending_questions") or []),
        "files_indexed_count": len(data.get("files_indexed") or []),
        "low_confidence_count": len(data.get("low_confidence_fields") or []),
        "project_code": (data.get("project") or {}).get("code"),
        "project_type": (data.get("project") or {}).get("type"),
        "stage": (data.get("project") or {}).get("stage"),
    })

## ---------- 主逻辑 ----------
def resolve_path(arg_code_or_path: str, explicit_path: str | None) -> Path:
    if explicit_path:
        return Path(explicit_path).expanduser().resolve()
    return REPO_ROOT / "projects" / arg_code_or_path / "05_output" / "record.md"

def validate_file(path: Path) -> Report:
    rpt = Report(path=str(path))
    if not path.exists():
        rpt.add("FATAL", "FILE_MISSING", f"文件不存在：{path}")
        return rpt
    text = path.read_text(encoding="utf-8")
    data, body = read_frontmatter(text)
    if data is None:
        rpt.add("FATAL", "FRONTMATTER", "无法解析 YAML frontmatter")
        return rpt

    check_required_fields(data, path, rpt)
    check_markers(body, rpt)
    check_pending_questions(data, rpt)
    check_files_indexed(data, rpt)
    check_completeness(data, rpt)
    check_soft_guidance(data, rpt)
    check_legacy_fields(data, rpt)
    compute_stats(data, rpt)
    return rpt

## ---------- 输出 ----------
def print_human(rpt: Report) -> None:
    print(f"== validate_record :: {rpt.path}")
    if rpt.stats:
        print("  stats:")
        for k, v in rpt.stats.items():
            print(f"    - {k}: {v}")
    if not rpt.issues:
        print("  ✔ 无问题")
        return
    for lvl in ("FATAL", "WARN", "INFO"):
        items = [i for i in rpt.issues if i.level == lvl]
        if not items:
            continue
        print(f"  [{lvl}] x{len(items)}")
        for it in items:
            print(f"    - {it.code}: {it.msg}")

def print_json(rpt: Report) -> None:
    out = {
        "path": rpt.path,
        "fatal": rpt.fatal_count,
        "warn": rpt.warn_count,
        "stats": rpt.stats,
        "issues": [asdict(i) for i in rpt.issues],
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))

## ---------- CLI ----------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="验证 record.md schema")
    p.add_argument("code", nargs="?", default="",
                   help="项目代号；与 --path 二选一")
    p.add_argument("--path", default=None, help="直接指定 record.md 路径")
    p.add_argument("--json", action="store_true", help="机器可读输出")
    args = p.parse_args()
    if not args.code and not args.path:
        p.error("请提供项目代号或 --path")
    return args

def main() -> int:
    args = parse_args()
    try:
        path = resolve_path(args.code, args.path)
    except Exception as e:
        sys.stderr.write(f"ERROR: 路径解析失败 {e}\n")
        return EXIT_IO

    rpt = validate_file(path)
    if args.json:
        print_json(rpt)
    else:
        print_human(rpt)

    if rpt.fatal_count > 0:
        if not any(i.code == "FILE_MISSING" for i in rpt.issues):
            return EXIT_FATAL
        return EXIT_IO
    return EXIT_OK

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Route visual project assets to a configured vision model.

This tool keeps image handling out of the user's hands. S0 can run it after
inventory: if OPENAI_API_KEY and VISION_MODEL are configured, image summaries
are written to 05_output/vision/*.json. If not configured, the tool writes a
clear sidecar explaining the missing configuration and the questions that
should be asked instead.
"""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from inventory import FileRecord, iter_input_files, resolve_project


REPO_ROOT = Path(__file__).resolve().parents[1]
VISION_OUTPUT_DIR = "05_output/vision"
VISION_BUCKETS = {"location_map", "site_photo", "reference"}
VISION_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
DEFAULT_API_BASE = "https://api.openai.com/v1"


@dataclass
class VisionRouteConfig:
    provider: str
    model: str | None
    api_key_present: bool
    api_base: str
    configured: bool


def load_config() -> VisionRouteConfig:
    provider = os.environ.get("VISION_PROVIDER", "openai").strip().lower()
    model = os.environ.get("VISION_MODEL") or os.environ.get("OPENAI_VISION_MODEL")
    api_key = os.environ.get("OPENAI_API_KEY")
    api_base = os.environ.get("OPENAI_API_BASE", DEFAULT_API_BASE).rstrip("/")
    return VisionRouteConfig(
        provider=provider,
        model=model,
        api_key_present=bool(api_key),
        api_base=api_base,
        configured=provider == "openai" and bool(model and api_key),
    )


def visual_records(records: list[FileRecord], buckets: set[str]) -> list[FileRecord]:
    return [
        record
        for record in records
        if record.bucket in buckets
        and record.read_policy == "visual_asset"
        and record.ext.lower() in VISION_EXTS
    ]


def prompt_for(record: FileRecord) -> str:
    if record.bucket == "location_map":
        return (
            "你是建筑设计项目前期资料助手。请识别这张区位图/卫星图，"
            "只输出 JSON，不要输出 Markdown。字段："
            "visual_summary(string), detected_text(array), location_clues(array), "
            "roads_or_landmarks(array), site_marker_description(string|null), "
            "confidence(high|medium|low), needs_review(array)。"
            "要求：不要编造精确坐标、面积或红线；如果只是从图面推断，"
            "必须在 needs_review 中写明需要人工复核。"
        )
    if record.bucket == "site_photo":
        return (
            "你是建筑设计现场踏勘助手。请识别这张现场照片，"
            "只输出 JSON，不要输出 Markdown。字段："
            "visual_summary(string), visible_site_conditions(array), constraints(array), "
            "opportunities(array), confidence(high|medium|low), needs_review(array)。"
            "不要推断不可见的红线、面积或权属。"
        )
    return (
        "你是建筑设计资料整理助手。请识别这张参考图，"
        "只输出 JSON，不要输出 Markdown。字段："
        "visual_summary(string), style_keywords(array), usable_references(array), "
        "confidence(high|medium|low), needs_review(array)。"
    )


def data_url(path: Path) -> str:
    mime = mimetypes.guess_type(str(path))[0] or "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def extract_output_text(payload: dict[str, Any]) -> str:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]
    parts: list[str] = []
    for item in payload.get("output", []) or []:
        for content in item.get("content", []) or []:
            text = content.get("text")
            if isinstance(text, str):
                parts.append(text)
    return "\n".join(parts).strip()


def parse_json_text(text: str) -> dict[str, Any] | None:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:].strip()
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def call_openai_vision(path: Path, record: FileRecord, config: VisionRouteConfig, timeout: int) -> dict[str, Any]:
    api_key = os.environ["OPENAI_API_KEY"]
    body = {
        "model": config.model,
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt_for(record)},
                    {"type": "input_image", "image_url": data_url(path), "detail": "high"},
                ],
            }
        ],
    }
    request = urllib.request.Request(
        f"{config.api_base}/responses",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    output_text = extract_output_text(payload)
    parsed = parse_json_text(output_text)
    return {
        "status": "ok" if parsed else "raw_text_only",
        "model": config.model,
        "summary": parsed,
        "raw_text": output_text if not parsed else None,
        "response_id": payload.get("id"),
    }


def not_configured_result(record: FileRecord, config: VisionRouteConfig) -> dict[str, Any]:
    return {
        "status": "vision_model_not_configured",
        "model": config.model,
        "summary": None,
        "fallback": {
            "action": "do_not_ask_user_to_switch_model",
            "record_as": "visual asset uploaded but not semantically parsed",
            "pending_questions": [
                {
                    "field": "site.address" if record.bucket == "location_map" else None,
                    "question": "请确认图中项目准确位置、地址或坐标。",
                },
                {
                    "field": "site.area_sqm" if record.bucket == "location_map" else None,
                    "question": "请确认红线范围或提供可计算面积的 CAD/DWG/PDF。",
                },
            ],
        },
        "config_hint": "Set OPENAI_API_KEY and VISION_MODEL for automatic image interpretation.",
    }


def error_result(exc: BaseException, config: VisionRouteConfig) -> dict[str, Any]:
    status = "vision_api_error"
    detail = str(exc)
    if isinstance(exc, urllib.error.HTTPError):
        try:
            detail = exc.read().decode("utf-8", errors="replace")
        except Exception:
            detail = str(exc)
    return {
        "status": status,
        "model": config.model,
        "summary": None,
        "error": detail,
        "fallback": {
            "action": "continue_without_user_model_switch",
            "record_as": "visual asset uploaded but vision parsing failed",
        },
    }


def sidecar_name(record: FileRecord) -> str:
    safe = record.path.replace("/", "__").replace("\\", "__")
    return f"{safe}.vision.json"


def analyze_record(project_dir: Path, record: FileRecord, config: VisionRouteConfig, timeout: int) -> dict[str, Any]:
    path = project_dir / record.path
    base: dict[str, Any] = {
        "schema_version": "1.0",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "source": asdict(record),
        "provider": config.provider,
    }
    if not config.configured:
        base.update(not_configured_result(record, config))
        return base
    try:
        base.update(call_openai_vision(path, record, config, timeout))
    except Exception as exc:
        base.update(error_result(exc, config))
    return base


def write_outputs(project_dir: Path, results: list[dict[str, Any]]) -> None:
    out_dir = project_dir / VISION_OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    for result in results:
        record = result["source"]
        target = out_dir / sidecar_name(FileRecord(**record))
        target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    index = {
        "schema_version": "1.0",
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "results": [
            {
                "path": result["source"]["path"],
                "status": result["status"],
                "sidecar": f"{VISION_OUTPUT_DIR}/{sidecar_name(FileRecord(**result['source']))}",
            }
            for result in results
        ],
    }
    (out_dir / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Route visual assets to a configured vision model")
    parser.add_argument("project", help="Project code or path")
    parser.add_argument("--json", action="store_true", help="Print JSON only")
    parser.add_argument("--write", action="store_true", help="Write 05_output/vision/*.json")
    parser.add_argument("--bucket", action="append", choices=sorted(VISION_BUCKETS), help="Limit to one bucket")
    parser.add_argument("--require-config", action="store_true", help="Exit 2 if no vision model is configured")
    parser.add_argument("--timeout", type=int, default=90)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_dir = resolve_project(args.project)
    if not project_dir.exists():
        print(f"ERROR: project not found: {project_dir}", file=sys.stderr)
        return 3

    buckets = set(args.bucket) if args.bucket else VISION_BUCKETS
    config = load_config()
    records = visual_records(iter_input_files(project_dir), buckets)
    results = [analyze_record(project_dir, record, config, args.timeout) for record in records]
    payload: dict[str, Any] = {
        "project_dir": str(project_dir),
        "project_code": project_dir.name,
        "config": asdict(config),
        "visual_asset_count": len(records),
        "results": results,
    }
    if args.write:
        write_outputs(project_dir, results)
        payload["written_to"] = str(project_dir / VISION_OUTPUT_DIR)

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"== vision_route :: {project_dir}")
        print(f"  configured: {config.configured}")
        print(f"  model: {config.model or '(unset)'}")
        print(f"  visual assets: {len(records)}")
        for result in results:
            print(f"  - {result['source']['path']}: {result['status']}")

    if args.require_config and not config.configured:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

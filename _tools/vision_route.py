#!/usr/bin/env python3
"""Route visual project assets to a configured vision model.

This tool keeps image handling out of the user's hands. S0 can run it after
inventory: if a vision provider is configured, image summaries are written to
05_output/vision/*.json. If not configured, the tool writes a clear sidecar
explaining the missing configuration and the questions that should be asked instead.

Supported providers:
- OpenAI (GPT-4o, GPT-4V)
- Anthropic (Claude 3.5 Sonnet, Claude 3 Opus)
- Google (Gemini Pro Vision, Gemini 1.5)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from inventory import FileRecord, iter_input_files, resolve_project
from vision_providers import get_provider, list_providers, VisionProvider


REPO_ROOT = Path(__file__).resolve().parents[1]
VISION_OUTPUT_DIR = "05_output/vision"
VISION_BUCKETS = {"location_map", "site_photo", "reference"}
VISION_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


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


def not_configured_result(record: FileRecord, provider: VisionProvider) -> dict[str, Any]:
    return {
        "status": "vision_model_not_configured",
        "provider": provider.get_config_info(),
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
        "config_hint": "Set VISION_PROVIDER and corresponding API key. Supported: openai, anthropic, google.",
    }


def sidecar_name(record: FileRecord) -> str:
    safe = record.path.replace("/", "__").replace("\\", "__")
    return f"{safe}.vision.json"


def analyze_record(project_dir: Path, record: FileRecord, provider: VisionProvider, timeout: int) -> dict[str, Any]:
    path = project_dir / record.path
    base: dict[str, Any] = {
        "schema_version": "1.0",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "source": asdict(record),
        "provider": provider.get_config_info(),
    }

    if not provider.is_configured():
        base.update(not_configured_result(record, provider))
        return base

    try:
        prompt = prompt_for(record)
        result = provider.analyze_image(path, prompt, timeout)
        base.update(result)
    except Exception as exc:
        base.update({
            "status": "vision_api_error",
            "provider": provider.get_config_info(),
            "summary": None,
            "error": str(exc),
            "fallback": {
                "action": "continue_without_user_model_switch",
                "record_as": "visual asset uploaded but vision parsing failed",
            },
        })

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
    parser.add_argument("project", nargs="?", help="Project code or path")
    parser.add_argument("--json", action="store_true", help="Print JSON only")
    parser.add_argument("--write", action="store_true", help="Write 05_output/vision/*.json")
    parser.add_argument("--bucket", action="append", choices=sorted(VISION_BUCKETS), help="Limit to one bucket")
    parser.add_argument("--require-config", action="store_true", help="Exit 2 if no vision model is configured")
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--provider", help="Vision provider to use (openai, anthropic, google, auto)")
    parser.add_argument("--list-providers", action="store_true", help="List all providers and exit")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    # 列出 providers
    if args.list_providers:
        providers = list_providers()
        if args.json:
            print(json.dumps(providers, ensure_ascii=False, indent=2))
        else:
            print("== Available vision providers ==")
            for p in providers:
                status = "configured" if p["configured"] else "not configured"
                print(f"  {p['name']}: {status}")
                for k, v in p["config_info"].items():
                    if k not in ("provider", "configured"):
                        print(f"    {k}: {v}")
        return 0

    project_dir = resolve_project(args.project)
    if not project_dir.exists():
        print(f"ERROR: project not found: {project_dir}", file=sys.stderr)
        return 3

    buckets = set(args.bucket) if args.bucket else VISION_BUCKETS
    provider = get_provider(args.provider)
    records = visual_records(iter_input_files(project_dir), buckets)
    results = [analyze_record(project_dir, record, provider, args.timeout) for record in records]
    payload: dict[str, Any] = {
        "project_dir": str(project_dir),
        "project_code": project_dir.name,
        "provider": provider.get_config_info(),
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
        print(f"  provider: {provider.get_provider_name()}")
        print(f"  configured: {provider.is_configured()}")
        print(f"  visual assets: {len(records)}")
        for result in results:
            print(f"  - {result['source']['path']}: {result['status']}")

    if args.require_config and not provider.is_configured():
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

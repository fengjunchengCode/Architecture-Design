#!/usr/bin/env python3
"""Suggest semantic roles for CAD control point candidates using vision routing."""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Any

import ezdxf
from PIL import Image, ImageDraw, ImageFont

from cad_preview import (
    LAYER_COLORS,
    bbox,
    choose_boundary,
    choose_dxf,
    collect_geometry,
    read_probe,
    resolve_project,
)
from vision_providers import get_provider

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = REPO_ROOT / ".env"
CANDIDATES_REL = Path("05_output/cad/control_point_candidates.json")
SEMANTICS_REL = Path("05_output/cad/control_point_candidate_semantics.json")
VISION_IMAGE_REL = Path("05_output/cad/site_preview_for_vision.png")
COMPOSITE_IMAGE_REL = Path("05_output/cad/cad_site_composite_for_vision.png")
AMAP_CONTEXT_REL = Path("05_output/amap/s1_map_context.json")
CONTROL_POINTS_REL = Path("05_output/amap/control_points.json")
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}

FEATURE_TO_LABEL = {
    "redline_corner": "红线配准点",
    "road_intersection": "道路交叉口",
    "road_centerline": "道路中心线",
    "road_edge": "道路边线",
    "bridge_endpoint": "桥头/桥端",
    "bridge_center": "桥中心",
    "water_edge": "水系岸线",
    "building_corner": "建筑角点",
    "visible_landmark": "固定地物",
    "other": "候选参照点",
}
VALID_FEATURES = set(FEATURE_TO_LABEL)
VALID_PURPOSES = {"registration", "road_binding", "entrance_check", "water_binding", "reference_only"}
VALID_CONFIDENCE = {"low", "medium", "high"}


def load_env_file(path: Path = ENV_FILE) -> list[str]:
    if not path.exists():
        return []
    loaded: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or key in os.environ:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ[key] = value
        loaded.append(key)
    return loaded


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def project_rel(path: Path, project_dir: Path) -> str:
    try:
        return path.relative_to(project_dir).as_posix()
    except ValueError:
        return str(path)


def project_point(points: list[tuple[float, float]], width: int, height: int, margin: int):
    metrics = bbox(points)
    min_x, min_y = metrics["min"]
    max_x, max_y = metrics["max"]
    span_x = max(max_x - min_x, 1.0)
    span_y = max(max_y - min_y, 1.0)
    scale = min((width - margin * 2) / span_x, (height - margin * 2) / span_y)

    def transform(point: tuple[float, float]) -> tuple[float, float]:
        x = margin + (point[0] - min_x) * scale
        y = height - margin - (point[1] - min_y) * scale
        return x, y

    return transform


def render_png(project_dir: Path, width: int = 1400, height: int = 980) -> Path:
    report = read_probe(project_dir)
    dxf_path, _ = choose_dxf(project_dir, report)
    doc = ezdxf.readfile(dxf_path)
    drawables, closed, all_points = collect_geometry(doc)
    boundary = choose_boundary(closed, all_points)
    candidate_data = read_json(project_dir / CANDIDATES_REL)
    candidates = candidate_data.get("candidates", [])
    if not all_points:
        raise RuntimeError("CAD preview has no drawable points")

    transform = project_point(all_points, width, height, 34)
    image = Image.new("RGB", (width, height), "#fbfaf7")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()

    for item in drawables:
        raw_points = item.get("points") or []
        if len(raw_points) < 2:
            continue
        points = [transform((float(x), float(y))) for x, y in raw_points]
        color = LAYER_COLORS.get(str(item.get("layer")), "#6b7280")
        if item.get("closed") and len(points) >= 3:
            draw.line(points + [points[0]], fill=color, width=2)
        else:
            draw.line(points, fill=color, width=1)

    if boundary:
        boundary_points = [transform((float(x), float(y))) for x, y in boundary.get("points", [])]
        if len(boundary_points) >= 3:
            draw.line(boundary_points + [boundary_points[0]], fill="#b91c1c", width=5)

    for candidate in candidates:
        point = candidate.get("cad_point") or {}
        try:
            x, y = transform((float(point["x"]), float(point["y"])))
        except Exception:
            continue
        label = str(candidate.get("label") or candidate.get("id") or "")
        r = 8
        draw.ellipse((x - r, y - r, x + r, y + r), fill="#facc15", outline="#111827", width=2)
        draw.rectangle((x + 10, y - 11, x + 74, y + 7), fill="#ffffff", outline="#111827")
        draw.text((x + 14, y - 9), label, fill="#111827", font=font)

    out = project_dir / VISION_IMAGE_REL
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out)
    return out


def location_image_paths(project_dir: Path, limit: int = 3) -> list[Path]:
    site_root = project_dir / "02_site"
    if not site_root.exists():
        return []
    preferred_tokens = ("区位", "卫星", "航拍", "satellite", "map")
    roots: list[Path] = []
    for child in site_root.iterdir():
        if child.is_dir() and any(token in child.name.lower() for token in preferred_tokens):
            roots.append(child)
    if not roots:
        fallback = site_root / "区位图"
        if fallback.exists():
            roots.append(fallback)

    paths: list[Path] = []
    for root in roots:
        paths.extend(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in IMAGE_EXTS)

    def sort_key(path: Path) -> tuple[int, int, str]:
        text = f"{path.parent.name} {path.name}".lower()
        priority = 0 if any(token in text for token in ("卫星", "航拍", "satellite")) else 1
        try:
            size = path.stat().st_size
        except OSError:
            size = 0
        return (priority, -size, path.name)

    unique = list(dict.fromkeys(sorted(paths, key=sort_key)))
    return unique[:limit]


def location_vision_context(project_dir: Path, limit: int = 3) -> list[dict[str, Any]]:
    vision_dir = project_dir / "05_output" / "vision"
    if not vision_dir.exists():
        return []
    tokens = ("区位", "卫星", "航拍", "location", "satellite", "map")
    rows: list[dict[str, Any]] = []
    for path in sorted(vision_dir.glob("*.vision.json")):
        text = path.name.lower()
        if not any(token in text for token in tokens):
            continue
        data = read_json(path)
        if not data:
            continue
        summary = data.get("summary") or {}
        if not isinstance(summary, dict):
            summary = {}
        rows.append(
            {
                "file": path.name,
                "status": data.get("status"),
                "source_path": (data.get("source") or {}).get("path"),
                "visual_summary": summary.get("visual_summary"),
                "detected_text": (summary.get("detected_text") or [])[:12],
                "roads_or_landmarks": (summary.get("roads_or_landmarks") or [])[:12],
                "site_marker_description": summary.get("site_marker_description"),
                "confidence": summary.get("confidence"),
                "needs_review": (summary.get("needs_review") or [])[:4],
            }
        )
        if len(rows) >= limit:
            break
    return rows


def paste_fit(canvas: Image.Image, source_path: Path, box: tuple[int, int, int, int], label: str) -> None:
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    x0, y0, x1, y1 = box
    draw.rectangle(box, fill="#ffffff", outline="#d1d5db")
    draw.text((x0 + 12, y0 + 10), label, fill="#111827", font=font)
    image_box = (x0 + 12, y0 + 32, x1 - 12, y1 - 12)
    max_size = (max(image_box[2] - image_box[0], 1), max(image_box[3] - image_box[1], 1))
    try:
        image = Image.open(source_path).convert("RGB")
    except Exception:
        draw.text((image_box[0], image_box[1]), f"Cannot open {source_path.name}", fill="#b91c1c", font=font)
        return
    resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
    image.thumbnail(max_size, resample)
    px = image_box[0] + (max_size[0] - image.width) // 2
    py = image_box[1] + (max_size[1] - image.height) // 2
    canvas.paste(image, (px, py))


def make_composite_image(project_dir: Path, cad_image_path: Path, location_images: list[Path]) -> Path:
    if not location_images:
        return cad_image_path
    out = project_dir / COMPOSITE_IMAGE_REL
    width = 2048
    height = 1120
    left_w = 1420
    margin = 24
    gap = 18
    canvas = Image.new("RGB", (width, height), "#f8fafc")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    draw.text((margin, 14), "CAD preview: yellow labels are candidate control points", fill="#111827", font=font)
    draw.text((left_w + margin, 14), "Location / satellite references uploaded for S1", fill="#111827", font=font)
    paste_fit(canvas, cad_image_path, (margin, 38, left_w - margin, height - margin), "CAD preview")

    slot_count = max(1, len(location_images))
    right_x0 = left_w + margin
    right_x1 = width - margin
    available_h = height - 38 - margin - gap * (slot_count - 1)
    slot_h = max(220, available_h // slot_count)
    y = 38
    for index, image_path in enumerate(location_images, start=1):
        paste_fit(canvas, image_path, (right_x0, y, right_x1, min(y + slot_h, height - margin)), f"Location map {index}: {image_path.name}")
        y += slot_h + gap

    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out)
    return out


def amap_context_summary(project_dir: Path) -> dict[str, Any]:
    context = read_json(project_dir / AMAP_CONTEXT_REL)
    if not context:
        return {}
    map_context = context.get("map_context") or {}
    regeo = map_context.get("regeo") or {}
    return {
        "location": (context.get("location") or {}).get("amap_gcj02"),
        "address": regeo.get("formatted_address"),
        "roads": regeo.get("roads", []),
        "road_intersections": regeo.get("road_intersections", []),
        "nearby_pois": regeo.get("nearby_pois", [])[:8],
        "keyword_context": {
            key: (value or {}).get("items", [])[:5]
            for key, value in (map_context.get("keyword_context") or {}).items()
            if isinstance(value, dict)
        },
    }


def default_candidate(candidate: dict[str, Any], reason: str, source: str) -> dict[str, Any]:
    feature_type = candidate.get("feature_type") or "redline_corner"
    if feature_type not in VALID_FEATURES:
        feature_type = "other"
    purpose = candidate.get("purpose") or "registration"
    if purpose not in VALID_PURPOSES:
        purpose = "registration"
    confidence = candidate.get("confidence") or "medium"
    if confidence not in VALID_CONFIDENCE:
        confidence = "medium"
    return {
        "id": candidate.get("id"),
        "label": candidate.get("label") or candidate.get("id"),
        "feature_type": feature_type,
        "feature_name": candidate.get("feature_name"),
        "purpose": purpose,
        "confidence": confidence,
        "role_label": FEATURE_TO_LABEL.get(feature_type, "候选参照点"),
        "reason": reason,
        "note": candidate.get("note"),
        "suggestion_source": source,
    }


def fallback_suggestions(project_dir: Path, reason: str, source: str = "fallback") -> list[dict[str, Any]]:
    data = read_json(project_dir / CANDIDATES_REL)
    candidates = data.get("candidates", []) if isinstance(data.get("candidates"), list) else []
    return [default_candidate(candidate, reason, source) for candidate in candidates]


def prompt_for_candidates(project_dir: Path) -> str:
    candidate_data = read_json(project_dir / CANDIDATES_REL)
    candidates = candidate_data.get("candidates", [])
    context = amap_context_summary(project_dir)
    location_images = [project_rel(path, project_dir) for path in location_image_paths(project_dir)]
    location_context = location_vision_context(project_dir)
    compact_candidates = [
        {
            "id": item.get("id"),
            "label": item.get("label"),
            "cad_point": item.get("cad_point"),
            "source_layer": item.get("source_layer"),
            "feature_type": item.get("feature_type"),
            "note": item.get("note"),
        }
        for item in candidates
    ]
    return (
        "你是建筑总图前期资料助手。请阅读这张综合图：左侧是 CAD 预览，黄色标签是候选 CAD 控制点；"
        "右侧是用户上传的区位图或卫星图。任务不是泛泛描述图片，而是尝试判断 CAD 候选点与真实道路、桥梁、水系、地块边界的对应关系。\n"
        "判断规则：只有当 CAD 图形特征和区位/卫星图或高德上下文能相互支持时，才把候选点标为 road_intersection、road_edge、bridge_endpoint、water_edge 等；"
        "如果只能从 CAD 图层猜测，confidence 用 low 或 medium；如果无法对应真实地物，保守保留 redline_corner/registration。"
        "不要编造看不见或上下文没有出现的道路名；道路名只能来自高德上下文、区位图文字或 sidecar 摘要。\n"
        "只能输出 JSON，不要输出 Markdown。"
        "输出格式："
        "{"
        '"candidates":[{"id":"CAD-01","feature_type":"redline_corner|road_intersection|road_centerline|road_edge|bridge_endpoint|bridge_center|water_edge|building_corner|visible_landmark|other","purpose":"registration|road_binding|entrance_check|water_binding|reference_only","feature_name":string|null,"confidence":"low|medium|high","role_label":string,"reason":string}],'
        '"global_findings":[string],"needs_user_pick":[string]'
        "}\n"
        f"候选点：{json.dumps(compact_candidates, ensure_ascii=False)}\n"
        f"高德上下文：{json.dumps(context, ensure_ascii=False)}\n"
        f"纳入综合图的区位/卫星图：{json.dumps(location_images, ensure_ascii=False)}\n"
        f"既有区位图视觉 sidecar 摘要：{json.dumps(location_context, ensure_ascii=False)}"
    )


def coerce_suggestions(project_dir: Path, vision_summary: dict[str, Any], source: str) -> list[dict[str, Any]]:
    defaults = {item["id"]: item for item in fallback_suggestions(project_dir, "默认按 CAD 红线候选点处理。", "fallback")}
    out: list[dict[str, Any]] = []
    rows = vision_summary.get("candidates") if isinstance(vision_summary, dict) else None
    if not isinstance(rows, list):
        return list(defaults.values())
    for row in rows:
        if not isinstance(row, dict):
            continue
        item_id = str(row.get("id") or row.get("label") or "").strip()
        base = defaults.get(item_id)
        if not base:
            continue
        feature_type = str(row.get("feature_type") or base["feature_type"])
        purpose = str(row.get("purpose") or base["purpose"])
        confidence = str(row.get("confidence") or base["confidence"])
        if feature_type not in VALID_FEATURES:
            feature_type = base["feature_type"]
        if purpose not in VALID_PURPOSES:
            purpose = base["purpose"]
        if confidence not in VALID_CONFIDENCE:
            confidence = base["confidence"]
        role_label = row.get("role_label") or FEATURE_TO_LABEL.get(feature_type, base["role_label"])
        if not any("\u4e00" <= char <= "\u9fff" for char in str(role_label)):
            role_label = FEATURE_TO_LABEL.get(feature_type, base["role_label"])
        out.append(
            {
                **base,
                "feature_type": feature_type,
                "purpose": purpose,
                "confidence": confidence,
                "feature_name": row.get("feature_name") or base.get("feature_name"),
                "role_label": role_label,
                "reason": row.get("reason") or base["reason"],
                "suggestion_source": source,
            }
        )
    seen = {item["id"] for item in out}
    out.extend(item for item_id, item in defaults.items() if item_id not in seen)
    return out


def build_payload(project_dir: Path, provider_name: str | None, timeout: int) -> dict[str, Any]:
    loaded_env = load_env_file()
    cad_image_path = render_png(project_dir)
    location_images = location_image_paths(project_dir)
    image_path = make_composite_image(project_dir, cad_image_path, location_images)
    provider = get_provider(provider_name)
    provider_info = provider.get_config_info()
    base: dict[str, Any] = {
        "schema_version": "1.0",
        "status": "ok",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "project_code": project_dir.name,
        "env_loaded": loaded_env,
        "vision_image": project_rel(image_path, project_dir),
        "cad_vision_image": project_rel(cad_image_path, project_dir),
        "location_images": [project_rel(path, project_dir) for path in location_images],
        "location_vision_context": location_vision_context(project_dir),
        "provider": provider_info,
    }
    if not provider.is_configured():
        reason = "视觉模型未配置，候选点先按 CAD 红线几何保守标注。"
        base.update(
            {
                "status": "vision_model_not_configured",
                "candidates": fallback_suggestions(project_dir, reason),
                "vision_result": None,
                "fallback_reason": reason,
            }
        )
        return base

    result = provider.analyze_image(image_path, prompt_for_candidates(project_dir), timeout)
    if result.get("status") != "ok" or not isinstance(result.get("summary"), dict):
        reason = "视觉模型未返回可解析 JSON，候选点先按 CAD 红线几何保守标注。"
        base.update(
            {
                "status": "vision_fallback",
                "candidates": fallback_suggestions(project_dir, reason),
                "vision_result": result,
                "fallback_reason": reason,
            }
        )
        return base
    base.update(
        {
            "status": "ok",
            "candidates": coerce_suggestions(project_dir, result["summary"], "vision_model"),
            "vision_result": {
                "status": result.get("status"),
                "model": result.get("model"),
                "response_id": result.get("response_id"),
                "global_findings": result["summary"].get("global_findings"),
                "needs_user_pick": result["summary"].get("needs_user_pick"),
            },
        }
    )
    return base


def write_payload(project_dir: Path, payload: dict[str, Any]) -> Path:
    target = project_dir / SEMANTICS_REL
    target.parent.mkdir(parents=True, exist_ok=True)
    out = {
        "schema_version": "1.0",
        "updated_at": payload.get("created_at"),
        "project": project_dir.name,
        "status": payload.get("status"),
        "provider": payload.get("provider"),
        "vision_image": payload.get("vision_image"),
        "cad_vision_image": payload.get("cad_vision_image"),
        "location_images": payload.get("location_images", []),
        "location_vision_context": payload.get("location_vision_context", []),
        "vision_result": payload.get("vision_result"),
        "fallback_reason": payload.get("fallback_reason"),
        "candidates": payload.get("candidates", []),
        "agent_note": "AI-assisted semantic suggestions for CAD-side candidate points. User still picks exact AMap coordinates.",
    }
    target.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Suggest CAD candidate semantics for S2")
    parser.add_argument("project", help="Project code or path")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--provider", help="Vision provider: openai, anthropic, google, auto")
    parser.add_argument("--timeout", type=int, default=60)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_dir = resolve_project(args.project)
    if not project_dir.exists():
        print(f"ERROR: project not found: {project_dir}", file=sys.stderr)
        return 3
    try:
        payload = build_payload(project_dir, args.provider, args.timeout)
        if args.write:
            payload["written_to"] = str(write_payload(project_dir, payload))
    except Exception as exc:
        payload = {
            "schema_version": "1.0",
            "status": "error",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "project_code": project_dir.name,
            "error": str(exc),
            "candidates": fallback_suggestions(project_dir, f"语义建议生成失败：{exc}", "fallback"),
        }
        if args.write:
            try:
                payload["written_to"] = str(write_payload(project_dir, payload))
            except Exception:
                pass
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"== cad_semantics :: {project_dir}")
        print(f"  status: {payload.get('status')}")
        print(f"  candidates: {len(payload.get('candidates', []))}")
    return 0 if payload.get("status") in {"ok", "vision_model_not_configured", "vision_fallback"} else 2


if __name__ == "__main__":
    sys.exit(main())

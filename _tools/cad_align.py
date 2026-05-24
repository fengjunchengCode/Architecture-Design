#!/usr/bin/env python3
"""Evaluate CAD-to-AMap control point alignment quality for S2."""
from __future__ import annotations

import argparse
import itertools
import json
import math
import sys
import time
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECTS_DIR = REPO_ROOT / "projects"
INPUT_REL = Path("05_output/amap/control_points.json")
OUTPUT_REL = Path("05_output/amap/cad_alignment_report.json")
CANDIDATE_REL = Path("05_output/cad/control_point_candidates.json")
MIGRATION_REPORT_DIR_REL = Path("05_output/amap")
EARTH_RADIUS_M = 6378137.0
SAME_GEOMETRY_THRESHOLD = 0.01
NEAR_GEOMETRY_THRESHOLD = 1.0


def resolve_project(code_or_path: str) -> Path:
    direct = Path(code_or_path).expanduser()
    if direct.exists():
        return direct.resolve()
    return (PROJECTS_DIR / code_or_path).resolve()


def load_control_points_payload(project_dir: Path, input_path: Path | None = None) -> tuple[dict[str, Any], Path]:
    path = input_path or project_dir / INPUT_REL
    if not path.exists():
        raise FileNotFoundError(f"{path.as_posix()} 不存在")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("control_points.json 必须是 JSON object")
    return data, path


def load_current_candidate_set_id(project_dir: Path) -> str | None:
    path = project_dir / CANDIDATE_REL
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    value = data.get("candidate_set_id")
    return str(value) if value else None


def candidate_set_mismatch(current: str | None, at_save: object) -> bool:
    return bool(current) and str(at_save or "") != current


def stale_control_points_report(project_dir: Path, current: str | None, at_save: object) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "status": "stale_control_points",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "project_code": project_dir.name,
        "candidate_set_id_current": current,
        "candidate_set_id_at_save": str(at_save) if at_save else None,
        "alignment_report": None,
        "recommendations": [
            "当前 control_points.json 保存时的候选集 ID 缺失或已过期，不能继续静默用于 CAD/高德配准。",
            "请先生成迁移诊断，确认旧 CAD 点是否能映射到当前候选点；必要时归档旧控制点后重新选择。",
        ],
    }


def extract_points(data: dict[str, Any]) -> list[dict[str, Any]]:
    points = data.get("control_points", [])
    if not isinstance(points, list):
        raise ValueError("control_points.json 中 control_points 必须是数组")
    cleaned = []
    for index, item in enumerate(points, start=1):
        label = str(item.get("label") or f"CP{index}")
        cad = item.get("cad_point")
        amap = item.get("amap_gcj02")
        if not isinstance(cad, dict) or not isinstance(amap, list) or len(amap) != 2:
            continue
        cleaned.append(
            {
                "label": label,
                "cad": [float(cad["x"]), float(cad["y"])],
                "amap_gcj02": [float(amap[0]), float(amap[1])],
                "feature_type": item.get("feature_type") or ("redline_corner" if label.upper().startswith("CAD-") else "other"),
                "feature_name": item.get("feature_name"),
                "purpose": item.get("purpose") or "registration",
                "confidence": item.get("confidence") or "medium",
                "note": item.get("note"),
            }
        )
    return cleaned


def load_points(project_dir: Path, input_path: Path | None = None) -> list[dict[str, Any]]:
    data, _ = load_control_points_payload(project_dir, input_path)
    return extract_points(data)


def ll_to_local_m(points: list[dict[str, Any]]) -> tuple[list[list[float]], dict[str, float]]:
    lon0 = sum(point["amap_gcj02"][0] for point in points) / len(points)
    lat0 = sum(point["amap_gcj02"][1] for point in points) / len(points)
    out = []
    for point in points:
        lon, lat = point["amap_gcj02"]
        x = math.radians(lon - lon0) * EARTH_RADIUS_M * math.cos(math.radians(lat0))
        y = math.radians(lat - lat0) * EARTH_RADIUS_M
        out.append([x, y])
    return out, {"lon": lon0, "lat": lat0}


def fit_similarity(src: list[list[float]], dst: list[list[float]], indices: list[int]) -> dict[str, Any]:
    if len(indices) < 2:
        raise ValueError("at least two points are required")
    src_center = [
        sum(src[i][0] for i in indices) / len(indices),
        sum(src[i][1] for i in indices) / len(indices),
    ]
    dst_center = [
        sum(dst[i][0] for i in indices) / len(indices),
        sum(dst[i][1] for i in indices) / len(indices),
    ]
    source = [[src[i][0] - src_center[0], src[i][1] - src_center[1]] for i in indices]
    target = [[dst[i][0] - dst_center[0], dst[i][1] - dst_center[1]] for i in indices]
    denom = sum(point[0] ** 2 + point[1] ** 2 for point in source)
    if denom <= 1e-12:
        raise ValueError("source control points are degenerate")
    a = sum(source[i][0] * target[i][0] + source[i][1] * target[i][1] for i in range(len(indices))) / denom
    b = sum(source[i][0] * target[i][1] - source[i][1] * target[i][0] for i in range(len(indices))) / denom
    tx = dst_center[0] - (a * src_center[0] - b * src_center[1])
    ty = dst_center[1] - (b * src_center[0] + a * src_center[1])

    residuals = []
    predictions = []
    deltas = []
    for point, target_point in zip(src, dst):
        x = a * point[0] - b * point[1] + tx
        y = b * point[0] + a * point[1] + ty
        dx = x - target_point[0]
        dy = y - target_point[1]
        predictions.append([x, y])
        deltas.append([dx, dy])
        residuals.append(math.hypot(dx, dy))
    fit_residuals = [residuals[i] for i in indices]
    rms = math.sqrt(sum(item * item for item in fit_residuals) / len(fit_residuals))
    return {
        "indices": indices,
        "scale": math.hypot(a, b),
        "rotation_deg": math.degrees(math.atan2(b, a)),
        "translation_local_m": [tx, ty],
        "rms_error_m": rms,
        "max_error_m": max(fit_residuals),
        "residuals_m": residuals,
        "predicted_local_m": predictions,
        "delta_local_m": deltas,
    }


def find_duplicate_map_points(points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[tuple[float, float], list[str]] = {}
    for point in points:
        key = tuple(point["amap_gcj02"])
        seen.setdefault(key, []).append(point["label"])
    return [
        {"amap_gcj02": list(key), "labels": labels}
        for key, labels in seen.items()
        if len(labels) > 1
    ]


def best_inlier_fit(
    src: list[list[float]],
    dst: list[list[float]],
    threshold_m: float,
) -> tuple[dict[str, Any] | None, list[int]]:
    best: tuple[tuple[int, float, float], dict[str, Any], list[int]] | None = None
    point_count = len(src)
    for size in range(3, point_count + 1):
        for indices in itertools.combinations(range(point_count), size):
            try:
                fit = fit_similarity(src, dst, list(indices))
            except ValueError:
                continue
            inliers = [index for index, value in enumerate(fit["residuals_m"]) if value <= threshold_m]
            score = (
                len(inliers),
                -sum(fit["residuals_m"][index] ** 2 for index in inliers),
                -fit["rms_error_m"],
            )
            if best is None or score > best[0]:
                best = (score, fit, inliers)
    if best is None:
        return None, []
    return best[1], best[2]


def quality(point_count: int, inlier_count: int, inlier_rms: float | None, duplicates: list[dict[str, Any]]) -> str:
    if point_count < 3:
        return "insufficient"
    if inlier_rms is None:
        return "failed"
    if inlier_count == point_count and inlier_rms <= 3 and not duplicates:
        return "aligned_high"
    if inlier_count >= 3 and inlier_rms <= 5:
        return "aligned_partial"
    return "weak"


def local_m_to_ll(point: list[float], origin: dict[str, float]) -> list[float]:
    lon0 = origin["lon"]
    lat0 = origin["lat"]
    lon = lon0 + math.degrees(point[0] / (EARTH_RADIUS_M * math.cos(math.radians(lat0))))
    lat = lat0 + math.degrees(point[1] / EARTH_RADIUS_M)
    return [lon, lat]


def residual_rows(points: list[dict[str, Any]], fit: dict[str, Any], origin: dict[str, float]) -> list[dict[str, Any]]:
    rows = []
    for index, value in enumerate(fit["residuals_m"]):
        delta = fit["delta_local_m"][index]
        rows.append(
            {
                "label": points[index]["label"],
                "feature_type": points[index].get("feature_type"),
                "feature_name": points[index].get("feature_name"),
                "purpose": points[index].get("purpose"),
                "confidence": points[index].get("confidence"),
                "error_m": value,
                "delta_east_m": delta[0],
                "delta_north_m": delta[1],
                "expected_gcj02": local_m_to_ll(fit["predicted_local_m"][index], origin),
                "provided_gcj02": points[index]["amap_gcj02"],
            }
        )
    return rows


def build_report(
    project_dir: Path,
    threshold_m: float,
    input_path: Path | None = None,
    allow_stale: bool = False,
) -> dict[str, Any]:
    payload, loaded_path = load_control_points_payload(project_dir, input_path)
    candidate_set_id_current = load_current_candidate_set_id(project_dir)
    candidate_set_id_at_save = payload.get("candidate_set_id_at_save")
    if not allow_stale and candidate_set_mismatch(candidate_set_id_current, candidate_set_id_at_save):
        return stale_control_points_report(project_dir, candidate_set_id_current, candidate_set_id_at_save)

    points = extract_points(payload)
    if len(points) < 3:
        return {
            "schema_version": "1.0",
            "status": "insufficient_points",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "project_code": project_dir.name,
            "candidate_set_id_current": candidate_set_id_current,
            "candidate_set_id_at_save": str(candidate_set_id_at_save) if candidate_set_id_at_save else None,
            "point_count": len(points),
            "required": "At least 3 CAD/AMap point pairs are required.",
        }
    src = [point["cad"] for point in points]
    dst, origin = ll_to_local_m(points)
    duplicates = find_duplicate_map_points(points)
    all_fit = fit_similarity(src, dst, list(range(len(points))))
    best_fit, inliers = best_inlier_fit(src, dst, threshold_m)
    inlier_rms = None
    if best_fit is not None and inliers:
        inlier_rms = math.sqrt(sum(best_fit["residuals_m"][index] ** 2 for index in inliers) / len(inliers))
    outliers = [index for index in range(len(points)) if index not in inliers]
    return {
        "schema_version": "1.0",
        "status": "ok",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "project_code": project_dir.name,
        "input": loaded_path.as_posix() if input_path else INPUT_REL.as_posix(),
        "candidate_set_id_current": candidate_set_id_current,
        "candidate_set_id_at_save": str(candidate_set_id_at_save) if candidate_set_id_at_save else None,
        "coordinate_system": {
            "source": "CAD drawing coordinates",
            "target": "AMap GCJ-02 converted to local tangent meters for residual checks",
            "local_origin_gcj02": origin,
        },
        "point_count": len(points),
        "inlier_threshold_m": threshold_m,
        "quality": quality(len(points), len(inliers), inlier_rms, duplicates),
        "duplicates": duplicates,
        "all_points_fit": {
            **{key: all_fit[key] for key in ("scale", "rotation_deg", "translation_local_m", "rms_error_m", "max_error_m")},
            "residuals": residual_rows(points, all_fit, origin),
        },
        "best_fit": None
        if best_fit is None
        else {
            **{key: best_fit[key] for key in ("scale", "rotation_deg", "translation_local_m", "rms_error_m", "max_error_m")},
            "inlier_labels": [points[index]["label"] for index in inliers],
            "outlier_labels": [points[index]["label"] for index in outliers],
            "residuals": residual_rows(points, best_fit, origin),
        },
        "recommendations": recommendations(points, duplicates, outliers, inliers),
    }


def recommendations(
    points: list[dict[str, Any]],
    duplicates: list[dict[str, Any]],
    outliers: list[int],
    inliers: list[int],
) -> list[str]:
    recs = []
    if duplicates:
        labels = ", ".join("/".join(item["labels"]) for item in duplicates)
        recs.append(f"复核重复高德坐标：{labels}。不同 CAD 点不应对应同一个地图点。")
    if outliers:
        recs.append("优先重选或删除高残差点：" + "、".join(points[index]["label"] for index in outliers))
    if len(inliers) >= 3:
        recs.append("可用内点先做粗配准判断，但不要把入口/道路边界写成高置信结论。")
        semantic_types = {"road_intersection", "road_centerline", "road_edge", "bridge_endpoint", "bridge_center", "water_edge"}
        semantic_purposes = {"road_binding", "entrance_check", "water_binding"}
        semantic_points = [
            point
            for point in points
            if point.get("feature_type") in semantic_types or point.get("purpose") in semantic_purposes
        ]
        if not semantic_points:
            recs.append("当前控制点主要用于几何配准；若要判断道路、桥梁、入口或水系落边，请补充道路交叉口、道路边线、桥头两端或水岸等语义控制点。")
    else:
        recs.append("请至少保留 3 个分布均匀、可在高德地图明确识别的对应点。")
    return recs


def write_report(project_dir: Path, report: dict[str, Any]) -> Path:
    out = project_dir / OUTPUT_REL
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def load_candidate_points(project_dir: Path) -> list[dict[str, Any]]:
    path = project_dir / CANDIDATE_REL
    if not path.exists():
        raise FileNotFoundError(f"{path.as_posix()} 不存在")
    data = json.loads(path.read_text(encoding="utf-8"))
    candidates = data.get("candidates", [])
    if not isinstance(candidates, list):
        raise ValueError("control_point_candidates.json 中 candidates 必须是数组")
    out = []
    for item in candidates:
        if not isinstance(item, dict) or not isinstance(item.get("cad_point"), dict):
            continue
        cad = item["cad_point"]
        out.append(
            {
                "id": str(item.get("id") or item.get("label") or ""),
                "label": str(item.get("label") or item.get("id") or ""),
                "cad": [float(cad["x"]), float(cad["y"])],
                "feature_type": item.get("feature_type"),
                "purpose": item.get("purpose"),
                "source_handle": item.get("source_handle"),
                "source_layer": item.get("source_layer"),
            }
        )
    return out


def nearest_candidate(point: dict[str, Any], candidates: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, float | None]:
    if not candidates:
        return None, None
    x, y = point["cad"]
    best: tuple[dict[str, Any], float] | None = None
    for candidate in candidates:
        distance = math.hypot(x - candidate["cad"][0], y - candidate["cad"][1])
        if best is None or distance < best[1]:
            best = (candidate, distance)
    return best if best else (None, None)


def migration_match_type(distance: float | None) -> str:
    if distance is None:
        return "unmatched"
    if distance <= SAME_GEOMETRY_THRESHOLD:
        return "same_geometry_match"
    if distance <= NEAR_GEOMETRY_THRESHOLD:
        return "near_geometry_match"
    return "unmatched"


def migration_recommendation(
    point: dict[str, Any],
    candidate: dict[str, Any] | None,
    match_type: str,
    alignment_status: str,
) -> str:
    if match_type == "unmatched":
        return "旧 CAD 坐标不在当前候选点集内；不要自动迁移，请在 S2 UI 中重新选择候选点并拾取高德坐标。"
    candidate_id = candidate.get("id") if candidate else None
    if alignment_status == "alignment_outlier":
        return "几何上能匹配当前候选点，但旧高德坐标在配准中是外点；建议重新拾取该点。"
    if candidate_id and candidate_id != point["label"]:
        return f"旧 label 与当前候选编号不一致（应对应 {candidate_id}）；建议人工确认后重新保存。"
    if match_type == "near_geometry_match":
        return "CAD 坐标接近当前候选点但不是同一点；建议人工确认后再迁移。"
    return "可作为迁移参考，但仍建议通过 UI 重新保存以写入最新 candidate_set_id_at_save。"


def build_migration_report(project_dir: Path, threshold_m: float, input_path: Path | None = None) -> dict[str, Any]:
    payload, loaded_path = load_control_points_payload(project_dir, input_path)
    points = extract_points(payload)
    candidates = load_candidate_points(project_dir)
    candidate_set_id_current = load_current_candidate_set_id(project_dir)
    candidate_set_id_at_save = payload.get("candidate_set_id_at_save")

    alignment_status = "not_checked"
    alignment_quality = None
    alignment_outlier_labels: list[str] = []
    try:
        alignment = build_report(project_dir, threshold_m, input_path, allow_stale=True)
        alignment_status = alignment.get("status", "not_checked")
        alignment_quality = alignment.get("quality")
        alignment_outlier_labels = alignment.get("best_fit", {}).get("outlier_labels", []) if alignment.get("best_fit") else []
    except Exception as exc:
        alignment_status = f"error: {exc}"
    outlier_set = set(alignment_outlier_labels)

    items = []
    for point in points:
        candidate, distance = nearest_candidate(point, candidates)
        match_type = migration_match_type(distance)
        matched_candidate_id = candidate.get("id") if candidate and match_type != "unmatched" else None
        point_alignment_status = "alignment_outlier" if point["label"] in outlier_set else "alignment_inlier"
        if alignment_status != "ok":
            point_alignment_status = "alignment_not_checked"
        items.append(
            {
                "old_label": point["label"],
                "old_cad_xy": point["cad"],
                "old_amap_gcj02": point["amap_gcj02"],
                "matched_candidate_id": matched_candidate_id,
                "match_type": match_type,
                "cad_distance": distance,
                "alignment_status": point_alignment_status,
                "recommendation": migration_recommendation(point, candidate, match_type, point_alignment_status),
            }
        )

    return {
        "schema_version": "1.0",
        "status": "ok",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "project_code": project_dir.name,
        "input": loaded_path.as_posix() if input_path else INPUT_REL.as_posix(),
        "candidate_set_id_current": candidate_set_id_current,
        "candidate_set_id_at_save": str(candidate_set_id_at_save) if candidate_set_id_at_save else None,
        "thresholds": {
            "same_geometry_match": SAME_GEOMETRY_THRESHOLD,
            "near_geometry_match": NEAR_GEOMETRY_THRESHOLD,
        },
        "alignment_status": alignment_status,
        "alignment_quality": alignment_quality,
        "alignment_outlier_labels": alignment_outlier_labels,
        "items": items,
        "recommendations": [
            "该文件只用于迁移诊断，不会自动改写 control_points.json。",
            "unmatched 或 alignment_outlier 的旧点应重新拾取；label 与 matched_candidate_id 不一致时不要按旧编号继续叙述。",
        ],
    }


def migration_report_path(project_dir: Path) -> Path:
    date = time.strftime("%Y-%m-%d")
    return project_dir / MIGRATION_REPORT_DIR_REL / f"migration_report_{date}.json"


def write_migration_report(project_dir: Path, report: dict[str, Any]) -> Path:
    out = migration_report_path(project_dir)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate CAD/AMap control point alignment")
    parser.add_argument("project", help="Project code or path")
    parser.add_argument("--json", action="store_true", help="Print JSON only")
    parser.add_argument("--write", action="store_true", help="Write 05_output/amap/cad_alignment_report.json")
    parser.add_argument("--allow-stale", action="store_true", help="Allow stale control points for audit-only alignment checks")
    parser.add_argument("--migration-report", action="store_true", help="Build a migration report for stale control points")
    parser.add_argument("--threshold-m", type=float, default=5.0, help="Residual threshold for inliers")
    parser.add_argument("--input", help="Optional control_points JSON path for temporary checks")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_dir = resolve_project(args.project)
    if not project_dir.exists():
        print(f"ERROR: project not found: {project_dir}", file=sys.stderr)
        return 3
    try:
        input_path = Path(args.input).resolve() if args.input else None
        if args.migration_report:
            report = build_migration_report(project_dir, args.threshold_m, input_path)
        else:
            report = build_report(project_dir, args.threshold_m, input_path, allow_stale=args.allow_stale)
    except Exception as exc:
        report = {
            "schema_version": "1.0",
            "status": "error",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "project_code": project_dir.name,
            "error": str(exc),
        }
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.write:
        if args.migration_report:
            report["written_to"] = str(write_migration_report(project_dir, report))
        elif report.get("status") == "stale_control_points":
            report["write_skipped"] = OUTPUT_REL.as_posix()
        else:
            report["written_to"] = str(write_report(project_dir, report))
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        title = "cad_align migration" if args.migration_report else "cad_align"
        print(f"== {title} :: {project_dir}")
        print(f"  status: {report['status']}")
        if "quality" in report:
            print(f"  quality: {report.get('quality')}")
        if report.get("candidate_set_id_current") or report.get("candidate_set_id_at_save"):
            print(f"  candidate_set_id_current: {report.get('candidate_set_id_current')}")
            print(f"  candidate_set_id_at_save: {report.get('candidate_set_id_at_save')}")
        if report.get("written_to"):
            print(f"  written_to: {report['written_to']}")
        if report.get("write_skipped"):
            print(f"  write_skipped: {report['write_skipped']}")
        if report.get("best_fit"):
            print(f"  inliers: {', '.join(report['best_fit']['inlier_labels'])}")
        if args.migration_report:
            print(f"  items: {len(report.get('items', []))}")
    return 0 if report["status"] in {"ok", "insufficient_points", "stale_control_points"} else 2


if __name__ == "__main__":
    sys.exit(main())

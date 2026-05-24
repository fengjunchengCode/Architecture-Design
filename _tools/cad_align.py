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
EARTH_RADIUS_M = 6378137.0


def resolve_project(code_or_path: str) -> Path:
    direct = Path(code_or_path).expanduser()
    if direct.exists():
        return direct.resolve()
    return (PROJECTS_DIR / code_or_path).resolve()


def load_points(project_dir: Path, input_path: Path | None = None) -> list[dict[str, Any]]:
    path = input_path or project_dir / INPUT_REL
    if not path.exists():
        raise FileNotFoundError(f"{path.as_posix()} 不存在")
    data = json.loads(path.read_text(encoding="utf-8"))
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


def build_report(project_dir: Path, threshold_m: float, input_path: Path | None = None) -> dict[str, Any]:
    points = load_points(project_dir, input_path)
    if len(points) < 3:
        return {
            "schema_version": "1.0",
            "status": "insufficient_points",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "project_code": project_dir.name,
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
        "input": input_path.as_posix() if input_path else INPUT_REL.as_posix(),
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate CAD/AMap control point alignment")
    parser.add_argument("project", help="Project code or path")
    parser.add_argument("--json", action="store_true", help="Print JSON only")
    parser.add_argument("--write", action="store_true", help="Write 05_output/amap/cad_alignment_report.json")
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
        report = build_report(project_dir, args.threshold_m, input_path)
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
        report["written_to"] = str(write_report(project_dir, report))
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"== cad_align :: {project_dir}")
        print(f"  status: {report['status']}")
        print(f"  quality: {report.get('quality')}")
        if report.get("best_fit"):
            print(f"  inliers: {', '.join(report['best_fit']['inlier_labels'])}")
    return 0 if report["status"] in {"ok", "insufficient_points"} else 2


if __name__ == "__main__":
    sys.exit(main())

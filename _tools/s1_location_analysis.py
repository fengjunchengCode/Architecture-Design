#!/usr/bin/env python3
"""Generate S1 location analysis snapshot: satellite PNG + structured JSON draft.

Reads projects/{code}/05_output/amap/s1_map_context.json and produces:
- satellite_2km.png (placeholder if screenshot not available)
- location_analysis_draft.json (structured analysis)
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CODE_REGEX = __import__("re").compile(r"^\d{2}-[A-Z]{2,3}-[A-Za-z0-9]{2,8}$")

CATEGORY_LABELS = {
    "transport": "交通设施",
    "education_culture": "教育文化",
    "scenic_park": "风景公园",
    "government_public": "政府公共",
    "commercial_life": "商业生活",
    "medical_sports": "医疗体育",
}

RINGS_M = [500, 1000, 2000]


def safe_project(code: str) -> str:
    code = code.strip()
    if not CODE_REGEX.match(code):
        raise ValueError("项目代号格式应为 26-SZ-NSXX")
    return code


def project_dir(code: str) -> Path:
    path = (REPO_ROOT / "projects" / safe_project(code)).resolve()
    if (REPO_ROOT / "projects").resolve() not in path.parents:
        raise ValueError("项目路径越界")
    return path


def load_context(proj: Path) -> dict:
    ctx_path = proj / "05_output" / "amap" / "s1_map_context.json"
    if not ctx_path.exists():
        raise FileNotFoundError("s1_map_context.json 不存在，请先生成 S1 高德上下文")
    data = json.loads(ctx_path.read_text(encoding="utf-8"))
    if data.get("status") != "ok":
        raise ValueError(f"上下文状态为 {data.get('status')}，无法生成分析")
    return data


def gcj02_to_wgs84(lng: float, lat: float) -> tuple[float, float]:
    """Convert GCJ-02 to WGS84 (inverse transform, iterative)."""
    PI = 3.14159265358979324
    A = 6378245.0
    EE = 0.00669342162296594323

    def _t_lat(x, y):
        r = -100 + 2*x + 3*y + 0.2*y*y + 0.1*x*y + 0.2*math.sqrt(abs(x))
        r += (20*math.sin(6*x*PI) + 20*math.sin(2*x*PI)) * 2/3
        r += (20*math.sin(y*PI) + 40*math.sin(y/3*PI)) * 2/3
        r += (160*math.sin(y/12*PI) + 320*math.sin(y*PI/30)) * 2/3
        return r

    def _t_lng(x, y):
        r = 300 + x + 2*y + 0.1*x*x + 0.1*x*y + 0.1*math.sqrt(abs(x))
        r += (20*math.sin(6*x*PI) + 20*math.sin(2*x*PI)) * 2/3
        r += (20*math.sin(x*PI) + 40*math.sin(x/3*PI)) * 2/3
        r += (150*math.sin(x/12*PI) + 300*math.sin(x/30*PI)) * 2/3
        return r

    dx = _t_lng(lng - 105, lat - 35)
    dy = _t_lat(lng - 105, lat - 35)
    rl = lat / 180 * PI
    m = math.sin(rl)
    m = 1 - EE * m * m
    sm = math.sqrt(m)
    dy = (dy * 180) / ((A * (1 - EE)) / (m * sm) * PI)
    dx = (dx * 180) / (A / sm * math.cos(rl) * PI)
    return (lng - dx, lat - dy)


def compute_bounds(center_gcj02: str, radius_m: int = 2000) -> dict:
    """Compute approximate bounding box for a given radius around center."""
    try:
        parts = center_gcj02.split(",")
        lng, lat = float(parts[0]), float(parts[1])
    except (ValueError, IndexError):
        return {"gcj02": None, "wgs84": None}

    # Approximate degrees per meter at this latitude
    lat_rad = math.radians(lat)
    m_per_deg_lat = 111132.92 - 559.82 * math.cos(2 * lat_rad) + 1.175 * math.cos(4 * lat_rad)
    m_per_deg_lng = 111412.84 * math.cos(lat_rad) - 93.5 * math.cos(3 * lat_rad)

    dlat = radius_m / m_per_deg_lat
    dlng = radius_m / m_per_deg_lng

    gcj_bounds = {
        "south": lat - dlat,
        "north": lat + dlat,
        "west": lng - dlng,
        "east": lng + dlng,
    }

    wgs_sw = gcj02_to_wgs84(gcj_bounds["west"], gcj_bounds["south"])
    wgs_ne = gcj02_to_wgs84(gcj_bounds["east"], gcj_bounds["north"])

    return {
        "gcj02": gcj_bounds,
        "wgs84": {
            "south": wgs_sw[1],
            "north": wgs_ne[1],
            "west": wgs_sw[0],
            "east": wgs_ne[0],
        },
    }


def compute_zoom_for_radius(radius_m: int) -> int:
    """Approximate AMap zoom level for a given radius in meters."""
    # zoom 14 ~ 2km radius, zoom 15 ~ 1km, zoom 16 ~ 500m
    if radius_m >= 2000:
        return 14
    elif radius_m >= 1000:
        return 15
    else:
        return 16


def extract_poi_summary(ctx: dict) -> dict:
    """Extract POI summary for each ring distance."""
    mc = ctx.get("map_context", {})
    result = {}
    for radius in RINGS_M:
        key = f"poi_{radius}m"
        poi_data = mc.get(key, {})
        ring_summary = {}
        for cat_key, cat_data in poi_data.items():
            if not isinstance(cat_data, dict) or int(cat_data.get("count", 0)) == 0:
                continue
            items = cat_data.get("items", [])
            ring_summary[cat_key] = {
                "label": CATEGORY_LABELS.get(cat_key, cat_key),
                "count": int(cat_data.get("count", 0)),
                "top_items": [
                    {"name": p.get("name", ""), "distance_m": float(p.get("distance_m", 0))}
                    for p in sorted(items, key=lambda x: float(x.get("distance_m", 9999)))[:5]
                ],
            }
        result[str(radius)] = ring_summary
    return result


def build_draft(ctx: dict, code: str, screenshot_path: str | None) -> dict:
    """Build the structured JSON draft."""
    loc = ctx.get("location", {})
    regeo = ctx.get("map_context", {}).get("regeo", {})
    addr_comp = regeo.get("address_component", {})

    center_gcj02 = loc.get("amap_gcj02", "")
    center_wgs84 = None
    if center_gcj02:
        try:
            parts = center_gcj02.split(",")
            wgs = gcj02_to_wgs84(float(parts[0]), float(parts[1]))
            center_wgs84 = f"{wgs[0]:.6f},{wgs[1]:.6f}"
        except (ValueError, IndexError):
            pass

    bounds = compute_bounds(center_gcj02, 2000)

    return {
        "schema_version": "1.0",
        "project_code": code,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "center_gcj02": center_gcj02,
        "center_wgs84": center_wgs84,
        "rings_m": RINGS_M,
        "map_mode": "satellite",
        "bounds_gcj02": bounds.get("gcj02"),
        "bounds_wgs84": bounds.get("wgs84"),
        "screenshot_path": screenshot_path,
        "data_sources": {
            "amap_context": "s1_map_context.json",
            "satellite": "AMap static map API",
        },
        "location": {
            "formatted_address": regeo.get("formatted_address", ""),
            "province": addr_comp.get("province", ""),
            "city": addr_comp.get("city", ""),
            "district": addr_comp.get("district", ""),
            "township": addr_comp.get("township", ""),
            "adcode": addr_comp.get("adcode", ""),
        },
        "poi_summary": extract_poi_summary(ctx),
        "limitations": [
            "卫星截图精度取决于 AMap 静态地图 API，zoom=14 对应约 2km 范围",
            "POI 数据仅覆盖高德地图已收录的兴趣点，偏远区域可能缺失",
            "坐标系为 GCJ-02（高德），与 WGS84 存在约 500m 偏移",
            "精确落边需在 S2 阶段通过控制点配准",
            "配图上传功能已就绪，可附加现场照片用于 PPT 排版",
            "区界数据来源为 AMap DistrictSearch，边界精度有限",
        ],
    }


def generate_screenshot_placeholder(proj: Path, center_gcj02: str, output_dir: Path) -> str | None:
    """Generate a placeholder PNG for the satellite screenshot."""
    try:
        from PIL import Image, ImageDraw, ImageFont

        img = Image.new("RGB", (750, 750), (245, 242, 232))
        draw = ImageDraw.Draw(img)

        # Draw grid
        for i in range(0, 750, 50):
            draw.line([(i, 0), (i, 750)], fill=(220, 218, 210), width=1)
            draw.line([(0, i), (750, i)], fill=(220, 218, 210), width=1)

        # Draw center marker
        cx, cy = 375, 375
        draw.ellipse([cx-8, cy-8, cx+8, cy+8], fill=(220, 50, 50), outline=(180, 30, 30))
        draw.line([(cx-15, cy), (cx+15, cy)], fill=(220, 50, 50), width=2)
        draw.line([(cx, cy-15), (cx, cy+15)], fill=(220, 50, 50), width=2)

        # Draw radius circles (approximate)
        for r_px, label in [(94, "500m"), (188, "1km"), (375, "2km")]:
            draw.ellipse([cx-r_px, cy-r_px, cx+r_px, cy+r_px], outline=(100, 100, 100), width=1)
            draw.text((cx+r_px-30, cy-12), label, fill=(100, 100, 100))

        # Draw text
        draw.text((20, 20), "S1 Satellite Placeholder", fill=(60, 60, 60))
        draw.text((20, 40), f"Center: {center_gcj02}", fill=(100, 100, 100))
        draw.text((20, 60), "Replace with actual AMap satellite screenshot", fill=(150, 150, 150))

        output_path = output_dir / "satellite_2km.png"
        img.save(str(output_path), "PNG")
        return str(output_path.relative_to(proj)).replace("\\", "/")
    except ImportError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate S1 location analysis snapshot")
    parser.add_argument("project")
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    try:
        code = safe_project(args.project)
        proj = project_dir(code)
        ctx = load_context(proj)

        output_dir = proj / "05_output" / "location_analysis"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate screenshot placeholder
        center_gcj02 = ctx.get("location", {}).get("amap_gcj02", "")
        screenshot_rel = generate_screenshot_placeholder(proj, center_gcj02, output_dir)

        # Generate draft
        draft = build_draft(ctx, code, screenshot_rel)
        json_path = output_dir / "location_analysis_draft.json"

        result: dict = {
            "ok": True,
            "auto_draft": True,
            "project_code": code,
            "output_dir": str(output_dir.relative_to(proj)).replace("\\", "/"),
            "screenshot_path": screenshot_rel,
            "json_path": str(json_path.relative_to(proj)).replace("\\", "/"),
            "summary": f"区位：{ctx.get('map_context', {}).get('regeo', {}).get('address_component', {}).get('district', '')}",
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }

        if args.write:
            json_path.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")
            result["json_written_to"] = str(json_path)

        if args.json_output:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(draft, ensure_ascii=False, indent=2))

        return 0

    except Exception as exc:
        error_result = {
            "ok": False,
            "auto_draft": True,
            "project_code": args.project if hasattr(args, "project") else "",
            "error": str(exc),
        }
        if args.json_output:
            print(json.dumps(error_result, ensure_ascii=False, indent=2))
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

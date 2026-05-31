#!/usr/bin/env python3
"""Generate S1 location analysis draft from existing map context data.

Reads projects/{code}/05_output/amap/s1_map_context.json and produces
a structured Chinese markdown analysis document.

Does NOT call any AMap APIs — purely local data transformation.
"""
from __future__ import annotations

import argparse
import json
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

KEYWORD_LABELS = {
    "河": "水系",
    "桥": "桥梁",
    "公园": "公园绿地",
    "公交站": "公交站点",
}

POI_DISPLAY_LIMIT = 8


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


def _fmt_distance(val) -> str:
    try:
        d = float(val)
        if d < 1000:
            return f"{d:.0f}m"
        return f"{d / 1000:.1f}km"
    except (TypeError, ValueError):
        return str(val)


def _poi_summary(items: list, limit: int = POI_DISPLAY_LIMIT) -> tuple[list[str], int]:
    """Return (display_lines, total_count)."""
    total = len(items)
    shown = sorted(items, key=lambda x: float(x.get("distance_m", 9999)))[:limit]
    lines = []
    for p in shown:
        name = p.get("name", "")
        dist = _fmt_distance(p.get("distance_m"))
        lines.append(f"{name}（{dist}）")
    return lines, total


def generate_markdown(ctx: dict) -> str:
    lines: list[str] = []
    ts = time.strftime("%Y-%m-%d %H:%M")

    lines.append("# S1 区位分析草稿")
    lines.append("")
    lines.append(f"> 自动生成于 {ts}，基于高德地图数据。本草稿为设计参考，需结合现场调研验证。")
    lines.append("")

    # 一、区位身份
    loc = ctx.get("location", {})
    regeo = ctx.get("map_context", {}).get("regeo", {})
    addr_comp = regeo.get("address_component", {})

    lines.append("## 一、区位身份")
    lines.append("")
    fa = regeo.get("formatted_address") or "无"
    lines.append(f"- **详细地址：** {fa}")
    province = addr_comp.get("province", "")
    city = addr_comp.get("city", "")
    district = addr_comp.get("district", "")
    township = addr_comp.get("township", "")
    admin_parts = " ".join(filter(None, [province, city, district, township]))
    lines.append(f"- **行政区划：** {admin_parts or '无'}")
    adcode = addr_comp.get("adcode", "")
    if adcode:
        lines.append(f"- **行政代码：** {adcode}")
    lines.append(f"- **坐标（GCJ-02）：** {loc.get('amap_gcj02', '无')}")
    lines.append(f"- **定位来源：** {loc.get('source', '无')}，置信度 {loc.get('confidence', '无')}")
    lines.append("")

    # 二、周边设施
    mc = ctx.get("map_context", {})
    poi_500 = mc.get("poi_500m", {})
    poi_1000 = mc.get("poi_1000m", {})

    has_any_poi = False
    for cat_data in list(poi_500.values()) + list(poi_1000.values()):
        if isinstance(cat_data, dict) and int(cat_data.get("count", 0)) > 0:
            has_any_poi = True
            break

    lines.append("## 二、周边设施")
    lines.append("")

    if has_any_poi:
        # 500m
        has_500 = any(int(v.get("count", 0)) > 0 for v in poi_500.values() if isinstance(v, dict))
        if has_500:
            lines.append("### 2.1 500米范围内")
            lines.append("")
            for cat_key, cat_data in sorted(poi_500.items()):
                if not isinstance(cat_data, dict) or int(cat_data.get("count", 0)) == 0:
                    continue
                label = CATEGORY_LABELS.get(cat_key, cat_key)
                items = cat_data.get("items", [])
                shown, total = _poi_summary(items)
                suffix = f"（共 {total} 处）" if total > len(shown) else ""
                lines.append(f"- **{label}：** {', '.join(shown)}{suffix}")
            lines.append("")

        # 1000m
        has_1000 = any(int(v.get("count", 0)) > 0 for v in poi_1000.values() if isinstance(v, dict))
        if has_1000:
            lines.append("### 2.2 1000米范围内")
            lines.append("")
            for cat_key, cat_data in sorted(poi_1000.items()):
                if not isinstance(cat_data, dict) or int(cat_data.get("count", 0)) == 0:
                    continue
                label = CATEGORY_LABELS.get(cat_key, cat_key)
                items = cat_data.get("items", [])
                shown, total = _poi_summary(items)
                suffix = f"（共 {total} 处）" if total > len(shown) else ""
                lines.append(f"- **{label}：** {', '.join(shown)}{suffix}")
            lines.append("")
    else:
        lines.append("高德地图在 1km 范围内未返回分类 POI 数据。")
        lines.append("")

    # 关键词检索
    kw_ctx = mc.get("keyword_context", {})
    has_kw = any(int(v.get("count", 0)) > 0 for v in kw_ctx.values() if isinstance(v, dict))
    if has_kw:
        lines.append("### 2.3 关键词检索")
        lines.append("")
        for kw, kw_data in sorted(kw_ctx.items()):
            if not isinstance(kw_data, dict) or int(kw_data.get("count", 0)) == 0:
                continue
            label = KEYWORD_LABELS.get(kw, kw)
            items = kw_data.get("items", [])
            shown, total = _poi_summary(items)
            suffix = f"（共 {total} 处）" if total > len(shown) else ""
            lines.append(f"- **{label}：** {', '.join(shown)}{suffix}")
        lines.append("")

    # 三、道路交通
    roads = regeo.get("roads", [])
    intersections = regeo.get("road_intersections", [])

    lines.append("## 三、道路交通")
    lines.append("")

    if roads:
        lines.append("### 3.1 周边道路")
        lines.append("")
        for r in roads:
            name = r.get("name", "")
            direction = r.get("direction", "")
            dist = _fmt_distance(r.get("distance_m"))
            parts = [name]
            if direction:
                parts.append(f"{direction}侧")
            parts.append(dist)
            lines.append(f"- {' '.join(parts)}")
        lines.append("")

    if intersections:
        lines.append("### 3.2 道路交叉口")
        lines.append("")
        for ix in intersections:
            n1 = ix.get("first_name", "")
            n2 = ix.get("second_name", "")
            direction = ix.get("direction", "")
            dist = _fmt_distance(ix.get("distance_m"))
            parts = [f"{n1} / {n2}"]
            if direction:
                parts.append(f"{direction}侧")
            parts.append(dist)
            lines.append(f"- {' '.join(parts)}")
        lines.append("")

    if not roads and not intersections:
        lines.append("高德地图在该位置未返回道路数据，可能为偏远或新开发区域。")
        lines.append("")

    # 四、自然与景观要素
    lines.append("## 四、自然与景观要素")
    lines.append("")

    seed = ctx.get("s1_external_context_seed", {})
    water = seed.get("amap_context", {}).get("water", [])
    kw_water = []
    for kw in ("河", "桥"):
        kw_data = kw_ctx.get(kw, {})
        if isinstance(kw_data, dict):
            for item in kw_data.get("items", []):
                kw_water.append(item.get("name", ""))

    all_water = list(dict.fromkeys(water + kw_water))  # dedupe preserving order
    if all_water:
        lines.append(f"- **水系/桥梁：** {', '.join(all_water[:10])}")
    else:
        lines.append("- **水系/桥梁：** 未检索到")

    parks = []
    park_data = kw_ctx.get("公园", {})
    if isinstance(park_data, dict):
        for item in park_data.get("items", []):
            parks.append(item.get("name", ""))
    if parks:
        lines.append(f"- **公园绿地：** {', '.join(parks[:10])}")
    else:
        lines.append("- **公园绿地：** 未检索到")

    bus = []
    bus_data = kw_ctx.get("公交站", {})
    if isinstance(bus_data, dict):
        for item in bus_data.get("items", []):
            bus.append(item.get("name", ""))
    if bus:
        lines.append(f"- **公交站点：** {', '.join(bus[:10])}")
    else:
        lines.append("- **公交站点：** 未检索到")
    lines.append("")

    # 五、设计启示与局限
    lines.append("## 五、设计启示与局限")
    lines.append("")

    lines.append("### 5.1 数据可支撑的判断")
    lines.append("")

    poi_total_500 = sum(int(v.get("count", 0)) for v in poi_500.values() if isinstance(v, dict))
    poi_total_1000 = sum(int(v.get("count", 0)) for v in poi_1000.values() if isinstance(v, dict))

    if admin_parts:
        lines.append(f"- 该地块位于{admin_parts}")
    if poi_total_500 > 0 or poi_total_1000 > 0:
        lines.append(f"- 周边 500m 内 {poi_total_500} 个设施，1km 内 {poi_total_1000} 个设施")

    commercial_500 = poi_500.get("commercial_life", {})
    if isinstance(commercial_500, dict) and int(commercial_500.get("count", 0)) > 0:
        lines.append("- 周边有商业配套，生活便利性可期")
    transport_1000 = poi_1000.get("transport", {})
    if isinstance(transport_1000, dict) and int(transport_1000.get("count", 0)) > 0:
        names = [i.get("name", "") for i in transport_1000.get("items", [])[:3]]
        lines.append(f"- 交通设施包括：{', '.join(names)}")
    if roads:
        lines.append(f"- 可达性：周边有 {len(roads)} 条道路")
    if all_water:
        lines.append(f"- 景观资源：{all_water[0]}等水系/桥梁要素")

    lines.append("")
    lines.append("### 5.2 需进一步调查的内容")
    lines.append("")
    lines.append("- 出入口位置需结合 CAD 红线和现场踏勘确定")
    lines.append("- 道路等级与通行条件需现场核实")
    if not roads and not intersections:
        lines.append("- 道路信息缺失，需现场补充")
    lines.append("- 周边用地性质需查阅规划文件确认")
    lines.append("- 噪音、日照等环境因素需现场测量")
    lines.append("")

    lines.append("### 5.3 坐标配准说明")
    lines.append("")
    lines.append("- 当前坐标系为 GCJ-02（高德），与 CAD 工程坐标系不能直接叠加")
    lines.append("- 精确落边需在 S2 阶段通过 2-3 个控制点完成配准")
    lines.append("")
    lines.append("---")
    lines.append("*本文件由 s1_location_analysis.py 自动生成，可直接编辑修改。*")

    return "\n".join(lines)


def generate_structured_draft(ctx: dict) -> dict:
    """Generate a structured JSON draft for programmatic consumption."""
    loc = ctx.get("location", {})
    regeo = ctx.get("map_context", {}).get("regeo", {})
    addr_comp = regeo.get("address_component", {})
    mc = ctx.get("map_context", {})
    poi_500 = mc.get("poi_500m", {})
    poi_1000 = mc.get("poi_1000m", {})
    kw_ctx = mc.get("keyword_context", {})
    seed = ctx.get("s1_external_context_seed", {})

    # POI summary by category
    def extract_pois(poi_data: dict) -> dict:
        result = {}
        for cat_key, cat_data in poi_data.items():
            if not isinstance(cat_data, dict) or int(cat_data.get("count", 0)) == 0:
                continue
            items = cat_data.get("items", [])
            result[cat_key] = {
                "label": CATEGORY_LABELS.get(cat_key, cat_key),
                "count": int(cat_data.get("count", 0)),
                "items": [
                    {"name": p.get("name", ""), "distance_m": float(p.get("distance_m", 0))}
                    for p in sorted(items, key=lambda x: float(x.get("distance_m", 9999)))[:POI_DISPLAY_LIMIT]
                ],
            }
        return result

    # Water/park features from keywords
    def extract_keyword_features(kw_data: dict, keywords: list[str]) -> list[dict]:
        features = []
        for kw in keywords:
            data = kw_data.get(kw, {})
            if not isinstance(data, dict) or int(data.get("count", 0)) == 0:
                continue
            for item in data.get("items", []):
                features.append({
                    "type": KEYWORD_LABELS.get(kw, kw),
                    "name": item.get("name", ""),
                    "distance_m": float(item.get("distance_m", 0)),
                })
        return sorted(features, key=lambda x: x["distance_m"])

    # Static map URL for 2km satellite view
    gcj02 = loc.get("amap_gcj02", "")
    static_map_url = None
    if gcj02:
        static_map_url = (
            f"https://restapi.amap.com/v3/staticmap?"
            f"location={gcj02}&zoom=14&size=750*750&scale=2"
            f"&markers=mid,0xFF0000,{gcj02}"
            f"&key=<AMAP_WEBSERVICE_KEY>"
        )

    return {
        "schema_version": "1.0",
        "type": "s1_location_draft",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "project_code": ctx.get("project_code", ""),
        "location": {
            "gcj02": gcj02,
            "formatted_address": regeo.get("formatted_address", ""),
            "province": addr_comp.get("province", ""),
            "city": addr_comp.get("city", ""),
            "district": addr_comp.get("district", ""),
            "township": addr_comp.get("township", ""),
            "adcode": addr_comp.get("adcode", ""),
            "confidence": loc.get("confidence", ""),
        },
        "static_map": {
            "url_template": static_map_url,
            "zoom": 14,
            "radius_m": 2000,
            "note": "Replace <AMAP_WEBSERVICE_KEY> with actual key from .env",
        },
        "facilities": {
            "500m": extract_pois(poi_500),
            "1000m": extract_pois(poi_1000),
        },
        "roads": {
            "list": regeo.get("roads", []),
            "intersections": regeo.get("road_intersections", []),
        },
        "natural_features": extract_keyword_features(kw_ctx, ["河", "桥", "公园", "公交站"]),
        "design_notes": {
            "data_supports": [],
            "needs_investigation": [
                "出入口位置需结合 CAD 红线和现场踏勘确定",
                "道路等级与通行条件需现场核实",
                "周边用地性质需查阅规划文件确认",
                "噪音、日照等环境因素需现场测量",
            ],
            "coordinate_note": "当前坐标系为 GCJ-02（高德），精确落边需在 S2 阶段通过控制点配准",
        },
    }


def build_summary(ctx: dict) -> str:
    mc = ctx.get("map_context", {})
    regeo = mc.get("regeo", {})
    addr_comp = regeo.get("address_component", {})
    district = addr_comp.get("district", "")
    township = addr_comp.get("township", "")
    poi_500 = mc.get("poi_500m", {})
    poi_1000 = mc.get("poi_1000m", {})
    c500 = sum(int(v.get("count", 0)) for v in poi_500.values() if isinstance(v, dict))
    c1000 = sum(int(v.get("count", 0)) for v in poi_1000.values() if isinstance(v, dict))
    roads = regeo.get("roads", [])
    loc = f"{township or district}"
    parts = [f"区位：{loc}"] if loc else []
    parts.append(f"500m 内 {c500} 个设施，1km 内 {c1000} 个设施")
    if roads:
        parts.append(f"{len(roads)} 条道路")
    return "，".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate S1 location analysis draft")
    parser.add_argument("project")
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    try:
        code = safe_project(args.project)
        proj = project_dir(code)
        ctx = load_context(proj)
        markdown = generate_markdown(ctx)
        structured = generate_structured_draft(ctx)
        summary = build_summary(ctx)

        out_path = proj / "05_output" / "s1_location_analysis.md"
        json_path = proj / "05_output" / "s1_location_draft.json"
        result: dict = {
            "ok": True,
            "auto_draft": True,
            "project_code": code,
            "path": str(out_path.relative_to(proj)).replace("\\", "/"),
            "json_path": str(json_path.relative_to(proj)).replace("\\", "/"),
            "summary": summary,
            "markdown_preview": markdown[:2000],
            "structured_preview": json.dumps(structured, ensure_ascii=False, indent=2)[:2000],
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }

        if args.write:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(markdown, encoding="utf-8")
            json_path.write_text(json.dumps(structured, ensure_ascii=False, indent=2), encoding="utf-8")
            result["written_to"] = str(out_path)
            result["json_written_to"] = str(json_path)

        if args.json_output:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(markdown)

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

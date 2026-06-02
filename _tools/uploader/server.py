#!/usr/bin/env python3
"""Local upload UI for architecture project intake."""
from __future__ import annotations

import argparse
import io
import json
import math
import mimetypes
import os
import re
import subprocess
import sys
import tempfile
import time
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote_to_bytes, urlparse
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parents[2]
STATIC_DIR = Path(__file__).resolve().parent / "static"
PROJECTS_DIR = REPO_ROOT / "projects"
ENV_FILE = REPO_ROOT / ".env"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from _tools.drawing_workbench.registry import (
    DRAWING_REGISTRY,
    DRAWING_TYPES,
    OBJECT_TYPE_REGISTRY,
    default_base_path_for,
    default_object_style,
)
from _tools.drawing_workbench.deck_layout import (
    export_deck_pptx,
    layout_rel_path,
    load_deck_layout,
    reflow_deck,
    save_deck_layout,
    set_drawing_frame,
    set_template_side,
)
from _tools.drawing_workbench.schema import (
    drawing_output_paths,
    empty_drawing,
    normalize_drawing,
)
from _tools.drawing_workbench.style_schema import validate_style_spec
from _tools.drawing_workbench.svg_to_png import export_svg
from _tools.drawing_workbench.task_pack import build_task_pack

CODE_REGEX = re.compile(r"^\d{2}-[A-Z]{2,3}-[A-Za-z0-9]{2,8}$")
VALID_TYPES = {
    "school",
    "residential",
    "commercial",
    "park",
    "street_scape",
    "renovation",
    "hospital",
    "cultural",
    "industrial",
    "cultural_tourism",
    "unknown",
}

BUCKETS = {
    "briefing": "01_briefing",
    "location_map": "02_site/区位图",
    "topography": "02_site/地形图",
    "site_photo": "02_site/现场照片",
    "reference": "03_references",
    "chat": "04_chat",
}
CAD_SEMANTICS_REL = Path("05_output/cad/control_point_candidate_semantics.json")
CAD_CANDIDATES_REL = Path("05_output/cad/control_point_candidates.json")
CONTROL_POINTS_REL = Path("05_output/amap/control_points.json")
SITE_CONTEXT_REL = Path("05_output/site_context/site_context.json")
SITE_BASEMAP_REL = Path("05_output/site_context/s2_tianditu_satellite.png")
STYLE_PRESETS_FILE = Path(
    os.environ.get(
        "DRAWING_STYLE_PRESETS_PATH",
        str(REPO_ROOT / "_tools" / "drawing_workbench" / "style_presets.json"),
    )
)

CONTROL_FEATURE_TYPES = {
    "redline_corner",
    "road_intersection",
    "road_centerline",
    "road_edge",
    "bridge_endpoint",
    "bridge_center",
    "water_edge",
    "building_corner",
    "visible_landmark",
    "other",
}
CONTROL_PURPOSES = {
    "registration",
    "road_binding",
    "entrance_check",
    "water_binding",
    "reference_only",
}
CONTROL_CONFIDENCE = {"low", "medium", "high"}
ROAD_NAME_RE = re.compile(
    r"(?:G\d{2,3}|\d{2,3}国道|\d{2,3}省道|\d{2,3}县道|\d{2,3}乡道|[\u4e00-\u9fa5A-Za-z0-9]{1,16}(?:大道|公路|道路|路|街|桥))"
)
PRIMARY_ROAD_RE = re.compile(r"(?:^G\d{2,3}$|\d{2,3}国道|国道|高速|快速路|大道)")
SECONDARY_ROAD_RE = re.compile(r"(?:^S\d{2,3}$|\d{2,3}省道|\d{2,3}县道|\d{2,3}乡道|省道|县道|乡道|公路)")

AMAP_JSAPI_REFERER_HINT = (
    "AMAP_JSAPI_KEY 需在高德控制台勾选 'Web 端' 并把 referer 白名单加入 "
    "http://127.0.0.1:8765 / http://localhost:8765"
)
AMAP_WEBSERVICE_ENV_NAMES = ("AMAP_WEBSERVICE_KEY", "AMAP_WEB_SERVICE_KEY", "AMAP_KEY")


def safe_project(code: str) -> str:
    code = code.strip()
    if not CODE_REGEX.match(code):
        raise ValueError("项目代号格式应为 26-SZ-NSXX")
    return code


def project_dir(code: str) -> Path:
    code = safe_project(code)
    path = (PROJECTS_DIR / code).resolve()
    if PROJECTS_DIR.resolve() not in path.parents:
        raise ValueError("项目路径越界")
    return path


def sanitize_filename(name: str) -> str:
    base = Path(name.replace("\\", "/")).name.strip()
    base = re.sub(r"[\x00-\x1f<>:\"|?*]", "_", base)
    base = base.strip(" .")
    return base or "upload.bin"


def unique_path(directory: Path, filename: str) -> Path:
    target = directory / filename
    if not target.exists():
        return target
    stem = target.stem
    suffix = target.suffix
    index = 2
    while True:
        candidate = directory / f"{stem}_{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def unique_dash_path(directory: Path, filename: str) -> Path:
    target = directory / filename
    if not target.exists():
        return target
    stem = target.stem
    suffix = target.suffix
    index = 1
    while True:
        candidate = directory / f"{stem}-{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def parse_header_params(value: str) -> dict[str, str]:
    params: dict[str, str] = {}
    parts = value.split(";")
    params[""] = parts[0].strip().lower() if parts else ""
    for part in parts[1:]:
        if "=" not in part:
            continue
        key, raw_value = part.split("=", 1)
        raw_value = raw_value.strip()
        if len(raw_value) >= 2 and raw_value[0] == raw_value[-1] == '"':
            raw_value = raw_value[1:-1].replace(r"\"", '"').replace(r"\\", "\\")
        params[key.strip().lower()] = raw_value
    return params


def decode_header_bytes(value: bytes) -> str:
    for encoding in ("utf-8", "gb18030", "latin-1"):
        try:
            return value.decode(encoding)
        except UnicodeDecodeError:
            continue
    return value.decode("utf-8", errors="replace")


def decode_filename(disposition_params: dict[str, str]) -> str | None:
    encoded = disposition_params.get("filename*")
    if encoded:
        try:
            charset, _, quoted = encoded.split("'", 2)
            return unquote_to_bytes(quoted).decode(charset or "utf-8")
        except (LookupError, UnicodeDecodeError, ValueError):
            pass
    return disposition_params.get("filename")


def iter_multipart_files(content_type: str, body: bytes) -> list[tuple[str, bytes]]:
    boundary = parse_header_params(content_type).get("boundary")
    if not boundary:
        return []
    delimiter = b"--" + boundary.encode("ascii", errors="ignore")
    files: list[tuple[str, bytes]] = []
    for part in body.split(delimiter):
        part = part.strip(b"\r\n")
        if not part or part == b"--":
            continue
        if part.endswith(b"--"):
            part = part[:-2].rstrip(b"\r\n")
        headers_raw, sep, payload = part.partition(b"\r\n\r\n")
        if not sep:
            continue
        headers: dict[str, bytes] = {}
        for line in headers_raw.split(b"\r\n"):
            name, colon, value = line.partition(b":")
            if colon:
                headers[name.decode("ascii", errors="ignore").strip().lower()] = value.strip()
        disposition = headers.get("content-disposition")
        if not disposition:
            continue
        filename = decode_filename(parse_header_params(decode_header_bytes(disposition)))
        if filename:
            files.append((filename, payload))
    return files


def run_tool(args: list[str]) -> tuple[int, str, str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    completed = subprocess.run(
        [sys.executable, *args],
        cwd=REPO_ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
        env=env,
    )
    return completed.returncode, completed.stdout, completed.stderr


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
        if not key or key in os.environ:
            continue
        os.environ[key] = value.strip().strip('"').strip("'")
        loaded.append(key)
    return loaded


def configured_env_name(names: tuple[str, ...]) -> str | None:
    for name in names:
        value = os.environ.get(name, "").strip()
        lowered = value.lower()
        if value and lowered not in {"xxx", "your_key", "your_amap_webservice_key", "none"} and not lowered.startswith("your_"):
            return name
    return None


def _font(size: int, bold: bool = False):
    from PIL import ImageFont

    candidates = [
        Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / ("msyhbd.ttc" if bold else "msyh.ttc"),
        Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / ("arialbd.ttf" if bold else "arial.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def _wgs84_to_tile(lng: float, lat: float, zoom: int) -> tuple[float, float]:
    lat = max(min(lat, 85.05112878), -85.05112878)
    n = 2**zoom
    x = (lng + 180.0) / 360.0 * n
    lat_rad = math.radians(lat)
    y = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n
    return x, y


def _fetch_tdt_tile(layer: str, zoom: int, x: int, y: int, tk: str):
    from PIL import Image

    server = abs(x + y + zoom) % 8
    url = (
        f"https://t{server}.tianditu.gov.cn/{layer}_w/wmts?"
        f"SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER={layer}"
        f"&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles"
        f"&TILEMATRIX={zoom}&TILEROW={y}&TILECOL={x}&tk={tk}"
    )
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 Architecture-Design/1.0",
            "Referer": "http://127.0.0.1/",
        },
    )
    with urlopen(request, timeout=10) as response:
        return Image.open(io.BytesIO(response.read())).convert("RGB")


def _draw_arrow(draw, cx: float, cy: float, radius: float, label: str, angle: float, ui: float, font) -> None:
    start = max(34 * ui, min(radius * 0.28, 74 * ui))
    end = max(start + 18 * ui, radius - 8 * ui)
    sx, sy = cx + math.cos(angle) * start, cy + math.sin(angle) * start
    ex, ey = cx + math.cos(angle) * end, cy + math.sin(angle) * end
    width = max(2, int(2 * ui))
    shadow = (0, 0, 0, 170)
    white = (255, 255, 255, 245)
    draw.line([(sx + 1, sy + 1), (ex + 1, ey + 1)], fill=shadow, width=width + 2)
    draw.line([(sx, sy), (ex, ey)], fill=white, width=width)
    head = 8 * ui
    left = (ex - math.cos(angle - 0.42) * head, ey - math.sin(angle - 0.42) * head)
    right = (ex - math.cos(angle + 0.42) * head, ey - math.sin(angle + 0.42) * head)
    draw.polygon([(ex, ey), left, right], fill=white)
    if math.cos(angle) >= 0:
        draw.text((ex - 10 * ui, ey), label, fill=white, font=font, anchor="rm", stroke_width=max(1, int(ui)), stroke_fill=(0, 0, 0, 180))
    else:
        draw.text((ex + 10 * ui, ey), label, fill=white, font=font, anchor="lm", stroke_width=max(1, int(ui)), stroke_fill=(0, 0, 0, 180))


def _draw_dashed_circle(draw, cx: float, cy: float, radius: float, ui: float) -> None:
    width = max(2, int(2 * ui))
    for start in range(0, 360, 24):
        draw.arc(
            [cx - radius, cy - radius, cx + radius, cy + radius],
            start=start,
            end=start + 12,
            fill=(255, 255, 255, 245),
            width=width,
        )


def _draw_location_overlay(image, center_wgs: tuple[float, float], zoom: int, radius_m: int) -> None:
    from PIL import ImageDraw

    draw = ImageDraw.Draw(image, "RGBA")
    width, height = image.size
    ui = max(0.85, min(1.35, min(width, height) / 1024))
    cx, cy = width / 2, height / 2
    meters_per_pixel = 156543.03392 * math.cos(math.radians(center_wgs[1])) / (2**zoom)
    rings = [500, 1000, 2000] if radius_m >= 2000 else [500, 1000]
    ring_px = {meters: meters / meters_per_pixel for meters in rings}
    arrow_font = _font(int(22 * ui), True)
    site_font = _font(int(34 * ui), True)

    for radius in ring_px.values():
        box = [cx - radius, cy - radius, cx + radius, cy + radius]
        draw.ellipse([value + 1 for value in box], outline=(0, 0, 0, 165), width=max(3, int(4 * ui)))
        draw.ellipse(box, outline=(255, 255, 255, 245), width=max(2, int(2.4 * ui)))

    if 500 in ring_px:
        _draw_arrow(draw, cx, cy, ring_px[500], "500m", -2.25, ui, arrow_font)
    if 1000 in ring_px:
        _draw_arrow(draw, cx, cy, ring_px[1000], "1km", -0.48, ui, arrow_font)
    if 2000 in ring_px:
        _draw_arrow(draw, cx, cy, ring_px[2000], "2km", 0.10, ui, arrow_font)

    _draw_dashed_circle(draw, cx, cy, 25 * ui, ui)
    draw.ellipse([cx - 8 * ui, cy - 8 * ui, cx + 8 * ui, cy + 8 * ui], fill=(227, 52, 47, 255), outline=(255, 255, 255, 255), width=max(2, int(2 * ui)))
    draw.text((cx + 20 * ui, cy - 32 * ui), "SITE", fill=(255, 255, 255, 250), font=site_font, anchor="lm", stroke_width=max(1, int(ui)), stroke_fill=(0, 0, 0, 190))


def generate_tdt_location_snapshot(proj: Path, radius_m: int, output_path: Path) -> dict[str, object]:
    from PIL import Image, ImageEnhance, ImageOps
    from _tools.s1_location_analysis import gcj02_to_wgs84

    load_env_file()
    tk = os.environ.get("TIANDITU_KEY", "").strip()
    if not tk:
        raise ValueError("缺少 TIANDITU_KEY，无法服务端生成天地图卫星快照")
    context_path = proj / "05_output" / "amap" / "s1_map_context.json"
    if not context_path.exists():
        raise ValueError("缺少 S1 高德上下文，无法读取中心点")
    context = json.loads(context_path.read_text(encoding="utf-8"))
    center_text = str(context.get("location", {}).get("amap_gcj02") or "")
    lng_gcj, lat_gcj = [float(part.strip()) for part in center_text.split(",", 1)]
    lng_wgs, lat_wgs = gcj02_to_wgs84(lng_gcj, lat_gcj)
    size = 1024
    target_mpp = (radius_m * 2 * 1.18) / size
    floating_zoom = math.log2((156543.03392 * math.cos(math.radians(lat_wgs))) / target_mpp)
    zoom = max(3, min(18, int(round(floating_zoom))))
    center_tile_x, center_tile_y = _wgs84_to_tile(lng_wgs, lat_wgs, zoom)
    center_px_x, center_px_y = center_tile_x * 256, center_tile_y * 256
    left, top = center_px_x - size / 2, center_px_y - size / 2
    first_x, last_x = math.floor(left / 256), math.floor((left + size - 1) / 256)
    first_y, last_y = math.floor(top / 256), math.floor((top + size - 1) / 256)
    mosaic = Image.new("RGB", (size, size), (30, 30, 30))
    for tile_x in range(first_x, last_x + 1):
        for tile_y in range(first_y, last_y + 1):
            tile = _fetch_tdt_tile("img", zoom, tile_x, tile_y, tk)
            px = int(tile_x * 256 - left)
            py = int(tile_y * 256 - top)
            mosaic.paste(tile, (px, py))
    bw = ImageOps.grayscale(mosaic).convert("RGB")
    bw = ImageEnhance.Contrast(bw).enhance(1.16)
    bw = ImageEnhance.Brightness(bw).enhance(0.72)
    _draw_location_overlay(bw, (lng_wgs, lat_wgs), zoom, radius_m)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    bw.save(output_path)
    return {"source": "server_tianditu_tiles", "zoom": zoom, "center_wgs84": f"{lng_wgs:.6f},{lat_wgs:.6f}"}


def generate_tdt_site_basemap(proj: Path, output_path: Path) -> dict[str, object]:
    from PIL import Image, ImageEnhance

    load_env_file()
    tk = os.environ.get("TIANDITU_KEY", "").strip()
    if not tk:
        raise ValueError("缺 TIANDITU_KEY，S2 天地图卫星底图不可用，请在仓库根 .env 配置")
    lng_gcj, lat_gcj = read_s2_center_gcj02(proj)
    tile_debug = estimate_s2_site_tile_debug(lng_gcj, lat_gcj)
    lng_wgs = float(tile_debug["center_wgs84"]["lng"])
    lat_wgs = float(tile_debug["center_wgs84"]["lat"])
    width = int(tile_debug["size"]["width"])
    height = int(tile_debug["size"]["height"])
    zoom = int(tile_debug["zoom"])
    first_x = int(tile_debug["tile_range"]["first_x"])
    last_x = int(tile_debug["tile_range"]["last_x"])
    first_y = int(tile_debug["tile_range"]["first_y"])
    last_y = int(tile_debug["tile_range"]["last_y"])
    left = float(tile_debug["pixel_origin"]["left"])
    top = float(tile_debug["pixel_origin"]["top"])
    mosaic = Image.new("RGB", (width, height), (30, 30, 30))
    for tile_x in range(first_x, last_x + 1):
        for tile_y in range(first_y, last_y + 1):
            tile = _fetch_tdt_tile("img", zoom, tile_x, tile_y, tk)
            px = int(tile_x * 256 - left)
            py = int(tile_y * 256 - top)
            mosaic.paste(tile, (px, py))
    mosaic = ImageEnhance.Contrast(mosaic).enhance(1.06)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mosaic.save(output_path)
    return {
        "source": "server_tianditu_tiles",
        "zoom": zoom,
        "center_gcj02": f"{lng_gcj:.6f},{lat_gcj:.6f}",
        "center_wgs84": f"{lng_wgs:.6f},{lat_wgs:.6f}",
        "size": {"width": width, "height": height},
        "tile_debug": tile_debug,
    }


def read_s2_center_gcj02(proj: Path) -> tuple[float, float]:
    context_path = proj / "05_output" / "amap" / "s1_map_context.json"
    if not context_path.exists():
        raise ValueError("missing_s1_map_context")
    context = json.loads(context_path.read_text(encoding="utf-8"))
    center_text = str(context.get("location", {}).get("amap_gcj02") or "")
    parts = [part.strip() for part in center_text.split(",", 1)]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError("missing_s1_center_gcj02")
    lng_gcj, lat_gcj = float(parts[0]), float(parts[1])
    if not (-180 <= lng_gcj <= 180 and -90 <= lat_gcj <= 90):
        raise ValueError("invalid_s1_center_gcj02")
    return lng_gcj, lat_gcj


def estimate_s2_site_tile_debug(lng_gcj: float, lat_gcj: float) -> dict[str, object]:
    from _tools.s1_location_analysis import gcj02_to_wgs84

    lng_wgs, lat_wgs = gcj02_to_wgs84(lng_gcj, lat_gcj)
    width, height, zoom = 1280, 820, 17
    center_tile_x, center_tile_y = _wgs84_to_tile(lng_wgs, lat_wgs, zoom)
    center_px_x, center_px_y = center_tile_x * 256, center_tile_y * 256
    left, top = center_px_x - width / 2, center_px_y - height / 2
    first_x, last_x = math.floor(left / 256), math.floor((left + width - 1) / 256)
    first_y, last_y = math.floor(top / 256), math.floor((top + height - 1) / 256)
    return {
        "zoom": zoom,
        "size": {"width": width, "height": height},
        "center_gcj02": {"lng": lng_gcj, "lat": lat_gcj},
        "center_wgs84": {"lng": lng_wgs, "lat": lat_wgs},
        "tile_range": {"first_x": first_x, "last_x": last_x, "first_y": first_y, "last_y": last_y},
        "pixel_origin": {"left": left, "top": top},
        "tile_count": (last_x - first_x + 1) * (last_y - first_y + 1),
    }


def build_s2_basemap_error_payload(
    exc: Exception,
    configured: bool,
    project: str,
    center_gcj02: str | None = None,
    tile_debug: dict[str, object] | None = None,
) -> dict[str, object]:
    error = str(exc)
    lowered = error.lower()
    if not configured or "tianditu_key" in lowered:
        reason = "missing_key"
        missing = "TIANDITU_KEY"
    elif "missing_s1" in lowered or "center" in lowered:
        reason = "missing_s1_center"
        missing = "s1_center_gcj02"
    elif "invalid_s1" in lowered or "could not convert" in lowered:
        reason = "invalid_s1_center"
        missing = None
    elif any(token in lowered for token in ("http", "urlopen", "tile", "timeout", "timed out", "connection")):
        reason = "tile_fetch_failed"
        missing = None
    else:
        reason = "unknown"
        missing = None
    return {
        "ok": False,
        "configured": configured,
        "reason": reason,
        "missing": missing,
        "project": project,
        "center_gcj02": center_gcj02,
        "tile_debug": tile_debug,
        "error": error,
    }


def _wgs84_to_gcj02_approx(lng: float, lat: float) -> tuple[float, float]:
    pi = 3.14159265358979324
    a = 6378245.0
    ee = 0.00669342162296594323

    def transform_lat(x: float, y: float) -> float:
        ret = -100 + 2 * x + 3 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
        ret += (20 * math.sin(6 * x * pi) + 20 * math.sin(2 * x * pi)) * 2 / 3
        ret += (20 * math.sin(y * pi) + 40 * math.sin(y / 3 * pi)) * 2 / 3
        ret += (160 * math.sin(y / 12 * pi) + 320 * math.sin(y * pi / 30)) * 2 / 3
        return ret

    def transform_lng(x: float, y: float) -> float:
        ret = 300 + x + 2 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
        ret += (20 * math.sin(6 * x * pi) + 20 * math.sin(2 * x * pi)) * 2 / 3
        ret += (20 * math.sin(x * pi) + 40 * math.sin(x / 3 * pi)) * 2 / 3
        ret += (150 * math.sin(x / 12 * pi) + 300 * math.sin(x / 30 * pi)) * 2 / 3
        return ret

    dlat = transform_lat(lng - 105, lat - 35)
    dlng = transform_lng(lng - 105, lat - 35)
    radlat = lat / 180 * pi
    magic = math.sin(radlat)
    magic = 1 - ee * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180) / ((a * (1 - ee)) / (magic * sqrtmagic) * pi)
    dlng = (dlng * 180) / (a / sqrtmagic * math.cos(radlat) * pi)
    return lng + dlng, lat + dlat


def _context_center_gcj02(context: dict) -> tuple[float, float] | None:
    center_text = str((context.get("location") or {}).get("amap_gcj02") or "")
    try:
        lng, lat = [float(part.strip()) for part in center_text.split(",", 1)]
    except (TypeError, ValueError):
        return None
    return lng, lat


def _semantic_geometry_to_normalized_path(
    geometry: object,
    coordinate_system: object,
    center_gcj02: tuple[float, float],
    radius_m: int,
) -> list[list[float]]:
    points = _geometry_points(geometry)
    if not points:
        return []
    center_lng, center_lat = center_gcj02
    cos_lat = max(0.000001, math.cos(math.radians(center_lat)))
    span_m = max(1.0, radius_m * 2 * 1.18)
    coords: list[list[float]] = []
    for lng, lat in points:
        if "wgs" in str(coordinate_system or "").lower():
            lng, lat = _wgs84_to_gcj02_approx(lng, lat)
        dx = (lng - center_lng) * 111320 * cos_lat
        dy = (lat - center_lat) * 110540
        x = 0.5 + dx / span_m
        y = 0.5 - dy / span_m
        if -0.2 <= x <= 1.2 and -0.2 <= y <= 1.2:
            coords.append([round(max(0.0, min(1.0, x)), 4), round(max(0.0, min(1.0, y)), 4)])
    return coords


def build_location_analysis_semantic_objects(proj: Path, radius_m: int) -> list[dict[str, object]]:
    context_path = proj / "05_output" / "amap" / "s1_map_context.json"
    if not context_path.exists():
        return []
    context = json.loads(context_path.read_text(encoding="utf-8"))
    center = _context_center_gcj02(context)
    if not center:
        return []
    surroundings = extract_surroundings_from_s1(context)
    objects: list[dict[str, object]] = []
    for index, road in enumerate(surroundings.get("roads") or [], start=1):
        if not isinstance(road, dict):
            continue
        coords = _semantic_geometry_to_normalized_path(
            road.get("geometry"),
            road.get("coordinate_system"),
            center,
            radius_m,
        )
        if len(coords) < 2:
            continue
        objects.append(
            {
                "id": f"auto-s1-road-{index}",
                "type": "location_road_line",
                "geometry": {"kind": "path", "closed": False, "coords": coords},
                "label": str(road.get("name") or f"road {index}"),
                "confidence": road.get("confidence") or "medium",
                "source": "s1_semantic_context",
                "style_hints": {
                    "inline_text": {"enabled": True, "text": str(road.get("name") or ""), "position": 0.5}
                },
            }
        )
    for index, water in enumerate(surroundings.get("water_features") or [], start=1):
        if not isinstance(water, dict) or "polygon" not in str((water.get("geometry") or {}).get("type") or "").lower():
            continue
        coords = _semantic_geometry_to_normalized_path(
            water.get("geometry"),
            water.get("coordinate_system"),
            center,
            radius_m,
        )
        if len(coords) < 3:
            continue
        if coords[0] != coords[-1]:
            coords.append(coords[0])
        objects.append(
            {
                "id": f"auto-s1-water-{index}",
                "type": "location_water_area",
                "geometry": {"kind": "path", "closed": True, "coords": coords},
                "label": str(water.get("name") or f"water {index}"),
                "confidence": water.get("confidence") or "medium",
                "source": "s1_semantic_context",
            }
        )
    return objects


def sync_location_analysis_drawing(proj: Path, code: str, screenshot_rel: str, radius_m: int) -> dict[str, object]:
    """Use the generated S1 snapshot as the editable workbench base image."""
    from PIL import Image

    suffix = "1km" if radius_m == 1000 else "2km"
    source_path = (proj / screenshot_rel).resolve()
    if proj.resolve() not in source_path.parents or not source_path.exists():
        raise ValueError("区位分析截图不存在，无法同步到图纸工作台")

    base_rel = f"05_output/drawings/base/location_analysis_{suffix}.png"
    base_path = proj / base_rel
    base_path.parent.mkdir(parents=True, exist_ok=True)
    base_path.write_bytes(source_path.read_bytes())

    with Image.open(base_path) as image:
        natural_width, natural_height = image.size

    rels = drawing_output_paths("location_analysis")
    semantic_path = proj / rels["semantic"]
    semantic_path.parent.mkdir(parents=True, exist_ok=True)

    if semantic_path.exists():
        try:
            drawing = normalize_drawing(json.loads(semantic_path.read_text(encoding="utf-8")), project_code=code)
        except Exception:
            drawing = empty_drawing(
                project_code=code,
                drawing_type="location_analysis",
                base_path=base_rel,
                natural_width=natural_width,
                natural_height=natural_height,
                base_source="sat_export",
            )
    else:
        drawing = empty_drawing(
            project_code=code,
            drawing_type="location_analysis",
            base_path=base_rel,
            natural_width=natural_width,
            natural_height=natural_height,
            base_source="sat_export",
        )

    drawing["base_image"] = {
        "path": base_rel,
        "natural_width": natural_width,
        "natural_height": natural_height,
        "source": "sat_export",
    }
    manual_objects = [
        obj
        for obj in drawing.get("objects", [])
        if isinstance(obj, dict) and obj.get("source") != "s1_semantic_context"
    ]
    auto_objects = build_location_analysis_semantic_objects(proj, radius_m)
    drawing["objects"] = manual_objects + auto_objects
    drawing = normalize_drawing(drawing, project_code=code)
    semantic_path.write_text(json.dumps(drawing, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "drawing_type": "location_analysis",
        "drawing_base_path": base_rel,
        "drawing_semantic_path": rels["semantic"],
        "drawing_object_count": len(drawing.get("objects", [])),
        "drawing_workbench_url": f"/?project={code}&page=workbench&drawing=location_analysis",
    }


def content_type_for(path: Path) -> str:
    mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    if path.suffix.lower() == ".svg":
        mime = "image/svg+xml"
    if (
        mime.startswith("text/")
        or mime in {"application/javascript", "application/json", "image/svg+xml"}
    ):
        return f"{mime}; charset=utf-8"
    return mime


def read_current_candidate_set_id(proj: Path) -> str | None:
    path = proj / CAD_CANDIDATES_REL
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    value = data.get("candidate_set_id")
    return str(value) if value else None


def short_candidate_set_id(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return "unknown"
    if ":" in text:
        text = text.split(":", 1)[1]
    text = re.sub(r"[^0-9a-fA-F]", "", text)
    return text[:16] or "unknown"


def _json_file(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _walk_coordinate_pairs(value: object, out: list[list[float]]) -> None:
    if (
        isinstance(value, list)
        and len(value) >= 2
        and isinstance(value[0], (int, float))
        and isinstance(value[1], (int, float))
    ):
        out.append([float(value[0]), float(value[1])])
        return
    if isinstance(value, list):
        for item in value:
            _walk_coordinate_pairs(item, out)


def redline_coordinate_reliability(points: list[list[float]], properties: dict) -> dict[str, object]:
    unit_note = str(properties.get("unit_note") or "").lower()
    looks_lonlat = bool(points) and all(-180 <= x <= 180 and -90 <= y <= 90 for x, y in points)
    projected_hint = any(token in unit_note for token in ("not wgs84", "not lon", "projected", "cad", "dxf"))
    reliable = looks_lonlat and not projected_hint
    if reliable:
        reason = "GeoJSON coordinates look like longitude/latitude and no CAD/projected warning was found."
    elif projected_hint:
        reason = properties.get("unit_note") or "GeoJSON properties indicate CAD/projected coordinates."
    else:
        reason = "GeoJSON coordinate range is outside longitude/latitude bounds."
    return {
        "reliable": reliable,
        "reason": reason,
        "placement": "geojson_coordinates" if reliable else "manual_rough_alignment",
    }


def normalize_redline_points(points: list[list[float]]) -> dict[str, object]:
    if len(points) < 3:
        raise ValueError("CAD 红线点数不足，无法生成叠加层")
    ring = points[:]
    if len(ring) > 1 and abs(ring[0][0] - ring[-1][0]) < 1e-9 and abs(ring[0][1] - ring[-1][1]) < 1e-9:
        ring = ring[:-1]
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    width = max(max_x - min_x, 1e-9)
    height = max(max_y - min_y, 1e-9)
    normalized = [
        {
            "x": (x - min_x) / width,
            "y": (max_y - y) / height,
        }
        for x, y in ring
    ]
    return {
        "normalized_points": normalized,
        "cad_bbox": [min_x, min_y, max_x, max_y],
        "aspect_ratio": width / height,
        "point_count": len(normalized),
    }


def read_redline_overlay(proj: Path, code: str) -> dict[str, object]:
    cad_dir = proj / "05_output" / "cad"
    preferred = cad_dir / "redline_candidate_1306.geojson"
    candidates = [preferred] if preferred.exists() else sorted(cad_dir.glob("redline_candidate_*.geojson"))
    if not candidates:
        return {
            "exists": False,
            "coordinate_reliability": {
                "reliable": False,
                "reason": "未找到 05_output/cad/redline_candidate_*.geojson",
                "placement": "missing",
            },
            "normalized_points": [],
        }
    path = candidates[0]
    data = _json_file(path)
    features = data.get("features") if isinstance(data, dict) else None
    feature = features[0] if isinstance(features, list) and features else {}
    properties = feature.get("properties") if isinstance(feature.get("properties"), dict) else {}
    geometry = feature.get("geometry") if isinstance(feature.get("geometry"), dict) else {}
    points: list[list[float]] = []
    _walk_coordinate_pairs(geometry.get("coordinates"), points)
    normalized = normalize_redline_points(points)
    reliability = redline_coordinate_reliability(points, properties)
    svg_path = cad_dir / "redline_candidate_1306.svg"
    preview_path = cad_dir / "site_preview.svg"
    return {
        "exists": True,
        "source": str(path.relative_to(proj)).replace("\\", "/"),
        "svg": str(svg_path.relative_to(proj)).replace("\\", "/") if svg_path.exists() else None,
        "site_preview_svg": str(preview_path.relative_to(proj)).replace("\\", "/") if preview_path.exists() else None,
        "handle": properties.get("handle"),
        "area_xy": properties.get("area_xy"),
        "unit_note": properties.get("unit_note"),
        "confidence": properties.get("confidence"),
        "coordinate_reliability": reliability,
        "default_transform": {
            "x": 0.5,
            "y": 0.5,
            "scale": 1.0,
            "rotation_deg": 0.0,
        },
        **normalized,
    }


def _append_unique_named(items: dict[str, dict], name: object, **fields: object) -> None:
    label = str(name or "").strip()
    if not label:
        return
    if label not in items:
        row = {"name": label}
        row.update({k: v for k, v in fields.items() if v not in (None, "", [])})
        items[label] = row
        return
    for key, value in fields.items():
        if value not in (None, "", []) and not items[label].get(key):
            items[label][key] = value


def _clean_geometry(geometry: object) -> dict[str, object] | None:
    if not isinstance(geometry, dict):
        return None
    geom_type = str(geometry.get("type") or "").strip()
    if geom_type not in {"Point", "LineString", "Polygon", "MultiLineString", "MultiPolygon"}:
        return None
    points: list[list[float]] = []
    _walk_coordinate_pairs(geometry.get("coordinates"), points)
    if not points:
        return None
    if geom_type == "Point" and len(points) >= 1:
        coordinates: object = [points[0][0], points[0][1]]
    else:
        coordinates = geometry.get("coordinates")
    return {"type": geom_type, "coordinates": coordinates}


def _geometry_points(geometry: object) -> list[list[float]]:
    cleaned = _clean_geometry(geometry)
    if not cleaned:
        return []
    points: list[list[float]] = []
    _walk_coordinate_pairs(cleaned.get("coordinates"), points)
    return points


def _geometry_centroid(geometry: object) -> tuple[float, float] | None:
    points = _geometry_points(geometry)
    if not points:
        return None
    return (
        sum(point[0] for point in points) / len(points),
        sum(point[1] for point in points) / len(points),
    )


def _line_geometry_from_location(location: object, span_deg: float = 0.0012) -> dict[str, object] | None:
    text = str(location or "").strip()
    if not text or "," not in text:
        return None
    try:
        lng, lat = [float(part.strip()) for part in text.split(",", 1)]
    except (TypeError, ValueError):
        return None
    if not (-180 <= lng <= 180 and -90 <= lat <= 90):
        return None
    return {
        "type": "LineString",
        "coordinates": [[lng - span_deg / 2, lat], [lng + span_deg / 2, lat]],
    }


def _osm_feature_tags(feature: object) -> dict[str, object]:
    if not isinstance(feature, dict):
        return {}
    tags = feature.get("tags") if isinstance(feature.get("tags"), dict) else {}
    properties = feature.get("properties") if isinstance(feature.get("properties"), dict) else {}
    merged = {}
    merged.update(tags)
    merged.update(properties)
    return merged


def _osm_road_level(tags: dict[str, object], name: object) -> str | None:
    highway = str(tags.get("highway") or "").strip().lower()
    ref = tags.get("ref")
    if highway in {"motorway", "trunk", "primary"}:
        return "primary"
    if highway in {"secondary", "tertiary"}:
        return "secondary"
    if highway in {"residential", "service", "unclassified", "living_street"}:
        return "local"
    return classify_road_level(ref or name)


def _is_osm_road(tags: dict[str, object], feature: object) -> bool:
    kind = str(feature.get("kind") or feature.get("type") or "").lower() if isinstance(feature, dict) else ""
    return kind == "road" or bool(tags.get("highway"))


def _is_osm_water(tags: dict[str, object], feature: object) -> bool:
    kind = str(feature.get("kind") or feature.get("type") or "").lower() if isinstance(feature, dict) else ""
    water_keys = {str(tags.get(key) or "").lower() for key in ("natural", "water", "waterway", "landuse")}
    return kind in {"water", "waterway"} or "water" in water_keys or bool(tags.get("waterway"))


def classify_road_level(name: object, fallback: str | None = None) -> str | None:
    label = str(name or "").strip()
    if fallback in {"primary", "secondary", "local"}:
        return fallback
    if PRIMARY_ROAD_RE.search(label):
        return "primary"
    if SECONDARY_ROAD_RE.search(label):
        return "secondary"
    if label.endswith(("路", "街", "桥", "巷")):
        return "local"
    return None


def _names_from_seed(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    names = []
    for item in value:
        if isinstance(item, dict):
            label = item.get("name")
        else:
            label = item
        if str(label or "").strip():
            names.append(str(label).strip())
    return names


def extract_surroundings_from_s1(context: dict) -> dict[str, object]:
    roads: dict[str, dict] = {}
    land_uses: dict[str, dict] = {}
    water_features: dict[str, dict] = {}
    notes: list[str] = []
    map_context = context.get("map_context") if isinstance(context.get("map_context"), dict) else {}
    regeo = map_context.get("regeo") if isinstance(map_context.get("regeo"), dict) else {}
    seed = context.get("s1_external_context_seed") if isinstance(context.get("s1_external_context_seed"), dict) else {}
    seed_features = seed.get("external_features") if isinstance(seed.get("external_features"), dict) else {}
    seed_amap = seed.get("amap_context") if isinstance(seed.get("amap_context"), dict) else {}
    osm_context = map_context.get("osm_context") if isinstance(map_context.get("osm_context"), dict) else {}

    for feature in osm_context.get("features") or []:
        if not isinstance(feature, dict):
            continue
        tags = _osm_feature_tags(feature)
        geometry = _clean_geometry(feature.get("geometry"))
        provider = str(feature.get("source") or osm_context.get("source") or "overpass")
        source = "osm_context"
        coordinate_system = str(
            feature.get("coordinate_system")
            or osm_context.get("coordinate_system")
            or "WGS84"
        )
        name = tags.get("name") or feature.get("name") or tags.get("ref") or feature.get("id")
        ref = tags.get("ref")
        if _is_osm_road(tags, feature):
            _append_unique_named(
                roads,
                name or ref,
                type="road",
                ref=ref,
                level=_osm_road_level(tags, name or ref),
                level_source="osm.highway",
                source=source,
                provider=provider,
                confidence=feature.get("confidence") or "medium",
                geometry=geometry,
                coordinate_system=coordinate_system,
            )
        elif _is_osm_water(tags, feature):
            label = name or tags.get("waterway") or tags.get("water") or "water_feature"
            _append_unique_named(
                water_features,
                label,
                type="water",
                waterway=tags.get("waterway"),
                source=source,
                provider=provider,
                confidence=feature.get("confidence") or "medium",
                geometry=geometry,
                coordinate_system=coordinate_system,
            )

    for item in regeo.get("roads") or []:
        if isinstance(item, dict):
            direction = item.get("direction")
            distance = item.get("distance") or item.get("distance_m")
            note = " / ".join(str(part) for part in (direction, f"{distance}m" if distance else None) if part)
            _append_unique_named(
                roads,
                item.get("name"),
                type="road",
                level=classify_road_level(item.get("name")),
                level_source="name_heuristic",
                source="regeo.roads",
                confidence="low_location_fallback" if item.get("location") else None,
                geometry=_line_geometry_from_location(item.get("location")),
                coordinate_system="GCJ-02",
                note=note,
            )
    for name in _names_from_seed(seed_features.get("primary_roads")):
        _append_unique_named(
            roads,
            name,
            type="road",
            level=classify_road_level(name, "primary"),
            level_source="s1_external_context_seed.primary_roads",
            source="s1_external_context_seed",
        )
    for name in _names_from_seed(seed_features.get("secondary_roads")):
        _append_unique_named(
            roads,
            name,
            type="road",
            level=classify_road_level(name, "secondary"),
            level_source="s1_external_context_seed.secondary_roads",
            source="s1_external_context_seed",
        )
    for name in _names_from_seed(seed_amap.get("roads")):
        _append_unique_named(
            roads,
            name,
            type="road",
            level=classify_road_level(name),
            level_source="name_heuristic",
            source="s1_external_context_seed",
        )

    poi_sources: list[tuple[str, list]] = []
    nearby = regeo.get("nearby_pois")
    if isinstance(nearby, list):
        poi_sources.append(("regeo.nearby_pois", nearby))
    keyword_context = map_context.get("keyword_context") if isinstance(map_context.get("keyword_context"), dict) else {}
    for key, value in keyword_context.items():
        items = value.get("items") if isinstance(value, dict) else []
        if isinstance(items, list):
            poi_sources.append((f"keyword_context.{key}", items))
    for source, items in poi_sources:
        for item in items:
            if not isinstance(item, dict):
                continue
            text = " ".join(str(item.get(key) or "") for key in ("name", "type", "address"))
            if "桥" in text:
                _append_unique_named(
                    roads,
                    item.get("name"),
                    type="bridge",
                    level=classify_road_level(item.get("name"), "local"),
                    level_source="poi_bridge_default",
                    source=source,
                    note=str(item.get("distance_m") or item.get("distance") or ""),
                )
            for match in ROAD_NAME_RE.findall(text):
                _append_unique_named(
                    roads,
                    match,
                    type="road",
                    level=classify_road_level(match),
                    level_source="name_heuristic",
                    source=source,
                    confidence="low_location_fallback" if item.get("location") else None,
                    geometry=_line_geometry_from_location(item.get("location")),
                    coordinate_system="GCJ-02",
                )

    poi_1000m = seed_amap.get("poi_1000m") if isinstance(seed_amap.get("poi_1000m"), dict) else {}
    for category, names in poi_1000m.items():
        for name in _names_from_seed(names):
            _append_unique_named(land_uses, name, category=category, source="s1_external_context_seed.poi_1000m")
    for name in _names_from_seed(seed_features.get("landscape_or_culture_nodes")):
        _append_unique_named(land_uses, name, category="landscape_or_culture_node", source="s1_external_context_seed")
    for name in _names_from_seed(seed_features.get("water_features")):
        _append_unique_named(
            water_features,
            name,
            type="water",
            source="s1_external_context_seed",
            confidence="seed",
        )
    for name in _names_from_seed(seed_amap.get("water_features")):
        _append_unique_named(
            water_features,
            name,
            type="water",
            source="s1_external_context_seed",
            confidence="seed",
        )

    address = regeo.get("formatted_address")
    if address:
        notes.append(f"S1 逆地理地址：{address}")
    if not roads:
        notes.append("S1 未返回明确道路；请在 UI 中手工补注入口所朝道路。")
    return {
        "roads": list(roads.values()),
        "land_uses": list(land_uses.values()),
        "water_features": list(water_features.values()),
        "notes": notes,
    }


def build_candidate_entrances(roads: object, redline: object) -> list[dict[str, object]]:
    if not isinstance(roads, list) or not isinstance(redline, dict):
        return []
    points = redline.get("normalized_points")
    if not isinstance(points, list) or len(points) < 2:
        return []
    usable_roads = [road for road in roads if isinstance(road, dict) and str(road.get("name") or "").strip()]
    normalized_points = []
    for point in points:
        if not isinstance(point, dict):
            continue
        try:
            normalized_points.append((float(point.get("x")), float(point.get("y"))))
        except (TypeError, ValueError):
            continue
    if len(normalized_points) < 2:
        return []

    geometry_points: list[list[float]] = []
    for road in usable_roads:
        geometry_points.extend(_geometry_points(road.get("geometry")))
    if geometry_points:
        lng_values = [point[0] for point in geometry_points]
        lat_values = [point[1] for point in geometry_points]
        min_lng, max_lng = min(lng_values), max(lng_values)
        min_lat, max_lat = min(lat_values), max(lat_values)
    else:
        min_lng = max_lng = min_lat = max_lat = 0.0

    level_priority = {"primary": 0, "secondary": 1, "local": 2}
    scored: list[tuple[tuple[int, float, int], dict[str, object]]] = []
    for order, road in enumerate(usable_roads):
        centroid = _geometry_centroid(road.get("geometry"))
        if centroid and geometry_points and max_lng != min_lng and max_lat != min_lat:
            road_x = (centroid[0] - min_lng) / (max_lng - min_lng)
            road_y = 1 - (centroid[1] - min_lat) / (max_lat - min_lat)
            source = "auto_s2_nearest_road_geometry"
            method = "normalized_geometry_centroid_to_redline_edge"
        else:
            road_x = 0.5
            road_y = 0.5
            source = "auto_s2_rough_alignment"
            method = "fallback_list_order"
        best_edge = 0
        best_t = 0.5
        best_distance = float("inf")
        for edge_index, a in enumerate(normalized_points):
            b = normalized_points[(edge_index + 1) % len(normalized_points)]
            dx = b[0] - a[0]
            dy = b[1] - a[1]
            len2 = dx * dx + dy * dy or 1.0
            t = max(0.0, min(1.0, ((road_x - a[0]) * dx + (road_y - a[1]) * dy) / len2))
            px = a[0] + dx * t
            py = a[1] + dy * t
            distance = math.hypot(road_x - px, road_y - py)
            if distance < best_distance:
                best_edge = edge_index
                best_t = t
                best_distance = distance
        candidate = {
            "id": f"ENT-C{len(scored) + 1}",
            "label": f"候选出入口 {len(scored) + 1}",
            "point_on_redline": {
                "edge_index": best_edge,
                "edge_t": round(best_t, 4),
            },
            "faces_road": str(road.get("name") or "").strip(),
            "road_level": road.get("level") or None,
            "source": source,
            "confidence": "candidate_needs_user_review",
            "distance_hint": {
                "method": method,
                "normalized_distance": round(best_distance if math.isfinite(best_distance) else 0.0, 4),
                "road_source": road.get("source"),
            },
        }
        geometry_priority = 0 if source == "auto_s2_nearest_road_geometry" else 1
        priority = level_priority.get(str(road.get("level") or ""), 3)
        scored.append(((geometry_priority, priority, candidate["distance_hint"]["normalized_distance"], order), candidate))

    scored.sort(key=lambda item: item[0])
    candidates: list[dict[str, object]] = []
    for index, (_, candidate) in enumerate(scored[: min(4, len(normalized_points))], start=1):
        candidate["id"] = f"ENT-C{index}"
        candidate["label"] = f"候选出入口 {index}"
        candidates.append(candidate)
    return candidates


def _finite_float(value: object, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} 必须是数字") from None
    if not math.isfinite(number):
        raise ValueError(f"{field} 必须是有限数字")
    return number


def _clean_named_items(value: object, field: str) -> list[dict[str, object]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{field} 必须是数组")
    cleaned = []
    for index, raw in enumerate(value, start=1):
        if isinstance(raw, str):
            name = raw.strip()
            row = {"name": name}
        elif isinstance(raw, dict):
            name = str(raw.get("name") or "").strip()
            row = {str(k): v for k, v in raw.items() if v not in (None, "", [])}
            row["name"] = name
        else:
            raise ValueError(f"{field}[{index}] 格式错误")
        if not name:
            raise ValueError(f"{field}[{index}].name 不能为空")
        cleaned.append(row)
    return cleaned


def _clean_notes(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [line.strip() for line in value.splitlines() if line.strip()]
    if not isinstance(value, list):
        raise ValueError("surroundings.notes 必须是数组或多行文本")
    return [str(item).strip() for item in value if str(item).strip()]


def _clean_geo_points(site_polygon_geo: object) -> dict[str, object]:
    if not isinstance(site_polygon_geo, dict):
        raise ValueError("site_polygon_geo 必须是对象")
    points = site_polygon_geo.get("points")
    if not isinstance(points, list) or len(points) < 3:
        raise ValueError("site_polygon_geo.points 至少需要 3 个点")
    cleaned_points = []
    for index, raw in enumerate(points, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"site_polygon_geo.points[{index}] 格式错误")
        lng = _finite_float(raw.get("lng"), f"site_polygon_geo.points[{index}].lng")
        lat = _finite_float(raw.get("lat"), f"site_polygon_geo.points[{index}].lat")
        if not (-180 <= lng <= 180 and -90 <= lat <= 90):
            raise ValueError(f"site_polygon_geo.points[{index}] 经纬度超出范围")
        cleaned_points.append({"lng": lng, "lat": lat})
    return {
        "coordinate_system": str(site_polygon_geo.get("coordinate_system") or "GCJ-02 / AMap approximate"),
        "points": cleaned_points,
        "confidence": str(site_polygon_geo.get("confidence") or "rough_overlay"),
    }


def clean_site_context_payload(payload: dict, code: str) -> dict[str, object]:
    north_deg = _finite_float(payload.get("north_deg"), "north_deg") % 360
    transform_raw = payload.get("redline_transform") if isinstance(payload.get("redline_transform"), dict) else {}
    transform = {
        "x": _finite_float(transform_raw.get("x", 0.5), "redline_transform.x"),
        "y": _finite_float(transform_raw.get("y", 0.5), "redline_transform.y"),
        "scale": _finite_float(transform_raw.get("scale", 1), "redline_transform.scale"),
        "rotation_deg": _finite_float(transform_raw.get("rotation_deg", 0), "redline_transform.rotation_deg") % 360,
    }
    if transform["scale"] <= 0:
        raise ValueError("redline_transform.scale 必须大于 0")
    site_polygon_geo = _clean_geo_points(payload.get("site_polygon_geo"))

    entrances_raw = payload.get("entrances")
    if not isinstance(entrances_raw, list) or not entrances_raw:
        raise ValueError("entrances 至少需要 1 个出入口")
    entrances = []
    for index, raw in enumerate(entrances_raw, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"entrances[{index}] 格式错误")
        faces_road = str(raw.get("faces_road") or "").strip()
        if not faces_road:
            raise ValueError(f"entrances[{index}].faces_road 不能为空")
        road_level = str(raw.get("road_level") or "").strip() or classify_road_level(faces_road)
        point = raw.get("point_on_redline")
        if not isinstance(point, dict):
            raise ValueError(f"entrances[{index}].point_on_redline 必须是对象")
        cleaned_point = {}
        if "lng" in point or "lat" in point:
            cleaned_point["lng"] = _finite_float(point.get("lng"), f"entrances[{index}].point_on_redline.lng")
            cleaned_point["lat"] = _finite_float(point.get("lat"), f"entrances[{index}].point_on_redline.lat")
        for key in ("edge_index", "edge_t", "screen_x", "screen_y"):
            if key in point:
                cleaned_point[key] = _finite_float(point.get(key), f"entrances[{index}].point_on_redline.{key}")
        entrances.append(
            {
                "id": str(raw.get("id") or f"ENT-{index}").strip(),
                "label": str(raw.get("label") or f"出入口 {index}").strip(),
                "point_on_redline": cleaned_point,
                "faces_road": faces_road,
                "road_level": road_level,
                "source": str(raw.get("source") or "").strip() or None,
                "confidence": str(raw.get("confidence") or "").strip() or None,
                "distance_hint": raw.get("distance_hint") if isinstance(raw.get("distance_hint"), dict) else None,
                "note": str(raw.get("note") or "").strip() or None,
            }
        )

    surroundings_raw = payload.get("surroundings") if isinstance(payload.get("surroundings"), dict) else {}
    surroundings = {
        "roads": _clean_named_items(surroundings_raw.get("roads"), "surroundings.roads"),
        "land_uses": _clean_named_items(surroundings_raw.get("land_uses"), "surroundings.land_uses"),
        "water_features": _clean_named_items(surroundings_raw.get("water_features"), "surroundings.water_features"),
        "notes": _clean_notes(surroundings_raw.get("notes")),
    }
    return {
        "schema_version": "1.0",
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "project": code,
        "north_deg": north_deg,
        "redline_transform": transform,
        "site_polygon_geo": site_polygon_geo,
        "entrances": entrances,
        "surroundings": surroundings,
        "source": "uploader_s2_redline_overlay",
    }


def style_presets_path() -> Path:
    path = STYLE_PRESETS_FILE.resolve()
    repo = REPO_ROOT.resolve()
    if path != repo and repo not in path.parents:
        raise ValueError("style preset path must stay inside repository")
    return path


def normalize_style_preset(raw: object) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("style preset must be an object")
    preset_id = str(raw.get("id") or "").strip()
    name = str(raw.get("name") or "").strip()
    kind = str(raw.get("kind") or "").strip()
    hints = raw.get("hints")
    if not preset_id:
        preset_id = f"preset-{int(time.time() * 1000)}"
    if not re.match(r"^[A-Za-z0-9_.:-]+$", preset_id):
        raise ValueError("style preset id contains unsupported characters")
    if not name:
        raise ValueError("style preset name is required")
    if kind not in OBJECT_TYPE_REGISTRY:
        raise ValueError(f"style preset kind must be one of {sorted(OBJECT_TYPE_REGISTRY)}")
    if not isinstance(hints, dict):
        raise ValueError("style preset hints must be an object")
    normalized = {
        "id": preset_id,
        "name": name,
        "kind": kind,
        "hints": hints,
    }
    if raw.get("created_at"):
        normalized["created_at"] = str(raw["created_at"])
    if raw.get("updated_at"):
        normalized["updated_at"] = str(raw["updated_at"])
    return normalized


def read_style_preset_library() -> dict:
    path = style_presets_path()
    if not path.exists():
        return {"schema_version": "1.0", "updated_at": "", "presets": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    presets = [normalize_style_preset(item) for item in data.get("presets", [])]
    return {
        "schema_version": str(data.get("schema_version") or "1.0"),
        "updated_at": str(data.get("updated_at") or ""),
        "presets": presets,
    }


def write_style_preset_library(presets: list[dict]) -> dict:
    path = style_presets_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    library = {
        "schema_version": "1.0",
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "presets": [normalize_style_preset(item) for item in presets],
    }
    path.write_text(json.dumps(library, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return library


def build_env_check_payload() -> dict[str, object]:
    loaded_env = load_env_file()
    key_env = configured_env_name(("AMAP_JSAPI_KEY",))
    key = os.environ.get(key_env, "").strip() if key_env else ""
    service_host = os.environ.get("AMAP_JSAPI_SERVICE_HOST", "").strip()
    security_jscode = os.environ.get("AMAP_JSAPI_SECURITY_JSCODE", "").strip()
    webservice_key_env = configured_env_name(AMAP_WEBSERVICE_ENV_NAMES)
    tdt_key = os.environ.get("TIANDITU_KEY", "").strip()
    env_file_exists = ENV_FILE.exists()
    warnings: list[str] = []

    security: dict[str, object] = {"mode": "none"}
    if service_host:
        security = {"mode": "service_host", "service_host": service_host}
    elif security_jscode:
        security = {"mode": "security_jscode", "security_jscode": security_jscode}
    elif key:
        warnings.append("未配置 AMAP_JSAPI_SECURITY_JSCODE 或 AMAP_JSAPI_SERVICE_HOST；若控制台启用安全密钥，S1 高德地图会加载失败。")

    if not env_file_exists:
        warnings.append("未找到仓库根目录 .env；请复制 .env.example 后配置地图 key。")
    if not tdt_key:
        warnings.append("缺 TIANDITU_KEY，S1/S2 天地图高清卫星底图不可用，请在仓库根 .env 配置。")
    if not webservice_key_env:
        warnings.append("缺 AMAP_WEBSERVICE_KEY，无法生成 S1 高德上下文和周边路网语义。")
    if not key:
        warnings.append("未配置 AMAP_JSAPI_KEY；S1 高德拾点地图不可用，但 S2 底图不依赖它。")

    return {
        "ok": True,
        "configured": bool(key_env),
        "key": key or None,
        "key_env": key_env,
        "webservice_configured": bool(webservice_key_env),
        "webservice_key_env": webservice_key_env,
        "tianditu_configured": bool(tdt_key),
        "tianditu_key": tdt_key or None,
        "security": security,
        "warnings": warnings,
        "referer_hint": AMAP_JSAPI_REFERER_HINT,
        "env_loaded": loaded_env,
        "env_file_exists": env_file_exists,
    }


class UploaderHandler(BaseHTTPRequestHandler):
    server_version = "ArchitectureUploader/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/projects":
                self.handle_projects()
            elif parsed.path == "/api/inventory":
                self.handle_inventory(parsed.query)
            elif parsed.path == "/api/validate":
                self.handle_validate(parsed.query)
            elif parsed.path == "/api/amap-check":
                self.handle_amap_check()
            elif parsed.path == "/api/amap-jsapi-config":
                self.handle_amap_jsapi_config()
            elif parsed.path == "/api/env-check":
                self.handle_env_check()
            elif parsed.path == "/api/s2/basemap":
                self.handle_s2_basemap(parsed.query)
            elif parsed.path == "/api/spatial":
                self.handle_spatial(parsed.query)
            elif parsed.path == "/api/site-context":
                self.handle_site_context_load(parsed.query)
            elif parsed.path == "/api/cad-preview":
                self.handle_cad_preview(parsed.query, run=False)
            elif parsed.path == "/api/drawing/registry":
                self.handle_drawing_registry()
            elif parsed.path == "/api/drawing/style-presets":
                self.handle_style_presets_load()
            elif parsed.path == "/api/drawing/deck-layout":
                self.handle_deck_layout_load(parsed.query)
            elif parsed.path == "/api/drawing/load":
                self.handle_drawing_load(parsed.query)
            elif parsed.path == "/api/drawing/supporting/list":
                self.handle_supporting_list(parsed.query)
            elif parsed.path == "/api/style/load":
                self.handle_style_load(parsed.query)
            elif parsed.path == "/api/project-file":
                self.serve_project_file(parsed.query)
            else:
                self.serve_static(parsed.path)
        except Exception as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/projects":
                self.handle_create_project()
            elif parsed.path == "/api/upload":
                self.handle_upload(parsed.query)
            elif parsed.path == "/api/amap-context":
                self.handle_amap_context()
            elif parsed.path == "/api/s1/auto-draft":
                self.handle_s1_auto_draft()
            elif parsed.path == "/api/control-points":
                self.handle_control_points()
            elif parsed.path == "/api/control-points/archive":
                self.handle_control_points_archive(archive=True)
            elif parsed.path == "/api/control-points/migration-report":
                self.handle_control_points_archive(archive=False)
            elif parsed.path == "/api/site-context":
                self.handle_site_context_save()
            elif parsed.path == "/api/cad-candidate-semantics":
                self.handle_cad_candidate_semantics()
            elif parsed.path == "/api/alignment-check":
                self.handle_alignment_check()
            elif parsed.path == "/api/cad-preview":
                self.handle_cad_preview("", run=True)
            elif parsed.path == "/api/drawing/base/upload":
                self.handle_drawing_base_upload(parsed.query)
            elif parsed.path == "/api/drawing/save":
                self.handle_drawing_save()
            elif parsed.path == "/api/drawing/supporting/upload":
                self.handle_supporting_upload(parsed.query)
            elif parsed.path == "/api/drawing/supporting/update":
                self.handle_supporting_update()
            elif parsed.path == "/api/drawing/supporting/delete":
                self.handle_supporting_delete()
            elif parsed.path == "/api/drawing/task-pack":
                self.handle_drawing_task_pack()
            elif parsed.path == "/api/drawing/export":
                self.handle_drawing_export(parsed.query)
            elif parsed.path == "/api/drawing/style-presets/save":
                self.handle_style_presets_save()
            elif parsed.path == "/api/drawing/style-presets/delete":
                self.handle_style_presets_delete()
            elif parsed.path == "/api/drawing/style-presets/import":
                self.handle_style_presets_import()
            elif parsed.path == "/api/drawing/deck-layout/save":
                self.handle_deck_layout_save()
            elif parsed.path == "/api/drawing/deck-layout/reflow":
                self.handle_deck_layout_reflow()
            elif parsed.path == "/api/drawing/deck-layout/export":
                self.handle_deck_layout_export()
            elif parsed.path == "/api/style/save":
                self.handle_style_save()
            else:
                self.send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
        except Exception as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def log_message(self, format: str, *args: object) -> None:
        print(f"[uploader] {self.address_string()} - {format % args}")

    def send_json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def serve_static(self, path: str) -> None:
        if path in ("", "/"):
            path = "/index.html"
        rel = path.lstrip("/")
        target = (STATIC_DIR / rel).resolve()
        if STATIC_DIR.resolve() not in target.parents and target != STATIC_DIR.resolve():
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        if not target.exists() or not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type_for(target))
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def serve_project_file(self, query: str) -> None:
        params = parse_qs(query)
        code = safe_project(params.get("project", [""])[0])
        rel = str(params.get("path", [""])[0]).replace("\\", "/").lstrip("/")
        if not rel.startswith("05_output/"):
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        proj = project_dir(code)
        target = (proj / rel).resolve()
        output_dir = (proj / "05_output").resolve()
        if output_dir not in target.parents and target != output_dir:
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        if not target.exists() or not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type_for(target))
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def drawing_paths(self, proj: Path, drawing_type: str) -> dict[str, Path]:
        rels = drawing_output_paths(drawing_type)
        return {key: proj / rel for key, rel in rels.items()}

    def project_file_url(self, code: str, rel_path: str | None) -> str | None:
        if not rel_path:
            return None
        return f"/api/project-file?project={code}&path={rel_path}"

    def default_drawing_for_project(self, code: str, proj: Path, drawing_type: str) -> dict[str, object]:
        base_rel = default_base_path_for(drawing_type)
        width = 1
        height = 1
        base_path = proj / base_rel
        if base_path.exists():
            try:
                from PIL import Image

                with Image.open(base_path) as image:
                    width, height = image.size
            except Exception:
                width = height = 1
        return empty_drawing(
            project_code=code,
            drawing_type=drawing_type,
            base_path=base_rel,
            natural_width=width,
            natural_height=height,
            base_source="user_upload",
        )

    def handle_drawing_registry(self) -> None:
        drawings = {}
        for dt_id, dt_info in DRAWING_REGISTRY.items():
            drawings[dt_id] = {
                "label": dt_info["label"],
                "status": dt_info["status"],
                "category": dt_info["category"],
                "default_base_path": dt_info["default_base_path"],
                "object_types": dt_info["object_types"],
                "tools": dt_info["tools"],
            }
        objects = {}
        for ot_id, ot_info in OBJECT_TYPE_REGISTRY.items():
            objects[ot_id] = {
                "label": ot_info["label"],
                "geometry": ot_info["geometry"],
                "closed": ot_info["closed"],
                "default_style": default_object_style(ot_id),
            }
        self.send_json({
            "ok": True,
            "schema_version": "1.0",
            "default_drawing_type": "functional_zoning",
            "drawings": drawings,
            "objects": objects,
        })

    def handle_style_presets_load(self) -> None:
        library = read_style_preset_library()
        rel = str(style_presets_path().relative_to(REPO_ROOT)).replace("\\", "/")
        self.send_json({"ok": True, "path": rel, **library})

    def handle_style_presets_save(self) -> None:
        payload = self.read_json()
        preset = normalize_style_preset(payload.get("preset") or payload)
        library = read_style_preset_library()
        presets = [item for item in library["presets"] if item["id"] != preset["id"]]
        presets.append(preset)
        next_library = write_style_preset_library(presets)
        rel = str(style_presets_path().relative_to(REPO_ROOT)).replace("\\", "/")
        self.send_json({"ok": True, "path": rel, **next_library})

    def handle_style_presets_delete(self) -> None:
        payload = self.read_json()
        preset_id = str(payload.get("id") or "").strip()
        if not preset_id:
            raise ValueError("style preset id is required")
        library = read_style_preset_library()
        presets = [item for item in library["presets"] if item["id"] != preset_id]
        if len(presets) == len(library["presets"]):
            raise ValueError(f"style preset not found: {preset_id}")
        next_library = write_style_preset_library(presets)
        rel = str(style_presets_path().relative_to(REPO_ROOT)).replace("\\", "/")
        self.send_json({"ok": True, "path": rel, **next_library})

    def handle_style_presets_import(self) -> None:
        payload = self.read_json()
        source = payload.get("library") or payload
        presets_raw = source.get("presets") if isinstance(source, dict) else None
        if not isinstance(presets_raw, list):
            raise ValueError("import payload must contain presets array")
        imported = [normalize_style_preset(item) for item in presets_raw]
        library = read_style_preset_library()
        merged = {item["id"]: item for item in library["presets"]}
        for item in imported:
            merged[item["id"]] = item
        next_library = write_style_preset_library(list(merged.values()))
        rel = str(style_presets_path().relative_to(REPO_ROOT)).replace("\\", "/")
        self.send_json({"ok": True, "path": rel, "imported": len(imported), **next_library})

    def handle_deck_layout_load(self, query: str) -> None:
        params = parse_qs(query)
        code = safe_project(params.get("project", [""])[0])
        proj = project_dir(code)
        layout = load_deck_layout(proj, code)
        self.send_json({
            "ok": True,
            "project": code,
            "path": layout_rel_path(),
            "exists": (proj / layout_rel_path()).exists(),
            "layout": layout,
        })

    def handle_deck_layout_save(self) -> None:
        payload = self.read_json()
        code = safe_project(str(payload.get("project", "")))
        proj = project_dir(code)
        layout = load_deck_layout(proj, code)
        if isinstance(payload.get("layout"), dict):
            layout = payload["layout"]
        drawing_type = str(payload.get("drawing_type") or "").strip()
        if drawing_type:
            if drawing_type not in DRAWING_TYPES:
                raise ValueError(f"drawing_type must be one of {sorted(DRAWING_TYPES)}")
            slide_patch = payload.get("slide") if isinstance(payload.get("slide"), dict) else {}
            slide = (layout.get("slides") or {}).get(drawing_type) or {}
            if "text" in slide_patch:
                slide["text"] = str(slide_patch.get("text") or "")
            if "title" in slide_patch:
                slide["title"] = str(slide_patch.get("title") or "")
            if isinstance(slide_patch.get("typography"), dict):
                slide["typography"] = slide_patch["typography"]
            if isinstance(slide_patch.get("elements"), dict):
                slide["elements"] = slide_patch["elements"]
            if "manual_overrides" in slide_patch:
                slide["manual_overrides"] = bool(slide_patch.get("manual_overrides"))
            layout.setdefault("slides", {})[drawing_type] = slide
        if isinstance(payload.get("title_style"), dict):
            layout["title_style"] = payload["title_style"]
        if "typography_accent" in payload:
            layout["typography_accent"] = str(payload.get("typography_accent") or "")
        if "template_side" in payload:
            layout = set_template_side(layout, str(payload.get("template_side") or ""))
        if isinstance(payload.get("drawing_frame"), dict):
            layout = set_drawing_frame(layout, payload["drawing_frame"])
        saved = save_deck_layout(proj, layout, code)
        self.send_json({"ok": True, "project": code, "path": layout_rel_path(), "layout": saved})

    def handle_deck_layout_reflow(self) -> None:
        payload = self.read_json()
        code = safe_project(str(payload.get("project", "")))
        proj = project_dir(code)
        layout = load_deck_layout(proj, code)
        scope = str(payload.get("scope") or "current")
        drawing_type = str(payload.get("drawing_type") or "").strip()
        if scope == "all":
            drawing_type_arg = None
        else:
            if drawing_type not in DRAWING_TYPES:
                raise ValueError(f"drawing_type must be one of {sorted(DRAWING_TYPES)}")
            drawing_type_arg = drawing_type
        layout = reflow_deck(proj, layout, drawing_type=drawing_type_arg)
        saved = save_deck_layout(proj, layout, code)
        self.send_json({"ok": True, "project": code, "path": layout_rel_path(), "layout": saved})

    def handle_deck_layout_export(self) -> None:
        payload = self.read_json()
        code = safe_project(str(payload.get("project", "")))
        proj = project_dir(code)
        layout = load_deck_layout(proj, code)
        result = export_deck_pptx(proj, layout, code)
        self.send_json({"ok": True, "project": code, **result})

    def handle_supporting_list(self, query: str) -> None:
        params = parse_qs(query)
        code = safe_project(params.get("project", [""])[0])
        drawing_type = str(params.get("drawing_type", [""])[0]).strip()
        if drawing_type not in DRAWING_TYPES:
            raise ValueError(f"drawing_type must be one of {sorted(DRAWING_TYPES)}")
        proj = project_dir(code)
        manifest_path = proj / "05_output" / "drawings" / "supporting" / drawing_type / "manifest.json"
        if not manifest_path.exists():
            self.send_json({"ok": True, "project": code, "drawing_type": drawing_type, "images": [], "count": 0})
            return
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        images = manifest.get("images", [])
        self.send_json({
            "ok": True,
            "project": code,
            "drawing_type": drawing_type,
            "images": images,
            "count": len(images),
        })

    def handle_supporting_upload(self, query: str) -> None:
        params = parse_qs(query)
        code = safe_project(params.get("project", [""])[0])
        drawing_type = str(params.get("drawing_type", [""])[0]).strip()
        if drawing_type not in DRAWING_TYPES:
            raise ValueError(f"drawing_type must be one of {sorted(DRAWING_TYPES)}")
        proj = project_dir(code)

        content_type = self.headers.get("Content-Type", "")
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length > 0 else b""
        files = iter_multipart_files(content_type, body) if "multipart/form-data" in content_type else []
        if not files:
            raise ValueError("请选择图片文件")

        allowed_ext = {".jpg", ".jpeg", ".png", ".webp"}
        sup_dir = proj / "05_output" / "drawings" / "supporting" / drawing_type
        sup_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = sup_dir / "manifest.json"

        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        else:
            manifest = {"schema_version": "1.0", "project_code": code, "drawing_type": drawing_type, "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "images": []}

        saved = []
        for fname, payload in files:
            filename = sanitize_filename(fname)
            suffix = Path(filename).suffix.lower()
            if suffix not in allowed_ext:
                raise ValueError(f"不支持的文件格式: {suffix}")
            out = unique_dash_path(sup_dir, filename)
            out.write_bytes(payload)
            rel = str(out.relative_to(proj)).replace("\\", "/")
            img_id = f"img-{time.strftime('%Y%m%d-%H%M%S')}-{len(manifest['images'])+1:03d}"
            entry = {
                "id": img_id,
                "file": rel,
                "original_name": filename,
                "caption": "",
                "sort_order": len(manifest["images"]) + 1,
                "notes": "",
                "uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            }
            manifest["images"].append(entry)
            saved.append(entry)

        manifest["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        self.send_json({
            "ok": True,
            "project": code,
            "drawing_type": drawing_type,
            "saved": saved,
            "count": len(saved),
        })

    def handle_supporting_update(self) -> None:
        payload = self.read_json()
        code = safe_project(str(payload.get("project", "")))
        drawing_type = str(payload.get("drawing_type", "")).strip()
        if drawing_type not in DRAWING_TYPES:
            raise ValueError(f"drawing_type must be one of {sorted(DRAWING_TYPES)}")
        proj = project_dir(code)
        manifest_path = proj / "05_output" / "drawings" / "supporting" / drawing_type / "manifest.json"
        if not manifest_path.exists():
            raise ValueError("manifest 不存在")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        image_id = str(payload.get("image_id", "")).strip()
        for img in manifest.get("images", []):
            if img.get("id") == image_id:
                if "caption" in payload:
                    img["caption"] = str(payload["caption"])
                if "notes" in payload:
                    img["notes"] = str(payload["notes"])
                if "sort_order" in payload:
                    img["sort_order"] = int(payload["sort_order"])
                break
        else:
            raise ValueError(f"image_id {image_id} not found")
        manifest["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        self.send_json({"ok": True, "project": code, "drawing_type": drawing_type})

    def handle_supporting_delete(self) -> None:
        payload = self.read_json()
        code = safe_project(str(payload.get("project", "")))
        drawing_type = str(payload.get("drawing_type", "")).strip()
        if drawing_type not in DRAWING_TYPES:
            raise ValueError(f"drawing_type must be one of {sorted(DRAWING_TYPES)}")
        proj = project_dir(code)
        manifest_path = proj / "05_output" / "drawings" / "supporting" / drawing_type / "manifest.json"
        if not manifest_path.exists():
            raise ValueError("manifest 不存在")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        image_id = str(payload.get("image_id", "")).strip()
        sup_dir = proj / "05_output" / "drawings" / "supporting" / drawing_type
        new_images = []
        deleted_file = None
        for img in manifest.get("images", []):
            if img.get("id") == image_id:
                file_path = (proj / img.get("file", "")).resolve()
                if sup_dir.resolve() in file_path.parents and file_path.exists():
                    file_path.unlink()
                    deleted_file = img.get("file")
            else:
                new_images.append(img)
        manifest["images"] = new_images
        manifest["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        self.send_json({"ok": True, "project": code, "drawing_type": drawing_type, "deleted_file": deleted_file})

    def handle_drawing_load(self, query: str) -> None:
        params = parse_qs(query)
        code = safe_project(params.get("project", [""])[0])
        drawing_type = str(params.get("drawing_type", [""])[0]).strip()
        if drawing_type not in DRAWING_TYPES:
            raise ValueError(f"drawing_type must be one of {sorted(DRAWING_TYPES)}")
        proj = project_dir(code)
        paths = self.drawing_paths(proj, drawing_type)
        rels = drawing_output_paths(drawing_type)
        semantic_path = paths["semantic"]
        if semantic_path.exists():
            drawing = normalize_drawing(
                json.loads(semantic_path.read_text(encoding="utf-8")),
                project_code=code,
            )
            exists = True
        else:
            drawing = self.default_drawing_for_project(code, proj, drawing_type)
            exists = False

        self.send_json(
            {
                "ok": True,
                "project": code,
                "drawing_type": drawing_type,
                "exists": exists,
                "drawing": drawing,
                "paths": rels,
                "base_image_exists": (proj / drawing["base_image"]["path"]).exists(),
                "base_image_url": self.project_file_url(code, drawing["base_image"]["path"]),
                "svg_exists": paths["svg"].exists(),
                "svg_url": self.project_file_url(code, rels["svg"]) if paths["svg"].exists() else None,
                "png_exists": paths["png"].exists(),
                "png_url": self.project_file_url(code, rels["png"]) if paths["png"].exists() else None,
                "pdf_exists": paths["pdf"].exists(),
                "pdf_url": self.project_file_url(code, rels["pdf"]) if paths["pdf"].exists() else None,
            }
        )

    def handle_drawing_base_upload(self, query: str) -> None:
        params = parse_qs(query)
        code = safe_project(params.get("project", [""])[0])
        proj = project_dir(code)
        if not proj.exists():
            raise ValueError("请先创建项目，再上传底图")

        content_type = self.headers.get("Content-Type", "")
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length > 0 else b""
        files = iter_multipart_files(content_type, body) if "multipart/form-data" in content_type else []
        if not files:
            raise ValueError("请选择 JPG 或 PNG 底图文件")

        fname, payload = files[0]
        filename = sanitize_filename(fname)
        suffix = Path(filename).suffix.lower()
        if suffix not in {".jpg", ".jpeg", ".png"}:
            raise ValueError("底图只支持 JPG/PNG")
        target_dir = proj / "05_output" / "drawings" / "base"
        target_dir.mkdir(parents=True, exist_ok=True)
        out = unique_dash_path(target_dir, filename)
        out.write_bytes(payload)
        rel = str(out.relative_to(proj)).replace("\\", "/")
        self.send_json(
            {
                "ok": True,
                "project": code,
                "path": rel,
                "url": self.project_file_url(code, rel),
                "filename": out.name,
            }
        )

    def handle_drawing_save(self) -> None:
        payload = self.read_json()
        code = safe_project(str(payload.get("project", "")))
        proj = project_dir(code)
        drawing = normalize_drawing(payload.get("drawing") or payload, project_code=code)
        paths = self.drawing_paths(proj, drawing["drawing_type"])
        paths["semantic"].parent.mkdir(parents=True, exist_ok=True)
        paths["semantic"].write_text(json.dumps(drawing, ensure_ascii=False, indent=2), encoding="utf-8")
        rels = drawing_output_paths(drawing["drawing_type"])
        self.send_json(
            {
                "ok": True,
                "project": code,
                "drawing_type": drawing["drawing_type"],
                "path": rels["semantic"],
                "drawing": drawing,
            }
        )

    def handle_drawing_task_pack(self) -> None:
        payload = self.read_json()
        code = safe_project(str(payload.get("project", "")))
        drawing_type = str(payload.get("drawing_type") or "").strip()
        if drawing_type not in DRAWING_TYPES:
            raise ValueError(f"drawing_type must be one of {sorted(DRAWING_TYPES)}")
        rels = drawing_output_paths(drawing_type)
        pack_path = build_task_pack(
            code,
            drawing_type,
            sketch_path=rels["semantic"],
            user_notes=str(payload.get("user_notes") or ""),
        )
        self.send_json(
            {
                "ok": True,
                "project": code,
                "drawing_type": drawing_type,
                "task_pack": str(pack_path.relative_to(REPO_ROOT)).replace("\\", "/"),
                "task_pack_project_path": str(pack_path.relative_to(project_dir(code))).replace("\\", "/"),
            }
        )

    def handle_drawing_export(self, query: str) -> None:
        params = parse_qs(query)
        code = safe_project(params.get("project", [""])[0])
        drawing_type = str(params.get("drawing_type", [""])[0]).strip()
        if drawing_type not in DRAWING_TYPES:
            raise ValueError(f"drawing_type must be one of {sorted(DRAWING_TYPES)}")
        proj = project_dir(code)
        rels = drawing_output_paths(drawing_type)
        svg_path = proj / rels["svg"]
        outputs = export_svg(svg_path, proj / "05_output" / "drawings", formats=("png", "pdf"), dpi=300, page_size="A3")
        rel_outputs = {key: str(path.relative_to(proj)).replace("\\", "/") for key, path in outputs.items()}
        self.send_json(
            {
                "ok": True,
                "project": code,
                "drawing_type": drawing_type,
                "outputs": rel_outputs,
                "urls": {key: self.project_file_url(code, rel) for key, rel in rel_outputs.items()},
            }
        )

    def handle_style_load(self, query: str) -> None:
        params = parse_qs(query)
        code = safe_project(params.get("project", [""])[0])
        proj = project_dir(code)
        path = proj / "05_output" / "style" / "style_spec.json"
        rel = "05_output/style/style_spec.json"
        if not path.exists():
            self.send_json({"ok": True, "project": code, "exists": False, "path": rel})
            return
        style_spec = validate_style_spec(json.loads(path.read_text(encoding="utf-8")))
        self.send_json(
            {
                "ok": True,
                "project": code,
                "exists": True,
                "path": rel,
                "style_spec": style_spec,
            }
        )

    def handle_style_save(self) -> None:
        payload = self.read_json()
        code = safe_project(str(payload.get("project", "")))
        proj = project_dir(code)
        style_spec = validate_style_spec(payload.get("style_spec") or payload)
        path = proj / "05_output" / "style" / "style_spec.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(style_spec, ensure_ascii=False, indent=2), encoding="utf-8")
        rel = "05_output/style/style_spec.json"
        self.send_json(
            {
                "ok": True,
                "project": code,
                "path": rel,
                "style_spec": style_spec,
            }
        )

    def handle_projects(self) -> None:
        PROJECTS_DIR.mkdir(exist_ok=True)
        projects = []
        for path in sorted(PROJECTS_DIR.iterdir()):
            if not path.is_dir():
                continue
            record = path / "05_output" / "record.md"
            projects.append(
                {
                    "code": path.name,
                    "record_exists": record.exists(),
                    "path": str(path.relative_to(REPO_ROOT)),
                }
            )
        self.send_json({"projects": projects})

    def handle_create_project(self) -> None:
        payload = self.read_json()
        code = safe_project(str(payload.get("code", "")))
        name = str(payload.get("name") or code).strip()
        project_type = str(payload.get("type") or "unknown")
        if project_type not in VALID_TYPES:
            raise ValueError(f"未知项目类型: {project_type}")
        args = [
            "_tools/init_project/scaffold.py",
            code,
            "--type",
            project_type,
            "--name",
            name,
            "--resume",
        ]
        rc, stdout, stderr = run_tool(args)
        self.send_json(
            {
                "ok": rc == 0,
                "returncode": rc,
                "stdout": stdout,
                "stderr": stderr,
                "project": code,
            },
            HTTPStatus.OK if rc == 0 else HTTPStatus.BAD_REQUEST,
        )

    def handle_upload(self, query: str) -> None:
        params = parse_qs(query)
        code = safe_project(params.get("project", [""])[0])
        bucket = params.get("bucket", [""])[0]
        if bucket not in BUCKETS:
            raise ValueError("未知资料分类")
        proj = project_dir(code)
        if not proj.exists():
            raise ValueError("请先创建项目，再上传资料")
        target_dir = proj / BUCKETS[bucket]
        if not target_dir.exists():
            target_dir.mkdir(parents=True, exist_ok=True)

        content_type = self.headers.get("Content-Type", "")
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length > 0 else b""

        saved = []
        if "multipart/form-data" in content_type:
            for fname, payload in iter_multipart_files(content_type, body):
                filename = sanitize_filename(fname)
                out = unique_path(target_dir, filename)
                out.write_bytes(payload)
                saved.append(str(out.relative_to(proj)).replace("\\", "/"))

        self.send_json(
            {
                "ok": True,
                "project": code,
                "bucket": bucket,
                "target_dir": BUCKETS[bucket],
                "saved": saved,
                "count": len(saved),
            }
        )

    def handle_inventory(self, query: str) -> None:
        params = parse_qs(query)
        code = safe_project(params.get("project", [""])[0])
        args = ["_tools/inventory.py", code, "--json", "--write"]
        rc, stdout, stderr = run_tool(args)
        payload = json.loads(stdout) if stdout.strip().startswith("{") else {"stdout": stdout}
        payload.update({"ok": rc == 0, "returncode": rc, "stderr": stderr})
        self.send_json(payload, HTTPStatus.OK if rc in (0, 2) else HTTPStatus.BAD_REQUEST)

    def handle_validate(self, query: str) -> None:
        params = parse_qs(query)
        code = safe_project(params.get("project", [""])[0])
        args = ["_tools/validate_record.py", code, "--json"]
        rc, stdout, stderr = run_tool(args)
        payload = json.loads(stdout) if stdout.strip().startswith("{") else {"stdout": stdout}
        payload.update({"ok": rc == 0, "returncode": rc, "stderr": stderr})
        self.send_json(payload, HTTPStatus.OK if rc in (0, 2) else HTTPStatus.BAD_REQUEST)

    def handle_amap_check(self) -> None:
        args = ["_tools/amap_context.py", "--check", "--json"]
        rc, stdout, stderr = run_tool(args)
        payload = json.loads(stdout) if stdout.strip().startswith("{") else {"stdout": stdout}
        payload.update({"ok": rc == 0, "returncode": rc, "stderr": stderr})
        self.send_json(payload, HTTPStatus.OK if rc in (0, 2) else HTTPStatus.BAD_REQUEST)

    def handle_amap_jsapi_config(self) -> None:
        self.send_json(build_env_check_payload())

    def handle_env_check(self) -> None:
        self.send_json(build_env_check_payload())

    def handle_s2_basemap(self, query: str) -> None:
        params = parse_qs(query)
        code = safe_project(params.get("project", [""])[0])
        proj = project_dir(code)
        target = proj / SITE_BASEMAP_REL
        try:
            meta = generate_tdt_site_basemap(proj, target)
        except Exception as exc:
            load_env_file()
            configured = bool(os.environ.get("TIANDITU_KEY", "").strip())
            center_gcj02 = None
            tile_debug = None
            try:
                lng_gcj, lat_gcj = read_s2_center_gcj02(proj)
                center_gcj02 = f"{lng_gcj:.6f},{lat_gcj:.6f}"
                tile_debug = estimate_s2_site_tile_debug(lng_gcj, lat_gcj)
            except Exception:
                pass
            self.send_json(build_s2_basemap_error_payload(exc, configured, code, center_gcj02, tile_debug))
            return
        rel_path = str(SITE_BASEMAP_REL).replace("\\", "/")
        self.send_json(
            {
                "ok": True,
                "path": rel_path,
                "image_url": self.project_file_url(code, rel_path),
                **meta,
            }
        )

    def handle_amap_context(self) -> None:
        payload = self.read_json()
        code = safe_project(str(payload.get("project", "")))
        location = str(payload.get("location") or "").strip()
        address = str(payload.get("address") or "").strip()
        args = ["_tools/amap_context.py", code, "--json", "--write"]
        if location:
            args.extend(["--location", location])
        elif address:
            args.extend(["--address", address])
        rc, stdout, stderr = run_tool(args)
        result = json.loads(stdout) if stdout.strip().startswith("{") else {"stdout": stdout}
        result.update({"ok": rc == 0 and result.get("status") == "ok", "returncode": rc, "stderr": stderr})
        self.send_json(result, HTTPStatus.OK if rc == 0 else HTTPStatus.BAD_REQUEST)

    def handle_s1_auto_draft(self) -> None:
        payload = self.read_json()
        code = safe_project(str(payload.get("project", "")))
        map_mode = str(payload.get("map_mode", "standard")).strip()
        radius_m = str(payload.get("radius_m", "2000")).strip()
        radius_value = 1000 if radius_m == "1000" else 2000
        screenshot_data_url = str(payload.get("screenshot_data_url", "")).strip()
        client_capture_error = str(payload.get("client_capture_error", "")).strip()
        # Save screenshot if provided
        proj = project_dir(code)
        output_dir = proj / "05_output" / "location_analysis"
        output_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = None
        snapshot_meta: dict[str, object] = {}
        suffix = "1km" if radius_value == 1000 else "2km"
        png_path = output_dir / f"satellite_{suffix}.png"
        try:
            snapshot_meta = generate_tdt_location_snapshot(proj, radius_value, png_path)
            if client_capture_error:
                snapshot_meta["client_capture_error"] = client_capture_error
            if screenshot_data_url:
                snapshot_meta["client_capture_ignored"] = "server_tianditu_tiles used for fixed-size radius snapshot"
            screenshot_path = str(png_path.relative_to(proj)).replace("\\", "/")
        except Exception as server_exc:
            if not screenshot_data_url or not screenshot_data_url.startswith("data:image/png;base64,"):
                self.send_json(
                    {
                        "ok": False,
                        "error": f"天地图快照生成失败：{server_exc}",
                        "client_capture_error": client_capture_error,
                    },
                    HTTPStatus.BAD_REQUEST,
                )
                return
            import base64
            try:
                b64 = screenshot_data_url.split(",", 1)[1]
                png_path.write_bytes(base64.b64decode(b64))
            except Exception as exc:
                self.send_json(
                    {"ok": False, "error": f"天地图截图保存失败：{exc}"},
                    HTTPStatus.BAD_REQUEST,
                )
                return
            snapshot_meta = {
                "source": "client_canvas_fallback",
                "server_error": str(server_exc),
            }
            if client_capture_error:
                snapshot_meta["client_capture_error"] = client_capture_error
            screenshot_path = str(png_path.relative_to(proj)).replace("\\", "/")
        # Run analysis script
        args = ["_tools/s1_location_analysis.py", code, "--json", "--write"]
        if screenshot_path:
            args.extend(["--screenshot-path", screenshot_path])
        args.extend(["--map-mode", map_mode])
        args.extend(["--radius-m", str(radius_value)])
        rc, stdout, stderr = run_tool(args)
        result = json.loads(stdout) if stdout.strip().startswith("{") else {"stdout": stdout}
        result.update({"ok": rc == 0 and result.get("ok", False), "returncode": rc, "stderr": stderr})
        result["snapshot"] = snapshot_meta
        if result["ok"] and screenshot_path:
            try:
                result.update(sync_location_analysis_drawing(proj, code, screenshot_path, radius_value))
            except Exception as exc:
                result["ok"] = False
                result["error"] = f"区位分析底图同步到图纸工作台失败：{exc}"
        self.send_json(result, HTTPStatus.OK if result.get("ok") else HTTPStatus.BAD_REQUEST)

    def handle_spatial(self, query: str) -> None:
        params = parse_qs(query)
        code = safe_project(params.get("project", [""])[0])
        proj = project_dir(code)
        amap_dir = proj / "05_output" / "amap"
        context_path = amap_dir / "s1_map_context.json"
        control_path = amap_dir / "control_points.json"
        candidate_set_id_current = read_current_candidate_set_id(proj)
        payload: dict[str, object] = {
            "project": code,
            "amap_context_exists": context_path.exists(),
            "control_points_exists": control_path.exists(),
            "candidate_set_id_current": candidate_set_id_current,
            "candidate_set_id_at_save": None,
            "control_points_stale": False,
            "control_points": [],
        }
        if context_path.exists():
            try:
                context = json.loads(context_path.read_text(encoding="utf-8"))
                surroundings = extract_surroundings_from_s1(context)
                payload["amap_context"] = {
                    "status": context.get("status"),
                    "location": context.get("location"),
                    "address": (context.get("map_context") or {}).get("regeo", {}).get("formatted_address"),
                    "path": str(context_path.relative_to(proj)).replace("\\", "/"),
                }
                payload["surroundings"] = surroundings
            except json.JSONDecodeError as exc:
                payload["amap_context_error"] = str(exc)
        else:
            payload["surroundings"] = {"roads": [], "land_uses": [], "water_features": [], "notes": ["缺少 S1 高德上下文。"]}
        try:
            payload["redline"] = read_redline_overlay(proj, code)
        except Exception as exc:
            payload["redline"] = {
                "exists": False,
                "error": str(exc),
                "coordinate_reliability": {
                    "reliable": False,
                    "reason": str(exc),
                    "placement": "error",
                },
                "normalized_points": [],
            }
        payload["candidate_entrances"] = build_candidate_entrances(
            (payload.get("surroundings") or {}).get("roads") if isinstance(payload.get("surroundings"), dict) else [],
            payload.get("redline"),
        )
        site_context_path = proj / SITE_CONTEXT_REL
        payload["site_context_exists"] = site_context_path.exists()
        if site_context_path.exists():
            try:
                payload["site_context"] = json.loads(site_context_path.read_text(encoding="utf-8"))
                payload["site_context_path"] = str(site_context_path.relative_to(proj)).replace("\\", "/")
            except json.JSONDecodeError as exc:
                payload["site_context_error"] = str(exc)
        if control_path.exists():
            try:
                saved = json.loads(control_path.read_text(encoding="utf-8"))
                payload["control_points"] = saved.get("control_points", [])
                candidate_set_id_at_save = saved.get("candidate_set_id_at_save")
                payload["candidate_set_id_at_save"] = candidate_set_id_at_save
                payload["control_points_stale"] = bool(
                    candidate_set_id_current and candidate_set_id_at_save != candidate_set_id_current
                )
                payload["control_points_path"] = str(control_path.relative_to(proj)).replace("\\", "/")
            except json.JSONDecodeError as exc:
                payload["control_points_error"] = str(exc)
        alignment_path = amap_dir / "cad_alignment_report.json"
        if alignment_path.exists():
            try:
                payload["alignment_report"] = json.loads(alignment_path.read_text(encoding="utf-8"))
                payload["alignment_report_path"] = str(alignment_path.relative_to(proj)).replace("\\", "/")
            except json.JSONDecodeError as exc:
                payload["alignment_report_error"] = str(exc)
        self.send_json(payload)

    def handle_site_context_load(self, query: str) -> None:
        params = parse_qs(query)
        code = safe_project(params.get("project", [""])[0])
        proj = project_dir(code)
        target = proj / SITE_CONTEXT_REL
        if not target.exists():
            self.send_json(
                {
                    "ok": True,
                    "project": code,
                    "exists": False,
                    "path": str(SITE_CONTEXT_REL).replace("\\", "/"),
                }
            )
            return
        self.send_json(
            {
                "ok": True,
                "project": code,
                "exists": True,
                "path": str(SITE_CONTEXT_REL).replace("\\", "/"),
                "site_context": json.loads(target.read_text(encoding="utf-8")),
            }
        )

    def handle_site_context_save(self) -> None:
        payload = self.read_json()
        code = safe_project(str(payload.get("project", "")))
        proj = project_dir(code)
        cleaned = clean_site_context_payload(payload, code)
        target = proj / SITE_CONTEXT_REL
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(cleaned, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.send_json(
            {
                "ok": True,
                "project": code,
                "path": str(target.relative_to(proj)).replace("\\", "/"),
                "site_context": cleaned,
            }
        )

    def read_cad_preview_payload(self, proj: Path, code: str) -> dict[str, object]:
        preview_path = proj / "05_output" / "cad" / "site_preview.svg"
        candidate_path = proj / "05_output" / "cad" / "control_point_candidates.json"
        semantics_path = proj / CAD_SEMANTICS_REL
        payload: dict[str, object] = {
            "ok": True,
            "project": code,
            "exists": preview_path.exists() and candidate_path.exists(),
            "preview_svg": "05_output/cad/site_preview.svg" if preview_path.exists() else None,
            "candidate_json": "05_output/cad/control_point_candidates.json" if candidate_path.exists() else None,
            "candidate_semantics": str(CAD_SEMANTICS_REL).replace("\\", "/") if semantics_path.exists() else None,
            "candidates": [],
        }
        if candidate_path.exists():
            try:
                saved = json.loads(candidate_path.read_text(encoding="utf-8"))
                payload.update(saved)
                payload["ok"] = saved.get("status") == "ok"
                payload["exists"] = preview_path.exists()
                if semantics_path.exists():
                    semantics = json.loads(semantics_path.read_text(encoding="utf-8"))
                    payload["candidate_semantics"] = str(CAD_SEMANTICS_REL).replace("\\", "/")
                    payload["candidate_semantics_updated_at"] = semantics.get("updated_at")
                    payload["candidates"] = self.merge_candidate_semantics(
                        payload.get("candidates", []),
                        semantics.get("candidates", []),
                    )
                    payload["candidate_semantics_status"] = semantics.get("status")
                    payload["candidate_semantics_provider"] = semantics.get("provider")
                    payload["candidate_semantics_fallback_reason"] = semantics.get("fallback_reason")
                    payload["candidate_semantics_vision_image"] = semantics.get("vision_image")
                    payload["candidate_semantics_cad_image"] = semantics.get("cad_vision_image")
                    payload["candidate_semantics_location_images"] = semantics.get("location_images", [])
                    vision_result = semantics.get("vision_result") if isinstance(semantics.get("vision_result"), dict) else {}
                    payload["candidate_semantics_global_findings"] = vision_result.get("global_findings", [])
                    payload["candidate_semantics_needs_user_pick"] = vision_result.get("needs_user_pick", [])
            except json.JSONDecodeError as exc:
                payload["ok"] = False
                payload["error"] = str(exc)
        return payload

    def clean_candidate_semantics(self, items: object) -> list[dict[str, object]]:
        if not isinstance(items, list):
            raise ValueError("candidates 必须是数组")
        cleaned = []
        for index, raw in enumerate(items, start=1):
            if not isinstance(raw, dict):
                raise ValueError(f"候选点 {index} 格式错误")
            candidate_id = str(raw.get("id") or raw.get("label") or f"CAD-{index:02d}").strip()
            label = str(raw.get("label") or candidate_id).strip()
            feature_type = str(raw.get("feature_type") or "redline_corner").strip()
            feature_name = str(raw.get("feature_name") or "").strip()
            purpose = str(raw.get("purpose") or "registration").strip()
            confidence = str(raw.get("confidence") or "medium").strip()
            role_label = str(raw.get("role_label") or "").strip()
            reason = str(raw.get("reason") or "").strip()
            suggestion_source = str(raw.get("suggestion_source") or "").strip()
            note = str(raw.get("note") or "").strip()
            if feature_type not in CONTROL_FEATURE_TYPES:
                feature_type = "other"
            if purpose not in CONTROL_PURPOSES:
                purpose = "registration"
            if confidence not in CONTROL_CONFIDENCE:
                confidence = "medium"
            cleaned.append(
                {
                    "id": candidate_id,
                    "label": label,
                    "feature_type": feature_type,
                    "feature_name": feature_name or None,
                    "purpose": purpose,
                    "confidence": confidence,
                    "role_label": role_label or None,
                    "reason": reason or None,
                    "suggestion_source": suggestion_source or None,
                    "note": note or None,
                    "source": "uploader_ui",
                }
            )
        return cleaned

    def merge_candidate_semantics(self, candidates: object, semantics: object) -> list[dict[str, object]]:
        if not isinstance(candidates, list):
            return []
        semantic_rows = semantics if isinstance(semantics, list) else []
        by_key = {}
        for item in semantic_rows:
            if not isinstance(item, dict):
                continue
            for key in (item.get("id"), item.get("label")):
                if key:
                    by_key[str(key)] = item
        merged = []
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            row = dict(candidate)
            semantic = by_key.get(str(row.get("id"))) or by_key.get(str(row.get("label")))
            if semantic:
                for field in ("feature_type", "feature_name", "purpose", "confidence", "note", "role_label", "reason", "suggestion_source"):
                    if semantic.get(field) is not None:
                        row[field] = semantic.get(field)
            merged.append(row)
        return merged

    def handle_cad_preview(self, query: str, run: bool) -> None:
        if run:
            payload = self.read_json()
            code = safe_project(str(payload.get("project", "")))
        else:
            params = parse_qs(query)
            code = safe_project(params.get("project", [""])[0])
        proj = project_dir(code)
        if not proj.exists():
            raise ValueError("请先创建项目，再生成 CAD 预览")
        if not run:
            self.send_json(self.read_cad_preview_payload(proj, code))
            return

        probe_rc, probe_stdout, probe_stderr = run_tool(["_tools/dwg_probe.py", code, "--json", "--write"])
        probe = json.loads(probe_stdout) if probe_stdout.strip().startswith("{") else {"stdout": probe_stdout}
        if probe_rc not in (0, 2) or probe.get("status") not in {"ok", "partial"}:
            probe.update({"ok": False, "returncode": probe_rc, "stderr": probe_stderr})
            self.send_json(probe, HTTPStatus.BAD_REQUEST)
            return

        rc, stdout, stderr = run_tool(["_tools/cad_preview.py", code, "--json", "--write"])
        result = json.loads(stdout) if stdout.strip().startswith("{") else {"stdout": stdout}
        semantic_rc = 0
        semantic_stdout = ""
        semantic_stderr = ""
        semantic_payload: dict[str, object] = {}
        if rc == 0 and result.get("status") == "ok":
            semantic_rc, semantic_stdout, semantic_stderr = run_tool(
                ["_tools/cad_semantics.py", code, "--json", "--write", "--timeout", "60"]
            )
            semantic_payload = (
                json.loads(semantic_stdout)
                if semantic_stdout.strip().startswith("{")
                else {"stdout": semantic_stdout}
            )
        result.update(
            {
                "ok": rc == 0 and result.get("status") == "ok",
                "returncode": rc,
                "stderr": stderr,
                "dwg_probe_status": probe.get("status"),
                "cad_semantics": semantic_payload,
                "cad_semantics_returncode": semantic_rc,
                "cad_semantics_stderr": semantic_stderr,
            }
        )
        if rc == 0:
            result.update(self.read_cad_preview_payload(proj, code))
        self.send_json(result, HTTPStatus.OK if rc == 0 else HTTPStatus.BAD_REQUEST)

    def clean_candidate_set_id_at_save(self, payload: dict) -> str:
        if "candidate_set_id_at_save" not in payload:
            raise ValueError("请求体缺少 candidate_set_id_at_save，请先重新加载 CAD 预览后再保存控制点")
        value = str(payload.get("candidate_set_id_at_save") or "").strip()
        if not value:
            raise ValueError("candidate_set_id_at_save 不能为空，请先生成 CAD 预览")
        return value

    def stale_control_points_payload(self, proj: Path, candidate_set_id_at_save: str) -> dict[str, object] | None:
        candidate_set_id_current = read_current_candidate_set_id(proj)
        if not candidate_set_id_current:
            raise ValueError("当前项目还没有 candidate_set_id，请先生成 CAD 预览")
        if candidate_set_id_at_save != candidate_set_id_current:
            return {
                "status": "stale_control_points",
                "candidate_set_id_current": candidate_set_id_current,
                "candidate_set_id_at_save": candidate_set_id_at_save,
            }
        return None

    def clean_control_points(self, points: object, candidate_set_id_at_save: str | None = None) -> list[dict[str, object]]:
        if not candidate_set_id_at_save:
            raise ValueError("请求体缺少 candidate_set_id_at_save，请先重新加载 CAD 预览后再保存控制点")
        if not isinstance(points, list):
            raise ValueError("control_points 必须是数组")
        cleaned = []
        for index, raw in enumerate(points, start=1):
            if not isinstance(raw, dict):
                raise ValueError(f"控制点 {index} 格式错误")
            label = str(raw.get("label") or f"CP{index}").strip()
            cad_x = str(raw.get("cad_x") or "").strip()
            cad_y = str(raw.get("cad_y") or "").strip()
            amap_location = str(raw.get("amap_location") or "").strip()
            feature_type = str(raw.get("feature_type") or "redline_corner").strip()
            feature_name = str(raw.get("feature_name") or "").strip()
            purpose = str(raw.get("purpose") or "registration").strip()
            confidence = str(raw.get("confidence") or "medium").strip()
            note = str(raw.get("note") or "").strip()
            if feature_type not in CONTROL_FEATURE_TYPES:
                feature_type = "other"
            if purpose not in CONTROL_PURPOSES:
                purpose = "registration"
            if confidence not in CONTROL_CONFIDENCE:
                confidence = "medium"
            if not amap_location:
                raise ValueError(f"控制点 {label} 缺少高德坐标")
            parts = [part.strip() for part in amap_location.replace("，", ",").split(",")]
            if len(parts) != 2:
                raise ValueError(f"控制点 {label} 的高德坐标应为 经度,纬度")
            lng = float(parts[0])
            lat = float(parts[1])
            if not (-180 <= lng <= 180 and -90 <= lat <= 90):
                raise ValueError(f"控制点 {label} 的高德坐标超出范围")
            cad_point = None
            if cad_x or cad_y:
                if not cad_x or not cad_y:
                    raise ValueError(f"控制点 {label} 的 CAD X/Y 需同时填写")
                cad_point = {"x": float(cad_x), "y": float(cad_y)}
            cleaned.append(
                {
                    "label": label,
                    "cad_point": cad_point,
                    "amap_gcj02": [lng, lat],
                    "feature_type": feature_type,
                    "feature_name": feature_name or None,
                    "purpose": purpose,
                    "confidence": confidence,
                    "note": note or None,
                    "source": "uploader_ui",
                }
            )
        return cleaned

    def handle_alignment_check(self) -> None:
        payload = self.read_json()
        code = safe_project(str(payload.get("project", "")))
        proj = project_dir(code)
        candidate_set_id_at_save = self.clean_candidate_set_id_at_save(payload)
        stale = self.stale_control_points_payload(proj, candidate_set_id_at_save)
        if stale:
            self.send_json(stale, HTTPStatus.CONFLICT)
            return
        cleaned = self.clean_control_points(payload.get("control_points"), candidate_set_id_at_save)
        with tempfile.TemporaryDirectory(prefix="alignment_check_") as tmp:
            source = Path(tmp) / "control_points.json"
            source.write_text(
                json.dumps(
                    {
                        "candidate_set_id_at_save": candidate_set_id_at_save,
                        "control_points": cleaned,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            rc, stdout, stderr = run_tool(
                ["_tools/cad_align.py", code, "--json", "--input", str(source)]
            )
        result = json.loads(stdout) if stdout.strip().startswith("{") else {"stdout": stdout}
        result.update({"ok": rc == 0, "returncode": rc, "stderr": stderr, "preview": True})
        self.send_json(result, HTTPStatus.OK if rc == 0 else HTTPStatus.BAD_REQUEST)

    def handle_control_points(self) -> None:
        payload = self.read_json()
        code = safe_project(str(payload.get("project", "")))
        proj = project_dir(code)
        candidate_set_id_at_save = self.clean_candidate_set_id_at_save(payload)
        stale = self.stale_control_points_payload(proj, candidate_set_id_at_save)
        if stale:
            self.send_json(stale, HTTPStatus.CONFLICT)
            return
        cleaned = self.clean_control_points(payload.get("control_points"), candidate_set_id_at_save)
        out_dir = proj / "05_output" / "amap"
        out_dir.mkdir(parents=True, exist_ok=True)
        out = {
            "schema_version": "1.0",
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "project": code,
            "candidate_set_id_at_save": candidate_set_id_at_save,
            "coordinate_system": {
                "map": "GCJ-02 / AMap",
                "cad": "project CAD units; unit and CRS must be confirmed in S2",
            },
            "control_points": cleaned,
            "agent_note": (
                "Use these points only as user-provided correspondence evidence. "
                "S2 must still verify CAD handles/layers and transformation quality."
            ),
        }
        target = out_dir / "control_points.json"
        target.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        align_rc, align_stdout, align_stderr = run_tool(["_tools/cad_align.py", code, "--json", "--write"])
        alignment = json.loads(align_stdout) if align_stdout.strip().startswith("{") else {"stdout": align_stdout}
        alignment.update({"ok": align_rc == 0, "returncode": align_rc, "stderr": align_stderr})
        self.send_json(
            {
                "ok": True,
                "project": code,
                "count": len(cleaned),
                "path": str(target.relative_to(proj)).replace("\\", "/"),
                "control_points": cleaned,
                "alignment": alignment,
            }
        )

    def handle_control_points_archive(self, archive: bool) -> None:
        payload = self.read_json()
        code = safe_project(str(payload.get("project", "")))
        proj = project_dir(code)
        control_path = proj / CONTROL_POINTS_REL
        if not control_path.exists():
            raise ValueError("当前项目没有 control_points.json 可处理")

        rc, stdout, stderr = run_tool(["_tools/cad_align.py", code, "--migration-report", "--write", "--json"])
        migration = json.loads(stdout) if stdout.strip().startswith("{") else {"stdout": stdout}
        if rc != 0 or migration.get("status") != "ok":
            migration.update({"ok": False, "returncode": rc, "stderr": stderr})
            self.send_json(migration, HTTPStatus.BAD_REQUEST)
            return

        response: dict[str, object] = {
            "ok": True,
            "project": code,
            "archived": False,
            "migration_report": str(Path(migration.get("written_to", "")).resolve().relative_to(proj)).replace("\\", "/")
            if migration.get("written_to")
            else None,
            "migration": migration,
        }

        if archive:
            saved = json.loads(control_path.read_text(encoding="utf-8"))
            at_save = saved.get("candidate_set_id_at_save")
            suffix = short_candidate_set_id(at_save)
            out_dir = control_path.parent
            filename = f"control_points.legacy_{time.strftime('%Y-%m-%d')}_{suffix}.json"
            legacy_path = unique_path(out_dir, filename)
            control_path.replace(legacy_path)
            response.update(
                {
                    "archived": True,
                    "legacy_file": str(legacy_path.relative_to(proj)).replace("\\", "/"),
                }
            )

        self.send_json(response)

    def handle_cad_candidate_semantics(self) -> None:
        payload = self.read_json()
        code = safe_project(str(payload.get("project", "")))
        cleaned = self.clean_candidate_semantics(payload.get("candidates"))
        proj = project_dir(code)
        out_dir = (proj / CAD_SEMANTICS_REL).parent
        out_dir.mkdir(parents=True, exist_ok=True)
        out = {
            "schema_version": "1.0",
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "project": code,
            "candidates": cleaned,
            "agent_note": (
                "Semantic annotations for CAD-side candidate points. They do not replace "
                "AMap coordinates; use them to decide which candidate points are useful "
                "for road, bridge, entrance, water, or registration reasoning."
            ),
        }
        target = proj / CAD_SEMANTICS_REL
        target.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        self.send_json(
            {
                "ok": True,
                "project": code,
                "count": len(cleaned),
                "path": str(target.relative_to(proj)).replace("\\", "/"),
                "candidates": cleaned,
            }
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local architecture upload UI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    server = ThreadingHTTPServer((args.host, args.port), UploaderHandler)
    url = f"http://{args.host}:{args.port}"
    print(f"Architecture uploader running at {url}")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping uploader")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

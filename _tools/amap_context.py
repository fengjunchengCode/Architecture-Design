#!/usr/bin/env python3
"""Build S1 map context with AMap Web Service APIs.

This tool keeps external map facts deterministic and reproducible. It reads a
Web Service key from .env, resolves a GCJ-02/AMap location from user input or
record.md, queries reverse geocoding and nearby POIs, then writes a compact
machine-readable context for S1.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = REPO_ROOT / ".env"
OUTPUT_DIR = "05_output/amap"
RAW_NAME = "s1_amap_raw.json"
CONTEXT_NAME = "s1_map_context.json"
AMAP_BASE = "https://restapi.amap.com"
KEY_ENV_NAMES = ("AMAP_WEBSERVICE_KEY", "AMAP_WEB_SERVICE_KEY", "AMAP_KEY")
DEFAULT_REQUEST_DELAY_SEC = 0.45
QPS_RETRY_INFOS = {"CUQPS_HAS_EXCEEDED_THE_LIMIT", "DAILY_QUERY_OVER_LIMIT"}
PLACE_CATEGORIES = {
    "transport": "150000",
    "education_culture": "140000",
    "scenic_park": "110000",
    "government_public": "130000|200000",
    "commercial_life": "050000|060000|070000|120000",
    "medical_sports": "090000|080000",
}
DEFAULT_KEYWORDS = ("河", "桥", "公园", "公交站")


@dataclass
class AmapRequest:
    name: str
    endpoint: str
    params: dict[str, Any]
    status: str
    response: dict[str, Any] | None = None
    error: str | None = None


def load_env_file(path: Path = ENV_FILE) -> list[str]:
    """Load simple KEY=VALUE pairs from .env without overriding process env."""
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


def is_placeholder(value: str) -> bool:
    lowered = value.strip().lower()
    return (
        not lowered
        or lowered in {"xxx", "your_key", "your_amap_webservice_key", "<用户的key>", "none"}
        or lowered.startswith("your_")
        or lowered.startswith("填入")
    )


def get_amap_key() -> tuple[str | None, str | None]:
    for env_name in KEY_ENV_NAMES:
        value = os.environ.get(env_name, "").strip()
        if value and not is_placeholder(value):
            return value, env_name
    return None, None


def setup_hint(project_code: str | None = None) -> dict[str, Any]:
    command_project = project_code or "{code}"
    return {
        "env_file": str(ENV_FILE),
        "template": str(REPO_ROOT / ".env.example"),
        "required_env": list(KEY_ENV_NAMES),
        "recommended_env": "AMAP_WEBSERVICE_KEY",
        "check_command": "python _tools/amap_context.py --check",
        "run_with_location": (
            f'python _tools/amap_context.py {command_project} --location "lng,lat" --write'
        ),
        "agent_rule": (
            "If the AMap key or reliable location is missing, do not invent roads, POIs, "
            "water features, or entry relationships. Write pending questions instead."
        ),
    }


def resolve_project(project: str | None) -> Path:
    if not project:
        raise ValueError("project code is required unless --check is used")
    raw = Path(project)
    if raw.exists():
        return raw.resolve()
    return (REPO_ROOT / "projects" / project).resolve()


def read_record(project_dir: Path) -> dict[str, Any]:
    record_path = project_dir / "05_output" / "record.md"
    if not record_path.exists():
        return {}
    text = record_path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    data = yaml.safe_load(text[4:end]) or {}
    return data if isinstance(data, dict) else {}


def parse_location(value: str) -> tuple[float, float]:
    parts = [part.strip() for part in value.replace("，", ",").split(",")]
    if len(parts) != 2:
        raise ValueError(f"location must be 'lng,lat', got: {value}")
    lng = float(parts[0])
    lat = float(parts[1])
    if not (-180 <= lng <= 180 and -90 <= lat <= 90):
        raise ValueError(f"location out of range: {value}")
    return lng, lat


def fmt_location(location: tuple[float, float]) -> str:
    return f"{location[0]:.6f},{location[1]:.6f}"


def redact_params(params: dict[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in params.items():
        redacted[key] = "***" if key.lower() == "key" else value
    return redacted


def amap_get(
    name: str,
    endpoint: str,
    params: dict[str, Any],
    api_key: str,
    timeout: int,
    requests_log: list[AmapRequest],
) -> dict[str, Any]:
    query = dict(params)
    query["key"] = api_key
    query.setdefault("output", "JSON")
    url = f"{AMAP_BASE}{endpoint}?{urllib.parse.urlencode(query)}"
    safe_params = redact_params(query)
    retries = 3
    delay = float(os.environ.get("AMAP_REQUEST_DELAY", DEFAULT_REQUEST_DELAY_SEC))
    last_error: str | None = None
    for attempt in range(retries + 1):
        if delay > 0:
            time.sleep(delay if attempt == 0 else max(delay, 1.2 * attempt))
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Architecture-Design-amap-context/1.0"})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read().decode("utf-8", errors="replace")
            data = json.loads(body)
            info = str(data.get("info") or "")
            if str(data.get("status")) == "1":
                requests_log.append(AmapRequest(name, endpoint, safe_params, "ok", data))
                return data
            last_error = info or str(data.get("infocode") or "unknown error")
            if info in QPS_RETRY_INFOS and attempt < retries:
                continue
            requests_log.append(AmapRequest(name, endpoint, safe_params, "amap_api_error", data))
            return data
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = str(exc)
            if attempt < retries:
                continue
            requests_log.append(AmapRequest(name, endpoint, safe_params, "request_error", None, last_error))
            raise RuntimeError(f"{name} request failed: {last_error}") from exc
    requests_log.append(AmapRequest(name, endpoint, safe_params, "request_error", None, last_error))
    raise RuntimeError(f"{name} request failed: {last_error}")


def ensure_amap_success(name: str, data: dict[str, Any]) -> None:
    if str(data.get("status")) != "1":
        info = data.get("info") or data.get("infocode") or "unknown error"
        raise RuntimeError(f"{name} failed: {info}")


def geocode_address(
    address: str,
    city: str | None,
    api_key: str,
    timeout: int,
    requests_log: list[AmapRequest],
) -> dict[str, Any]:
    params: dict[str, Any] = {"address": address}
    if city:
        params["city"] = city
    data = amap_get("geocode", "/v3/geocode/geo", params, api_key, timeout, requests_log)
    ensure_amap_success("geocode", data)
    geocodes = data.get("geocodes") or []
    if not geocodes:
        raise RuntimeError(f"geocode returned no result for address: {address}")
    selected = geocodes[0]
    parse_location(str(selected.get("location", "")))
    return selected


def convert_to_amap(
    location: tuple[float, float],
    coordsys: str,
    api_key: str,
    timeout: int,
    requests_log: list[AmapRequest],
) -> tuple[float, float]:
    if coordsys in {"gcj02", "amap", "autonavi"}:
        return location
    api_coordsys = "gps" if coordsys == "wgs84" else coordsys
    data = amap_get(
        "coordinate_convert",
        "/v3/assistant/coordinate/convert",
        {"locations": fmt_location(location), "coordsys": api_coordsys},
        api_key,
        timeout,
        requests_log,
    )
    ensure_amap_success("coordinate_convert", data)
    locations = str(data.get("locations", "")).split(";")
    if not locations or not locations[0]:
        raise RuntimeError("coordinate_convert returned no converted location")
    return parse_location(locations[0])


def compact_poi(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": item.get("name"),
        "type": item.get("type"),
        "typecode": item.get("typecode"),
        "address": item.get("address"),
        "location": item.get("location"),
        "distance_m": item.get("distance"),
    }


def compact_road(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": item.get("name"),
        "direction": item.get("direction"),
        "distance_m": item.get("distance"),
        "location": item.get("location"),
    }


def compact_intersection(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "first_name": item.get("first_name"),
        "second_name": item.get("second_name"),
        "direction": item.get("direction"),
        "distance_m": item.get("distance"),
        "location": item.get("location"),
    }


def compact_aoi(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": item.get("name"),
        "type": item.get("type"),
        "adcode": item.get("adcode"),
        "location": item.get("location"),
        "distance_m": item.get("distance"),
    }


def regeo_context(
    location: tuple[float, float],
    radius: int,
    api_key: str,
    timeout: int,
    requests_log: list[AmapRequest],
    max_items: int,
) -> dict[str, Any]:
    data = amap_get(
        "regeo",
        "/v3/geocode/regeo",
        {
            "location": fmt_location(location),
            "radius": max(0, min(radius, 3000)),
            "extensions": "all",
            "roadlevel": 0,
        },
        api_key,
        timeout,
        requests_log,
    )
    ensure_amap_success("regeo", data)
    regeocode = data.get("regeocode") or {}
    roads = regeocode.get("roads") or []
    intersections = regeocode.get("roadinters") or []
    pois = regeocode.get("pois") or []
    aois = regeocode.get("aois") or []
    return {
        "formatted_address": regeocode.get("formatted_address"),
        "address_component": regeocode.get("addressComponent"),
        "roads": [compact_road(item) for item in roads[:max_items]],
        "road_intersections": [compact_intersection(item) for item in intersections[:max_items]],
        "nearby_pois": [compact_poi(item) for item in pois[:max_items]],
        "aois": [compact_aoi(item) for item in aois[:max_items]],
    }


def place_around(
    name: str,
    location: tuple[float, float],
    radius: int,
    api_key: str,
    timeout: int,
    requests_log: list[AmapRequest],
    max_items: int,
    *,
    types: str | None = None,
    keywords: str | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "location": fmt_location(location),
        "radius": max(0, min(radius, 50000)),
        "offset": max(1, min(max_items, 25)),
        "page": 1,
        "extensions": "base",
        "sortrule": "distance",
    }
    if types:
        params["types"] = types
    if keywords:
        params["keywords"] = keywords
    data = amap_get(name, "/v3/place/around", params, api_key, timeout, requests_log)
    if str(data.get("status")) != "1":
        return {
            "status": "amap_api_error",
            "error": data.get("info") or data.get("infocode") or "unknown error",
            "count": 0,
            "items": [],
        }
    pois = data.get("pois") or []
    return {
        "status": "ok",
        "count": data.get("count"),
        "items": [compact_poi(item) for item in pois[:max_items]],
    }


def static_map_url(location: tuple[float, float]) -> str:
    params = {
        "location": fmt_location(location),
        "zoom": 16,
        "size": "750*500",
        "scale": 2,
        "markers": f"mid,0xFF0000,A:{fmt_location(location)}",
        "key": "<AMAP_WEBSERVICE_KEY>",
    }
    return f"{AMAP_BASE}/v3/staticmap?{urllib.parse.urlencode(params)}"


def location_from_record(record: dict[str, Any]) -> tuple[tuple[float, float] | None, str | None, str | None]:
    site = record.get("site") if isinstance(record.get("site"), dict) else {}
    coords = site.get("coords")
    if isinstance(coords, (list, tuple)) and len(coords) == 2:
        return (float(coords[0]), float(coords[1])), "record.site.coords", None
    address = site.get("address")
    if isinstance(address, str) and address.strip():
        return None, "record.site.address", address.strip()
    return None, None, None


def choose_location(
    args: argparse.Namespace,
    record: dict[str, Any],
    api_key: str,
    requests_log: list[AmapRequest],
) -> dict[str, Any]:
    if args.location:
        raw_location = parse_location(args.location)
        amap_location = convert_to_amap(raw_location, args.location_crs, api_key, args.timeout, requests_log)
        return {
            "amap_gcj02": fmt_location(amap_location),
            "source": "argument.location",
            "source_crs": args.location_crs,
            "confidence": "high",
            "raw": {"location": args.location},
        }

    address = args.address
    address_source = "argument.address" if address else None
    if not address:
        _, record_source, record_address = location_from_record(record)
        if record_address:
            address = record_address
            address_source = record_source
    if address:
        geocode = geocode_address(address, args.city, api_key, args.timeout, requests_log)
        amap_location = parse_location(str(geocode["location"]))
        level = str(geocode.get("level") or "")
        confidence = "high" if level in {"门牌号", "兴趣点", "道路"} else "medium"
        return {
            "amap_gcj02": fmt_location(amap_location),
            "source": address_source,
            "source_crs": "address_geocode",
            "confidence": confidence,
            "raw": {"address": address, "city": args.city, "geocode": geocode},
        }

    record_location, record_source, _ = location_from_record(record)
    if record_location:
        amap_location = convert_to_amap(
            record_location,
            args.record_coords_crs,
            api_key,
            args.timeout,
            requests_log,
        )
        return {
            "amap_gcj02": fmt_location(amap_location),
            "source": record_source,
            "source_crs": args.record_coords_crs,
            "confidence": "medium",
            "raw": {"record_coords": list(record_location)},
        }

    raise RuntimeError("no address or location input found")


def names(items: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for item in items:
        value = item.get("name") or item.get("first_name")
        if value and value not in out:
            out.append(str(value))
    return out


def build_context(args: argparse.Namespace, project_dir: Path, api_key: str, key_env: str | None) -> dict[str, Any]:
    record = read_record(project_dir)
    requests_log: list[AmapRequest] = []
    location = choose_location(args, record, api_key, requests_log)
    amap_location = parse_location(location["amap_gcj02"])
    regeo = regeo_context(amap_location, args.regeo_radius, api_key, args.timeout, requests_log, args.max_items)

    poi_500m: dict[str, Any] = {}
    poi_1000m: dict[str, Any] = {}
    if not args.skip_poi:
        for label, types in PLACE_CATEGORIES.items():
            poi_500m[label] = place_around(
                f"place_around_500m_{label}",
                amap_location,
                500,
                api_key,
                args.timeout,
                requests_log,
                args.max_items,
                types=types,
            )
            poi_1000m[label] = place_around(
                f"place_around_1000m_{label}",
                amap_location,
                1000,
                api_key,
                args.timeout,
                requests_log,
                args.max_items,
                types=types,
            )

    keywords = args.keyword if args.keyword is not None else list(DEFAULT_KEYWORDS)
    keyword_context: dict[str, Any] = {}
    if not args.skip_keywords:
        for keyword in keywords:
            keyword_context[keyword] = place_around(
                f"place_around_keyword_{keyword}",
                amap_location,
                args.keyword_radius,
                api_key,
                args.timeout,
                requests_log,
                args.max_items,
                keywords=keyword,
            )

    road_names = names(regeo["roads"]) + [
        " / ".join(filter(None, [item.get("first_name"), item.get("second_name")]))
        for item in regeo["road_intersections"]
    ]
    road_names = [name for i, name in enumerate(road_names) if name and name not in road_names[:i]]
    water_or_landscape = []
    for keyword, payload in keyword_context.items():
        water_or_landscape.extend(names(payload.get("items", [])))
    water_or_landscape = [
        name for i, name in enumerate(water_or_landscape) if name and name not in water_or_landscape[:i]
    ]

    context = {
        "schema_version": "1.0",
        "status": "ok",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "project_code": project_dir.name,
        "provider": {
            "name": "amap_webservice",
            "configured": True,
            "key_env": key_env,
            "key": "***",
        },
        "location": location,
        "map_context": {
            "coordinate_system": "GCJ-02 / AMap",
            "regeo": regeo,
            "poi_500m": poi_500m,
            "poi_1000m": poi_1000m,
            "keyword_context": keyword_context,
        },
        "static_map": {
            "url_template": static_map_url(amap_location),
            "note": "Replace <AMAP_WEBSERVICE_KEY> locally if a static preview image is needed.",
        },
        "s1_external_context_seed": {
            "registration_state": "map_located",
            "coordinate_evidence": {
                "address": regeo.get("formatted_address"),
                "amap_gcj02": location["amap_gcj02"],
                "wgs84_for_record": None,
                "source": location["source"],
                "confidence": location["confidence"],
            },
            "location_evidence": [
                f"AMap reverse geocode: {regeo.get('formatted_address')}",
                f"AMap coordinate source: {location['source']} ({location['source_crs']})",
            ],
            "amap_context": {
                "roads": road_names,
                "water": water_or_landscape,
                "poi_500m": {
                    label: names(payload.get("items", []))
                    for label, payload in poi_500m.items()
                },
                "poi_1000m": {
                    label: names(payload.get("items", []))
                    for label, payload in poi_1000m.items()
                },
                "transit_or_routes": names(poi_500m.get("transport", {}).get("items", [])),
            },
            "external_features": {
                "primary_roads": road_names,
                "secondary_roads": [],
                "barriers": [],
                "landscape_or_culture_nodes": water_or_landscape
                + names(poi_500m.get("education_culture", {}).get("items", []))
                + names(poi_500m.get("scenic_park", {}).get("items", [])),
            },
            "approach_vectors": [],
            "entrance_judgment": {
                "level": "candidate",
                "main_entrance": None,
                "secondary_entrance": None,
                "reason": "Only map location is available; CAD edge binding requires control points.",
            },
            "s2_use": {
                "can_bind_to_cad_edges": False,
                "required_control_points": [
                    "2-3 common points between AMap and CAD, such as bridge ends, road intersections, or redline corners",
                ],
                "notes": [
                    "AMap coordinates are GCJ-02 and cannot be directly overlaid on unknown CAD engineering coordinates.",
                ],
            },
        },
    }

    raw = {
        "schema_version": "1.0",
        "created_at": context["created_at"],
        "project_code": project_dir.name,
        "requests": [asdict(item) for item in requests_log],
    }
    context["_raw"] = raw
    return context


def not_configured_payload(project_dir: Path | None, loaded_env: list[str]) -> dict[str, Any]:
    project_code = project_dir.name if project_dir else None
    return {
        "schema_version": "1.0",
        "status": "amap_not_configured",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "project_code": project_code,
        "env_loaded": loaded_env,
        "provider": {
            "name": "amap_webservice",
            "configured": False,
            "checked_env": list(KEY_ENV_NAMES),
        },
        "setup": setup_hint(project_code),
        "s1_external_context_seed": {
            "registration_state": "no_location",
            "coordinate_evidence": {
                "address": None,
                "amap_gcj02": None,
                "wgs84_for_record": None,
                "source": None,
                "confidence": "low",
            },
            "amap_context": {
                "roads": [],
                "water": [],
                "poi_500m": [],
                "poi_1000m": [],
                "transit_or_routes": [],
            },
            "s2_use": {
                "can_bind_to_cad_edges": False,
                "required_control_points": [],
                "notes": ["AMAP_WEBSERVICE_KEY is not configured."],
            },
        },
    }


def no_location_payload(project_dir: Path, loaded_env: list[str], error: str) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "status": "no_location_input",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "project_code": project_dir.name,
        "env_loaded": loaded_env,
        "error": error,
        "setup": setup_hint(project_dir.name),
        "pending_questions": [
            {
                "field": "site.coords",
                "question": "请提供地块中心点的高德坐标，或高德地图位置分享链接。",
            },
            {
                "field": None,
                "question": "如需 CAD 与高德地图精确套合，请提供 2-3 个地图点与 CAD 点的对应关系。",
            },
        ],
        "s1_external_context_seed": {
            "registration_state": "no_location",
            "coordinate_evidence": {
                "address": None,
                "amap_gcj02": None,
                "wgs84_for_record": None,
                "source": None,
                "confidence": "low",
            },
            "amap_context": {
                "roads": [],
                "water": [],
                "poi_500m": [],
                "poi_1000m": [],
                "transit_or_routes": [],
            },
            "s2_use": {
                "can_bind_to_cad_edges": False,
                "required_control_points": [],
                "notes": [error],
            },
        },
    }


def write_outputs(project_dir: Path, payload: dict[str, Any]) -> None:
    out_dir = project_dir / OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    raw = payload.pop("_raw", None)
    (out_dir / CONTEXT_NAME).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if raw is not None:
        (out_dir / RAW_NAME).write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    index = {
        "schema_version": "1.0",
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "results": [
            {
                "path": f"{OUTPUT_DIR}/{CONTEXT_NAME}",
                "status": payload.get("status"),
            },
        ],
    }
    if raw is not None:
        index["results"].append({"path": f"{OUTPUT_DIR}/{RAW_NAME}", "status": "raw"})
    (out_dir / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    payload["written_to"] = str(out_dir)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build S1 AMap context for a project")
    parser.add_argument("project", nargs="?", help="Project code or project directory")
    parser.add_argument("--location", help="AMap/GCJ-02 location, formatted as lng,lat")
    parser.add_argument(
        "--location-crs",
        choices=("gcj02", "amap", "autonavi", "wgs84", "gps", "baidu", "mapbar"),
        default="gcj02",
        help="Coordinate system for --location. Default is gcj02/amap.",
    )
    parser.add_argument("--address", help="Address to geocode when no --location is provided")
    parser.add_argument("--city", help="Optional city/adcode for address geocoding")
    parser.add_argument(
        "--record-coords-crs",
        choices=("wgs84", "gps", "gcj02", "amap", "autonavi", "baidu", "mapbar"),
        default="wgs84",
        help="Coordinate system for record.md site.coords. Schema default is WGS84.",
    )
    parser.add_argument("--regeo-radius", type=int, default=1000, help="Reverse geocode nearby radius, max 3000m")
    parser.add_argument("--keyword-radius", type=int, default=1000, help="Keyword around-search radius")
    parser.add_argument("--keyword", action="append", help="Extra keyword around-search. Repeatable.")
    parser.add_argument("--skip-poi", action="store_true", help="Skip grouped 500m/1000m POI searches")
    parser.add_argument("--skip-keywords", action="store_true", help="Skip keyword searches for water/bridges/parks")
    parser.add_argument("--max-items", type=int, default=8, help="Max items per category, capped by AMap offset limit")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout seconds")
    parser.add_argument("--write", action="store_true", help="Write 05_output/amap/s1_map_context.json")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    parser.add_argument("--require-config", action="store_true", help="Exit 2 if AMap key is not configured")
    parser.add_argument("--check", action="store_true", help="Check AMap key configuration and exit")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    loaded_env = load_env_file()
    api_key, key_env = get_amap_key()

    if args.check:
        payload = {
            "env_loaded": loaded_env,
            "provider": {
                "name": "amap_webservice",
                "configured": api_key is not None,
                "key_env": key_env,
                "checked_env": list(KEY_ENV_NAMES),
            },
            "setup": None if api_key else setup_hint(args.project),
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print("== amap_context :: check ==")
            print(f"  .env: {ENV_FILE} ({'loaded' if loaded_env else 'not found or no new keys'})")
            print(f"  configured: {api_key is not None}")
            if key_env:
                print(f"  key env: {key_env}")
            else:
                print(f"  setup: add AMAP_WEBSERVICE_KEY to {ENV_FILE}")
        return 0 if api_key or not args.require_config else 2

    try:
        project_dir = resolve_project(args.project)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3
    if not project_dir.exists():
        print(f"ERROR: project not found: {project_dir}", file=sys.stderr)
        return 3

    if not api_key:
        payload = not_configured_payload(project_dir, loaded_env)
        if args.write:
            write_outputs(project_dir, payload)
    else:
        try:
            payload = build_context(args, project_dir, api_key, key_env)
        except RuntimeError as exc:
            message = str(exc)
            if "no address or location input" in message:
                payload = no_location_payload(project_dir, loaded_env, message)
            else:
                payload = {
                    "schema_version": "1.0",
                    "status": "amap_api_error",
                    "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    "project_code": project_dir.name,
                    "error": message,
                    "setup": setup_hint(project_dir.name),
                }
        if args.write:
            write_outputs(project_dir, payload)

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"== amap_context :: {project_dir}")
        print(f"  status: {payload.get('status')}")
        if payload.get("status") == "ok":
            location = payload["location"]
            print(f"  location: {location['amap_gcj02']} ({location['source']}, {location['confidence']})")
            print(f"  address: {payload['map_context']['regeo'].get('formatted_address')}")
        elif payload.get("status") == "amap_not_configured":
            print(f"  setup: add AMAP_WEBSERVICE_KEY to {ENV_FILE}")
        elif payload.get("error"):
            print(f"  error: {payload['error']}")
        if payload.get("written_to"):
            print(f"  written: {payload['written_to']}")

    if args.require_config and not api_key:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

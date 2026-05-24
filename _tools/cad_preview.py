#!/usr/bin/env python3
"""Generate an SVG CAD preview and candidate CAD control points for S2."""
from __future__ import annotations

import argparse
import hashlib
import html
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
REPORT_NAME = "dwg_probe.json"
PREVIEW_NAME = "site_preview.svg"
CANDIDATES_NAME = "control_point_candidates.json"

LAYER_COLORS = {
    "0": "#b91c1c",
    "TK": "#374151",
    "GXYZ": "#1f6f5b",
    "JMD": "#8a5a1f",
    "DLSS": "#2563eb",
    "SXSS": "#0f766e",
    "DMTZ": "#7c3aed",
    "ASSIST": "#9ca3af",
}

SEMANTIC_LAYER_HINTS = {
    "DLSS": {
        "feature_type": "road_edge",
        "purpose": "road_binding",
        "role_label": "道路设施候选",
        "note": "DLSS 图层候选，可能是道路/硬质设施边线；请在高德中确认对应地物。",
    },
    "SXSS": {
        "feature_type": "water_edge",
        "purpose": "water_binding",
        "role_label": "水系岸线候选",
        "note": "SXSS 图层候选，可能是水系/沟渠/水岸设施；请在高德中确认对应地物。",
    },
    "DLDW": {
        "feature_type": "visible_landmark",
        "purpose": "reference_only",
        "role_label": "固定地物候选",
        "note": "DLDW 图层候选，可能是独立地物；可作为辅助参照点。",
    },
    "JMD": {
        "feature_type": "building_corner",
        "purpose": "reference_only",
        "role_label": "建筑/构筑物候选",
        "note": "JMD 图层候选，可能是建筑或构筑物边角；可作为辅助参照点。",
    },
}


def resolve_project(code_or_path: str) -> Path:
    direct = Path(code_or_path).expanduser()
    if direct.exists():
        return direct.resolve()
    return (PROJECTS_DIR / code_or_path).resolve()


def rel_to_project(path: Path, project_dir: Path) -> str:
    try:
        return path.relative_to(project_dir).as_posix()
    except ValueError:
        return str(path)


def point2(point: Any) -> tuple[float, float]:
    return (float(point[0]), float(point[1]))


def distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def shoelace_area(points: list[tuple[float, float]]) -> float:
    if len(points) < 3:
        return 0.0
    area = 0.0
    for index, (x1, y1) in enumerate(points):
        x2, y2 = points[(index + 1) % len(points)]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


def bbox(points: list[tuple[float, float]]) -> dict[str, list[float]]:
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return {
        "min": [min(xs), min(ys)],
        "max": [max(xs), max(ys)],
        "size": [max(xs) - min(xs), max(ys) - min(ys)],
    }


def clean_ring(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if len(points) > 1 and distance(points[0], points[-1]) < 1e-8:
        return points[:-1]
    return points


def read_probe(project_dir: Path) -> dict[str, Any]:
    path = project_dir / "05_output" / REPORT_NAME
    if not path.exists():
        raise FileNotFoundError("05_output/dwg_probe.json 不存在，请先运行 dwg_probe.py")
    return json.loads(path.read_text(encoding="utf-8"))


def choose_dxf(project_dir: Path, report: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    for item in report.get("files", []):
        parse = item.get("parse") or {}
        if parse.get("status") != "ok":
            continue
        dxf_rel = (item.get("conversion") or {}).get("dxf_path")
        if not dxf_rel and str(item.get("ext", "")).lower() == ".dxf":
            dxf_rel = item.get("path")
        if not dxf_rel:
            continue
        dxf_path = (project_dir / dxf_rel).resolve()
        if dxf_path.exists():
            return dxf_path, item
    raise FileNotFoundError("没有可解析的 DXF。请检查 dwg_probe.py 的转换结果。")


def layer_visible(doc: Any, layer_name: str) -> bool:
    try:
        layer = doc.layers.get(layer_name)
        return not layer.is_off() and not layer.is_frozen()
    except Exception:
        return True


def entity_points(entity: Any) -> tuple[list[tuple[float, float]], bool] | None:
    dxftype = entity.dxftype()
    if dxftype == "LINE":
        return [point2(entity.dxf.start), point2(entity.dxf.end)], False
    if dxftype == "LWPOLYLINE":
        return [(float(item[0]), float(item[1])) for item in entity.get_points("xy")], bool(entity.closed)
    if dxftype == "POLYLINE" and entity.is_2d_polyline:
        return [point2(vertex.dxf.location) for vertex in entity.vertices], bool(entity.is_closed)
    return None


def collect_geometry(doc: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[tuple[float, float]]]:
    drawables: list[dict[str, Any]] = []
    closed: list[dict[str, Any]] = []
    all_points: list[tuple[float, float]] = []
    for entity in doc.modelspace():
        if not layer_visible(doc, entity.dxf.layer):
            continue
        parsed = entity_points(entity)
        if not parsed:
            continue
        points, is_closed = parsed
        if len(points) < 2:
            continue
        all_points.extend(points)
        item = {
            "type": entity.dxftype(),
            "layer": entity.dxf.layer,
            "handle": entity.dxf.handle,
            "points": points,
            "closed": is_closed,
        }
        drawables.append(item)
        if is_closed and len(points) >= 3:
            ring = clean_ring(points)
            metrics = bbox(ring)
            closed.append(
                {
                    **item,
                    "points": ring,
                    "area_xy": shoelace_area(ring),
                    "bbox_xy": metrics,
                    "vertex_count": len(ring),
                }
            )
    return drawables, closed, all_points


def choose_boundary(closed: list[dict[str, Any]], all_points: list[tuple[float, float]]) -> dict[str, Any] | None:
    if not closed:
        return None
    drawing_bbox = bbox(all_points)
    drawing_area = max(drawing_bbox["size"][0] * drawing_bbox["size"][1], 1.0)
    useful = [
        item
        for item in closed
        if item["area_xy"] > 500 and item["vertex_count"] >= 5 and item["area_xy"] < drawing_area * 0.35
    ]
    if useful:
        return sorted(useful, key=lambda item: item["area_xy"], reverse=True)[0]
    useful = [item for item in closed if item["area_xy"] > 500]
    return sorted(useful or closed, key=lambda item: item["area_xy"], reverse=True)[0]


def angle_score(points: list[tuple[float, float]], index: int) -> float:
    prev_point = points[index - 1]
    point = points[index]
    next_point = points[(index + 1) % len(points)]
    a = (prev_point[0] - point[0], prev_point[1] - point[1])
    b = (next_point[0] - point[0], next_point[1] - point[1])
    la = math.hypot(*a)
    lb = math.hypot(*b)
    if la < 1e-8 or lb < 1e-8:
        return 0.0
    cos_value = max(-1.0, min(1.0, (a[0] * b[0] + a[1] * b[1]) / (la * lb)))
    angle = math.acos(cos_value)
    return abs(math.pi - angle)


def candidate_vertices(boundary: dict[str, Any] | None, limit: int = 6) -> list[dict[str, Any]]:
    if not boundary:
        return []
    points = boundary["points"]
    metrics = boundary["bbox_xy"]
    diag = math.hypot(metrics["size"][0], metrics["size"][1])
    min_gap = diag * 0.08

    extreme_indices = {
        min(range(len(points)), key=lambda i: points[i][0]): "west edge vertex",
        max(range(len(points)), key=lambda i: points[i][0]): "east edge vertex",
        min(range(len(points)), key=lambda i: points[i][1]): "south edge vertex",
        max(range(len(points)), key=lambda i: points[i][1]): "north edge vertex",
    }
    ranked = [(idx, 10.0, note) for idx, note in extreme_indices.items()]
    ranked.extend(
        (idx, angle_score(points, idx), "redline corner candidate")
        for idx in range(len(points))
        if idx not in extreme_indices
    )
    ranked.sort(key=lambda item: item[1], reverse=True)

    selected: list[tuple[int, str]] = []
    for idx, _, note in ranked:
        point = points[idx]
        if any(distance(point, points[existing]) < min_gap for existing, _ in selected):
            continue
        selected.append((idx, note))
        if len(selected) >= limit:
            break

    centroid = (
        sum(point[0] for point in points) / len(points),
        sum(point[1] for point in points) / len(points),
    )
    selected.sort(key=lambda item: math.atan2(points[item[0]][1] - centroid[1], points[item[0]][0] - centroid[0]))
    candidates: list[dict[str, Any]] = []
    for number, (idx, note) in enumerate(selected, start=1):
        point = points[idx]
        candidates.append(
            {
                "id": f"CAD-{number:02d}",
                "label": f"CAD-{number:02d}",
                "kind": "boundary_vertex",
                "feature_type": "redline_corner",
                "purpose": "registration",
                "feature_name": f"redline handle {boundary['handle']} vertex {idx}",
                "cad_point": {"x": point[0], "y": point[1]},
                "source_handle": boundary["handle"],
                "source_layer": boundary["layer"],
                "source_vertex_index": idx,
                "confidence": "candidate",
                "note": f"{note}; pick the matching visible map feature in AMap if it can be identified.",
            }
        )
    return candidates


def polyline_length(points: list[tuple[float, float]]) -> float:
    return sum(distance(points[index - 1], points[index]) for index in range(1, len(points)))


def semantic_feature_candidates(
    drawables: list[dict[str, Any]],
    boundary: dict[str, Any] | None,
    existing: list[dict[str, Any]],
    limit: int = 3,
) -> list[dict[str, Any]]:
    if not boundary:
        return []
    metrics = boundary["bbox_xy"]
    diag = math.hypot(metrics["size"][0], metrics["size"][1])
    min_gap = max(diag * 0.065, 8.0)
    min_length = max(diag * 0.025, 5.0)
    existing_points = [
        (item["cad_point"]["x"], item["cad_point"]["y"])
        for item in existing
        if item.get("cad_point")
    ]

    candidates: list[dict[str, Any]] = []

    def too_close(point: tuple[float, float]) -> bool:
        return any(distance(point, other) < min_gap for other in existing_points)

    def add_point(point: tuple[float, float], layer: str, handle: str) -> bool:
        if too_close(point):
            return False
        hint = SEMANTIC_LAYER_HINTS[layer]
        number = len(existing) + len(candidates) + 1
        candidates.append(
            {
                "id": f"CAD-{number:02d}",
                "label": f"CAD-{number:02d}",
                "kind": f"{hint['feature_type']}_candidate",
                "feature_type": hint["feature_type"],
                "purpose": hint["purpose"],
                "feature_name": f"{layer} handle {handle}",
                "role_label": hint["role_label"],
                "cad_point": {"x": point[0], "y": point[1]},
                "source_handle": handle,
                "source_layer": layer,
                "confidence": "candidate",
                "note": hint["note"],
            }
        )
        existing_points.append(point)
        return True

    boundary_bbox = boundary["bbox_xy"]
    min_x, min_y = boundary_bbox["min"]
    max_x, max_y = boundary_bbox["max"]
    pad = diag * 0.22
    layer_order = ["DLSS", "SXSS"]
    layer_priority = {layer: index for index, layer in enumerate(layer_order)}

    def distance_to_boundary_bbox(point: tuple[float, float]) -> float:
        dx = max(min_x - point[0], 0.0, point[0] - max_x)
        dy = max(min_y - point[1], 0.0, point[1] - max_y)
        return math.hypot(dx, dy)

    ranked_points: list[tuple[float, tuple[float, float], str, str]] = []
    for layer in layer_order:
        layer_items = [
            item
            for item in drawables
            if str(item.get("layer", "")).upper() == layer
            and len(item.get("points", [])) >= 2
            and polyline_length(item["points"]) >= min_length
        ]
        for item in layer_items:
            points = item["points"]
            length = polyline_length(points)
            useful_points = [points[0], points[-1], points[len(points) // 2]]
            for offset, point in enumerate(useful_points):
                outside = distance_to_boundary_bbox(point)
                if outside > pad:
                    continue
                score = layer_priority[layer] * 100000 + outside * 100 - length * 0.01 + offset
                ranked_points.append((score, point, layer, item["handle"]))

    used_handles: set[str] = set()
    for _, point, layer, handle in sorted(ranked_points, key=lambda item: item[0]):
        if handle in used_handles:
            continue
        if add_point(point, layer, handle):
            used_handles.add(handle)
        if len(candidates) >= limit:
            return candidates
    return candidates


def make_projector(points: list[tuple[float, float]], width: int, height: int, margin: int):
    metrics = bbox(points)
    min_x, min_y = metrics["min"]
    max_x, max_y = metrics["max"]
    span_x = max(max_x - min_x, 1.0)
    span_y = max(max_y - min_y, 1.0)
    scale = min((width - margin * 2) / span_x, (height - margin * 2) / span_y)

    def project(point: tuple[float, float]) -> tuple[float, float]:
        x = margin + (point[0] - min_x) * scale
        y = height - margin - (point[1] - min_y) * scale
        return x, y

    return project, metrics


def svg_poly(points: list[tuple[float, float]], project: Any) -> str:
    return " ".join(f"{project(point)[0]:.2f},{project(point)[1]:.2f}" for point in points)


def render_svg(
    project_code: str,
    source_rel: str,
    drawables: list[dict[str, Any]],
    boundary: dict[str, Any] | None,
    candidates: list[dict[str, Any]],
    all_points: list[tuple[float, float]],
) -> str:
    width = 1200
    height = 840
    margin = 54
    project, drawing_bbox = make_projector(all_points, width, height, margin)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fbfaf7"/>',
        f'<text x="24" y="30" font-family="Arial, sans-serif" font-size="16" fill="#111827">{html.escape(project_code)} S2 CAD preview</text>',
        f'<text x="24" y="52" font-family="Arial, sans-serif" font-size="12" fill="#6b7280">source: {html.escape(source_rel)}; CAD orientation, not north-up unless source drawing is north-up</text>',
        '<g fill="none" stroke-linecap="round" stroke-linejoin="round">',
    ]
    for item in drawables:
        color = LAYER_COLORS.get(str(item["layer"]).upper(), "#6b7280")
        points = item["points"]
        opacity = "0.82" if item["layer"] != "ASSIST" else "0.42"
        if len(points) == 2 and not item["closed"]:
            x1, y1 = project(points[0])
            x2, y2 = project(points[1])
            parts.append(
                f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{color}" stroke-width="1" opacity="{opacity}"/>'
            )
        else:
            close = " polygon" if item["closed"] else " polyline"
            parts.append(
                f'<polyline points="{svg_poly(points, project)}" stroke="{color}" stroke-width="1" opacity="{opacity}" data-type="{close.strip()}"/>'
            )
    parts.append("</g>")

    if boundary:
        points = boundary["points"]
        parts.append(
            f'<polygon points="{svg_poly(points, project)}" fill="#fee2e2" fill-opacity="0.38" stroke="#b91c1c" stroke-width="3"/>'
        )
        label = (
            f'candidate redline handle {boundary["handle"]}; layer {boundary["layer"]}; '
            f'area {boundary["area_xy"]:.2f} raw units²'
        )
        parts.append(
            f'<text x="24" y="{height - 26}" font-family="Arial, sans-serif" font-size="13" fill="#7f1d1d">{html.escape(label)}</text>'
        )

    for item in candidates:
        point = (item["cad_point"]["x"], item["cad_point"]["y"])
        x, y = project(point)
        parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="8" fill="#f97316" stroke="#7c2d12" stroke-width="2"/>')
        parts.append(
            f'<text x="{x + 11:.2f}" y="{y - 9:.2f}" font-family="Arial, sans-serif" font-size="13" font-weight="700" fill="#7c2d12">{html.escape(item["id"])}</text>'
        )

    size = drawing_bbox["size"]
    parts.append(
        f'<text x="24" y="{height - 8}" font-family="Arial, sans-serif" font-size="12" fill="#6b7280">drawing bbox: {size[0]:.2f} × {size[1]:.2f} CAD units; DXF unit must be confirmed in S2</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts)


def file_sha1(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_hash_coord(value: Any) -> str:
    return f"{float(value):.6f}"


def normalize_candidate_for_hash(candidate: dict[str, Any]) -> dict[str, Any]:
    point = candidate.get("cad_point") or {}
    return {
        "id": candidate.get("id"),
        "cad_point": {
            "x": normalize_hash_coord(point["x"]),
            "y": normalize_hash_coord(point["y"]),
        },
        "feature_type": candidate.get("feature_type"),
        "source_handle": candidate.get("source_handle"),
        "source_layer": candidate.get("source_layer"),
    }


def candidate_set_fingerprint_from_source_hash(
    source_dxf_sha1: str,
    boundary: dict[str, Any] | None,
    candidates: list[dict[str, Any]],
    schema_version: str = "1.0",
) -> dict[str, Any]:
    selected_boundary = {
        "handle": boundary.get("handle") if boundary else None,
        "layer": boundary.get("layer") if boundary else None,
    }
    normalized_candidates = [normalize_candidate_for_hash(candidate) for candidate in candidates]
    normalized_candidates.sort(
        key=lambda item: (
            str(item.get("id") or ""),
            str(item.get("source_handle") or ""),
            str(item.get("source_layer") or ""),
            item["cad_point"]["x"],
            item["cad_point"]["y"],
        )
    )
    hash_input = {
        "schema_version": schema_version,
        "source_dxf_sha1": source_dxf_sha1,
        "selected_boundary": selected_boundary,
        "candidates": normalized_candidates,
    }
    encoded = json.dumps(hash_input, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()
    return {
        "candidate_set_id": f"sha256:{digest[:16]}",
        "candidate_set_hash": f"sha256:{digest}",
        "candidate_set_inputs": {
            "schema_version": schema_version,
            "source_dxf_sha1": source_dxf_sha1,
            "selected_boundary": selected_boundary,
            "candidate_count": len(normalized_candidates),
        },
        "candidate_set_hash_input": hash_input,
    }


def candidate_set_fingerprint(
    source_dxf: Path,
    boundary: dict[str, Any] | None,
    candidates: list[dict[str, Any]],
    schema_version: str = "1.0",
) -> dict[str, Any]:
    return candidate_set_fingerprint_from_source_hash(file_sha1(source_dxf), boundary, candidates, schema_version)


def selftest_candidate_set_id() -> dict[str, Any]:
    source_hash = "0123456789abcdef0123456789abcdef01234567"
    boundary = {"handle": "B1", "layer": "0"}
    candidates = [
        {
            "id": "CAD-02",
            "cad_point": {"x": 10.1234567, "y": 20.7654321},
            "feature_type": "road_edge",
            "source_handle": "H2",
            "source_layer": "DLSS",
        },
        {
            "id": "CAD-01",
            "cad_point": {"x": 1.0, "y": 2.0},
            "feature_type": "redline_corner",
            "source_handle": "H1",
            "source_layer": "0",
        },
    ]
    expected_hash = "sha256:1d80924ddf340296c0baab25942e71bd3f6fff3674f45981dac20f9c0f2a91ec"
    base = candidate_set_fingerprint_from_source_hash(source_hash, boundary, candidates)
    if base["candidate_set_hash"] != expected_hash:
        raise AssertionError(f"stable hash expected {expected_hash}, got {base['candidate_set_hash']}")

    repeated = candidate_set_fingerprint_from_source_hash(source_hash, boundary, candidates)
    if repeated["candidate_set_hash"] != expected_hash:
        raise AssertionError("same input did not produce the same candidate_set_hash")

    reordered = candidate_set_fingerprint_from_source_hash(source_hash, boundary, list(reversed(candidates)))
    if reordered["candidate_set_hash"] != expected_hash:
        raise AssertionError("candidate input order changed candidate_set_hash")

    changed_x = json.loads(json.dumps(candidates))
    changed_x[0]["cad_point"]["x"] = 10.2234567
    if candidate_set_fingerprint_from_source_hash(source_hash, boundary, changed_x)["candidate_set_hash"] == expected_hash:
        raise AssertionError("cad_point.x change did not change candidate_set_hash")

    changed_feature = json.loads(json.dumps(candidates))
    changed_feature[0]["feature_type"] = "water_edge"
    if candidate_set_fingerprint_from_source_hash(source_hash, boundary, changed_feature)["candidate_set_hash"] == expected_hash:
        raise AssertionError("feature_type change did not change candidate_set_hash")

    changed_handle = json.loads(json.dumps(candidates))
    changed_handle[0]["source_handle"] = "H2B"
    if candidate_set_fingerprint_from_source_hash(source_hash, boundary, changed_handle)["candidate_set_hash"] == expected_hash:
        raise AssertionError("source_handle change did not change candidate_set_hash")

    return {
        "source_dxf_sha1": source_hash,
        "boundary": boundary,
        "candidates": candidates,
        "expected_candidate_set_id": base["candidate_set_id"],
        "expected_candidate_set_hash": base["candidate_set_hash"],
    }


def build_preview(project_dir: Path) -> dict[str, Any]:
    try:
        import ezdxf
    except Exception as exc:
        raise RuntimeError(f"ezdxf is required for cad_preview.py: {exc}") from exc

    report = read_probe(project_dir)
    dxf_path, source_item = choose_dxf(project_dir, report)
    doc = ezdxf.readfile(str(dxf_path))
    drawables, closed, all_points = collect_geometry(doc)
    if not all_points:
        raise RuntimeError("DXF 中没有可绘制的 LINE/LWPOLYLINE/POLYLINE 实体")
    boundary = choose_boundary(closed, all_points)
    candidates = candidate_vertices(boundary)
    candidates.extend(semantic_feature_candidates(drawables, boundary, candidates))
    source_rel = rel_to_project(dxf_path, project_dir)

    out_dir = project_dir / "05_output" / "cad"
    svg_rel = "05_output/cad/" + PREVIEW_NAME
    candidate_rel = "05_output/cad/" + CANDIDATES_NAME
    fingerprint = candidate_set_fingerprint(dxf_path, boundary, candidates)
    payload = {
        "schema_version": "1.0",
        "candidate_set_id": fingerprint["candidate_set_id"],
        "candidate_set_hash": fingerprint["candidate_set_hash"],
        "candidate_set_inputs": fingerprint["candidate_set_inputs"],
        "status": "ok",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "project_code": project_dir.name,
        "source_dxf": source_rel,
        "source_cad": source_item.get("path"),
        "preview_svg": svg_rel,
        "candidate_json": candidate_rel,
        "selected_boundary": None,
        "candidates": candidates,
        "notes": [
            "CAD candidates are drawing-side points only; the user must pick the corresponding AMap GCJ-02 coordinate.",
            "Generated preview keeps source CAD orientation; do not treat the SVG as north-up unless the source CAD is north-up.",
        ],
    }
    if boundary:
        payload["selected_boundary"] = {
            "handle": boundary["handle"],
            "layer": boundary["layer"],
            "area_xy": boundary["area_xy"],
            "vertex_count": boundary["vertex_count"],
            "bbox_xy": boundary["bbox_xy"],
            "confidence": "candidate_needs_cad_review",
        }
    out_dir.mkdir(parents=True, exist_ok=True)
    svg = render_svg(project_dir.name, source_rel, drawables, boundary, candidates, all_points)
    (out_dir / PREVIEW_NAME).write_text(svg, encoding="utf-8")
    (out_dir / CANDIDATES_NAME).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate S2 CAD preview and candidate control points")
    parser.add_argument("project", nargs="?", help="Project code or path")
    parser.add_argument("--json", action="store_true", help="Print JSON only")
    parser.add_argument("--write", action="store_true", help="Write preview SVG and candidate JSON")
    parser.add_argument("--selftest-candidate-set-id", action="store_true", help="Run candidate_set_id selftest and exit")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.selftest_candidate_set_id:
        try:
            result = selftest_candidate_set_id()
        except AssertionError as exc:
            print(f"candidate_set_id selftest failed: {exc}", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps({"status": "ok", **result}, ensure_ascii=False, indent=2))
        else:
            print("ok: candidate_set_id selftest passed")
            print(f"  candidate_set_id: {result['expected_candidate_set_id']}")
            print(f"  candidate_set_hash: {result['expected_candidate_set_hash']}")
        return 0
    if not args.project:
        print("ERROR: project is required unless --selftest-candidate-set-id is used", file=sys.stderr)
        return 3
    project_dir = resolve_project(args.project)
    if not project_dir.exists():
        print(f"ERROR: project not found: {project_dir}", file=sys.stderr)
        return 3
    try:
        payload = build_preview(project_dir)
    except Exception as exc:
        payload = {
            "schema_version": "1.0",
            "status": "error",
            "project_code": project_dir.name,
            "error": str(exc),
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"== cad_preview :: {project_dir}")
        print(f"  source_dxf: {payload['source_dxf']}")
        print(f"  preview_svg: {payload['preview_svg']}")
        print(f"  candidates: {len(payload['candidates'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

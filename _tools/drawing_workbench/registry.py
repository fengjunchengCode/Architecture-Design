#!/usr/bin/env python3
"""Centralized drawing and object type registry for the drawing workbench."""
from __future__ import annotations

from copy import deepcopy
from typing import Any


# ---------------------------------------------------------------------------
# Drawing types
# ---------------------------------------------------------------------------

DRAWING_REGISTRY: dict[str, dict[str, Any]] = {
    "functional_zoning": {
        "label": "功能分区",
        "status": "enabled",
        "category": "analysis_a",
        "default_base_path": "05_output/drawings/base/master_plan.jpg",
        "object_types": ["functional_zone"],
        "tools": ["closed_path"],
    },
    "planting_design": {
        "label": "绿化设计图",
        "status": "enabled",
        "category": "analysis_a",
        "default_base_path": "05_output/drawings/base/master_plan.jpg",
        "object_types": ["planting_zone", "key_planting_zone", "planting_edge_line"],
        "tools": ["closed_path", "open_path", "supporting_images"],
    },
    "landscape_analysis": {
        "label": "景观绿地规划设计分析",
        "status": "enabled",
        "category": "analysis_a",
        "default_base_path": "05_output/drawings/base/master_plan.jpg",
        "object_types": ["landscape_axis_primary", "landscape_axis_secondary", "landscape_node"],
        "tools": ["open_path", "circle", "supporting_images"],
    },
    "traffic_analysis": {
        "label": "交通组织",
        "status": "enabled",
        "category": "analysis_a",
        "default_base_path": "05_output/drawings/base/master_plan.jpg",
        "object_types": ["vehicle_flow", "pedestrian_flow", "underground_flow", "entrance_marker"],
        "tools": ["open_path", "triangle"],
    },
    "fire_route": {
        "label": "消防流线",
        "status": "enabled",
        "category": "analysis_a",
        "default_base_path": "05_output/drawings/base/master_plan.jpg",
        "object_types": ["fire_route_line", "turning_radius"],
        "tools": ["open_path", "turning_radius"],
    },
    "vertical_analysis": {
        "label": "竖向分区图",
        "status": "enabled",
        "category": "analysis_a",
        "default_base_path": "05_output/drawings/base/master_plan.jpg",
        "object_types": ["elevation_marker", "slope_arrow"],
        "tools": ["elevation_marker", "slope_arrow"],
    },
    "supporting_facilities": {
        "label": "配套分析图",
        "status": "enabled",
        "category": "analysis_a",
        "default_base_path": "05_output/drawings/base/master_plan.jpg",
        "object_types": ["facility_zone", "trash_collection_point"],
        "tools": ["closed_path", "circle", "supporting_images"],
    },
    "sponge_city": {
        "label": "海绵城市专篇",
        "status": "enabled",
        "category": "analysis_a",
        "default_base_path": "05_output/drawings/base/master_plan.jpg",
        "object_types": ["sponge_zone", "ecological_ditch_line", "runoff_line"],
        "tools": ["closed_path", "open_path", "supporting_images"],
    },
    "accessibility_design": {
        "label": "无障碍设计专篇",
        "status": "enabled",
        "category": "analysis_a",
        "default_base_path": "05_output/drawings/base/master_plan.jpg",
        "object_types": ["accessible_facility_zone", "accessible_point"],
        "tools": ["closed_path", "circle", "supporting_images"],
    },
    "civil_defense": {
        "label": "人防设计专篇",
        "status": "enabled",
        "category": "analysis_a",
        "default_base_path": "05_output/drawings/base/civil_defense_base.jpg",
        "object_types": ["civil_defense_zone"],
        "tools": ["closed_path"],
    },
}

DRAWING_ALIASES: dict[str, str] = {}

DRAWING_TYPES: set[str] = set(DRAWING_REGISTRY.keys())


# ---------------------------------------------------------------------------
# Object types
# ---------------------------------------------------------------------------

OBJECT_TYPE_REGISTRY: dict[str, dict[str, Any]] = {
    "functional_zone": {
        "label": "功能区",
        "geometry": "path",
        "closed": True,
    },
    "planting_zone": {
        "label": "普通绿化区域",
        "geometry": "path",
        "closed": True,
    },
    "key_planting_zone": {
        "label": "重点绿化区域",
        "geometry": "path",
        "closed": True,
    },
    "planting_edge_line": {
        "label": "绿化线",
        "geometry": "path",
        "closed": False,
    },
    "landscape_axis_primary": {
        "label": "主要景观轴线",
        "geometry": "path",
        "closed": False,
    },
    "landscape_axis_secondary": {
        "label": "次要景观轴线",
        "geometry": "path",
        "closed": False,
    },
    "landscape_node": {
        "label": "景观节点",
        "geometry": "circle",
        "closed": None,
    },
    "vehicle_flow": {
        "label": "车行流线",
        "geometry": "path",
        "closed": False,
    },
    "pedestrian_flow": {
        "label": "人行流线",
        "geometry": "path",
        "closed": False,
    },
    "underground_flow": {
        "label": "地下车库流线",
        "geometry": "path",
        "closed": False,
    },
    "entrance_marker": {
        "label": "出入口",
        "geometry": "triangle",
        "closed": None,
    },
    "fire_route_line": {
        "label": "消防流线",
        "geometry": "path",
        "closed": False,
    },
    "turning_radius": {
        "label": "转弯半径",
        "geometry": "path",
        "closed": False,
    },
    "elevation_marker": {
        "label": "标高点",
        "geometry": "triangle",
        "closed": None,
    },
    "slope_arrow": {
        "label": "坡度箭头",
        "geometry": "path",
        "closed": False,
    },
    "facility_zone": {
        "label": "配套设施区域",
        "geometry": "path",
        "closed": True,
    },
    "trash_collection_point": {
        "label": "垃圾收集点",
        "geometry": "circle",
        "closed": None,
    },
    "sponge_zone": {
        "label": "海绵城市分区",
        "geometry": "path",
        "closed": True,
    },
    "ecological_ditch_line": {
        "label": "生态草沟线性设施",
        "geometry": "path",
        "closed": False,
    },
    "runoff_line": {
        "label": "雨水径流线",
        "geometry": "path",
        "closed": False,
    },
    "accessible_facility_zone": {
        "label": "无障碍设施区域",
        "geometry": "path",
        "closed": True,
    },
    "accessible_point": {
        "label": "无障碍设施点",
        "geometry": "circle",
        "closed": None,
    },
    "civil_defense_zone": {
        "label": "人防分区",
        "geometry": "path",
        "closed": True,
    },
    "label": {
        "label": "标签",
        "geometry": "point",
        "closed": None,
    },
}

OBJECT_TYPE_ALIASES: dict[str, str] = {
    "main_entrance": "entrance_marker",
}

OBJECT_TYPES: set[str] = set(OBJECT_TYPE_REGISTRY.keys()) | set(OBJECT_TYPE_ALIASES.values())


# ---------------------------------------------------------------------------
# Default styles per object type
# ---------------------------------------------------------------------------

_BASE_STYLE: dict[str, Any] = {
    "fill_mode": "none",
    "fill_color": "#DCE8C8",
    "fill_opacity": 0.42,
    "hatch_angle_deg": 45,
    "hatch_spacing": 0.018,
    "hatch_width": 0.002,
    "stroke_color": "#333333",
    "stroke_width": 0.003,
    "stroke_style": "solid",
    "border_style": "solid",
    "double_border_gap": 0.006,
    "start_arrow": False,
    "end_arrow": False,
    "arrow_size": 0.028,
    "legend_enabled": True,
    "legend_label": "",
    "label_box": {
        "enabled": False,
        "text": "",
        "width": 0.09,
        "height": 0.035,
        "font_size": 0.018,
        "opacity": 0.18,
        "offset": [0.02, -0.02],
    },
    "inline_text": {
        "enabled": False,
        "text": "",
        "font_size": 0.018,
        "position": 0.5,
        "offset": [0, -0.018],
    },
}

_OBJECT_STYLE_OVERRIDES: dict[str, dict[str, Any]] = {
    "functional_zone": {
        "fill_mode": "translucent",
        "fill_color": "#DCE8C8",
        "stroke_color": "#7AA35A",
    },
    "planting_zone": {
        "fill_mode": "translucent",
        "fill_color": "#DCE8C8",
        "stroke_color": "#7AA35A",
    },
    "key_planting_zone": {
        "fill_mode": "hatch",
        "fill_color": "#DCE8C8",
        "stroke_color": "#7AA35A",
    },
    "planting_edge_line": {
        "fill_mode": "none",
        "stroke_color": "#7AA35A",
        "stroke_width": 0.003,
        "legend_enabled": True,
    },
    "landscape_axis_primary": {
        "stroke_color": "#E04030",
        "stroke_width": 0.006,
        "stroke_style": "dashed",
    },
    "landscape_axis_secondary": {
        "stroke_color": "#3070D0",
        "stroke_width": 0.004,
        "stroke_style": "dashed",
    },
    "landscape_node": {
        "fill_mode": "translucent",
        "fill_color": "#DCE8C8",
        "border_style": "double",
    },
    "vehicle_flow": {
        "stroke_color": "#E08020",
        "stroke_width": 0.007,
        "end_arrow": True,
    },
    "pedestrian_flow": {
        "stroke_color": "#3070D0",
        "stroke_width": 0.005,
        "end_arrow": True,
    },
    "underground_flow": {
        "stroke_color": "#3070D0",
        "stroke_width": 0.004,
        "stroke_style": "dashed",
        "end_arrow": True,
    },
    "entrance_marker": {
        "fill_mode": "solid",
        "fill_color": "#E08020",
    },
    "fire_route_line": {
        "stroke_color": "#E08020",
        "stroke_width": 0.008,
        "end_arrow": True,
    },
    "turning_radius": {
        "stroke_color": "#20A0A0",
        "stroke_width": 0.004,
        "end_arrow": True,
        "label_box": {
            "enabled": True,
            "text": "R=9M",
            "width": 0.09,
            "height": 0.035,
            "font_size": 0.018,
            "opacity": 0.18,
            "offset": [0.02, -0.02],
        },
    },
    "elevation_marker": {
        "fill_mode": "solid",
        "fill_color": "#E08020",
        "label_box": {
            "enabled": True,
            "text": "",
            "width": 0.09,
            "height": 0.035,
            "font_size": 0.018,
            "opacity": 0.18,
            "offset": [0.02, -0.02],
        },
    },
    "slope_arrow": {
        "stroke_width": 0.004,
        "end_arrow": True,
        "inline_text": {
            "enabled": True,
            "text": "0.3%",
            "font_size": 0.018,
            "position": 0.5,
            "offset": [0, -0.018],
        },
    },
    "facility_zone": {
        "fill_mode": "translucent",
    },
    "trash_collection_point": {
        "fill_mode": "solid",
        "fill_color": "#DCE8C8",
        "legend_enabled": True,
    },
    "sponge_zone": {
        "fill_mode": "translucent",
    },
    "ecological_ditch_line": {
        "stroke_color": "#7AA35A",
        "stroke_style": "dashed",
    },
    "runoff_line": {
        "stroke_color": "#3070D0",
        "end_arrow": True,
    },
    "accessible_facility_zone": {
        "fill_mode": "translucent",
    },
    "accessible_point": {
        "fill_mode": "translucent",
        "fill_color": "#DCE8C8",
    },
    "civil_defense_zone": {
        "fill_mode": "translucent",
    },
}


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------

def _deep_merge(base: dict, override: dict) -> dict:
    result = deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def normalize_drawing_type(value: object) -> str:
    text = str(value or "").strip()
    if text in DRAWING_REGISTRY:
        return text
    alias = DRAWING_ALIASES.get(text)
    if alias and alias in DRAWING_REGISTRY:
        return alias
    raise ValueError(f"drawing_type must be one of {sorted(DRAWING_TYPES)}")


def normalize_object_type(value: object) -> str:
    text = str(value or "").strip()
    if text in OBJECT_TYPE_REGISTRY:
        return text
    alias = OBJECT_TYPE_ALIASES.get(text)
    if alias and alias in OBJECT_TYPE_REGISTRY:
        return alias
    raise ValueError(f"object_type must be one of {sorted(OBJECT_TYPES)}")


def default_base_path_for(drawing_type: str) -> str:
    entry = DRAWING_REGISTRY.get(drawing_type)
    if not entry:
        raise ValueError(f"unknown drawing_type: {drawing_type}")
    return entry["default_base_path"]


def default_object_style(object_type: str) -> dict[str, Any]:
    override = _OBJECT_STYLE_OVERRIDES.get(object_type, {})
    return _deep_merge(_BASE_STYLE, override)

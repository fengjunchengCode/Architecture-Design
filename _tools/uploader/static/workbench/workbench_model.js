/**
 * Pure logic module for drawing workbench — no DOM dependencies.
 * Exposes both browser global (DrawingWorkbenchModel) and Node export.
 */
(function (root, factory) {
  var model = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = model;
  root.DrawingWorkbenchModel = model;
})(typeof window !== "undefined" ? window : globalThis, function () {
  "use strict";

  // ---------------------------------------------------------------------------
  // Default style templates
  // ---------------------------------------------------------------------------

  var _BASE_STYLE = {
    fill_mode: "none",
    fill_color: "#DCE8C8",
    fill_opacity: 0.42,
    hatch_angle_deg: 45,
    hatch_spacing: 0.018,
    hatch_width: 0.002,
    stroke_color: "#333333",
    stroke_width: 0.003,
    stroke_style: "solid",
    dash_scale: 1,
    border_style: "solid",
    double_border_gap: 0.006,
    start_arrow: false,
    end_arrow: false,
    arrow_size: 0.028,
    legend_enabled: true,
    legend_label: "",
    label_box: {
      enabled: false,
      text: "",
      width: 0.09,
      height: 0.035,
      font_size: 0.018,
      opacity: 0.55,
      offset: [0.02, -0.02],
    },
    inline_text: {
      enabled: false,
      text: "",
      font_size: 0.018,
      position: 0.5,
      offset: [0, -0.018],
    },
  };

  var _STYLE_OVERRIDES = {
    functional_zone: {
      fill_mode: "translucent",
      fill_color: "#DCE8C8",
      stroke_color: "#7AA35A",
    },
    planting_zone: {
      fill_mode: "translucent",
      fill_color: "#7CB342",
      stroke_color: "#2E7D32",
    },
    key_planting_zone: {
      fill_mode: "hatch",
      fill_color: "#7CB342",
      stroke_color: "#1B5E20",
    },
    planting_edge_line: {
      fill_mode: "none",
      stroke_color: "#2E7D32",
      stroke_width: 0.003,
    },
    landscape_axis_primary: {
      stroke_color: "#E11D1D",
      stroke_width: 0.006,
      stroke_style: "dashed",
    },
    landscape_axis_secondary: {
      stroke_color: "#7B2FF0",
      stroke_width: 0.004,
      stroke_style: "dashed",
    },
    landscape_node: {
      fill_mode: "translucent",
      fill_color: "#FFFFFF",
      stroke_color: "#F08A24",
      border_style: "double",
    },
    vehicle_flow: {
      stroke_color: "#E8551E",
      stroke_width: 0.007,
      end_arrow: true,
    },
    pedestrian_flow: {
      stroke_color: "#1F6FE0",
      stroke_width: 0.005,
      end_arrow: true,
    },
    underground_flow: {
      stroke_color: "#1F6FE0",
      stroke_width: 0.004,
      stroke_style: "dashed",
      end_arrow: true,
    },
    entrance_marker: { fill_mode: "solid", fill_color: "#E03020", stroke_color: "#E03020" },
    fire_route_line: {
      stroke_color: "#E11D1D",
      stroke_width: 0.008,
      end_arrow: true,
    },
    turning_radius: {
      stroke_color: "#0E9594",
      stroke_width: 0.004,
      end_arrow: true,
      label_box: {
        enabled: true,
        text: "R=9M",
        width: 0.09,
        height: 0.035,
        font_size: 0.018,
        opacity: 0.55,
        offset: [0.02, -0.02],
      },
    },
    elevation_marker: {
      fill_mode: "solid",
      fill_color: "#7B2FF0",
      stroke_color: "#7B2FF0",
      label_box: {
        enabled: true,
        text: "",
        width: 0.09,
        height: 0.035,
        font_size: 0.018,
        opacity: 0.55,
        offset: [-0.045, -0.09],
      },
    },
    slope_arrow: {
      stroke_color: "#0E7C86",
      stroke_width: 0.004,
      end_arrow: true,
      inline_text: {
        enabled: true,
        text: "0.3%",
        font_size: 0.018,
        position: 0.5,
        offset: [0, -0.018],
      },
    },
    facility_zone: { fill_mode: "translucent", fill_color: "#F08A24", stroke_color: "#A44D00" },
    trash_collection_point: {
      fill_mode: "solid",
      fill_color: "#E03020",
      stroke_color: "#E03020",
    },
    sponge_zone: { fill_mode: "translucent", fill_color: "#00A6A6", stroke_color: "#006D6D" },
    ecological_ditch_line: {
      stroke_color: "#00897B",
      stroke_style: "dashed",
    },
    runoff_line: { stroke_color: "#1565C0", end_arrow: true },
    accessible_facility_zone: { fill_mode: "translucent", fill_color: "#7B2FF0", stroke_color: "#4C1D95" },
    accessible_point: { fill_mode: "translucent", fill_color: "#FFFFFF", stroke_color: "#7B2FF0" },
    civil_defense_zone: { fill_mode: "translucent", fill_color: "#C2185B", stroke_color: "#7B113A" },
    text_label: {
      stroke_color: "#1A1A1A",
      text_content: "文字",
      font_size: 0.024,
      legend_enabled: false,
    },
  };

  var _LEGACY_ALIASES = { main_entrance: "entrance_marker" };

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  function deepClone(obj) {
    return JSON.parse(JSON.stringify(obj));
  }

  function isHexColor(v) {
    return typeof v === "string" && /^#[0-9a-fA-F]{6}$/.test(v);
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------

  function normalizeHexColor(value, fallback) {
    if (typeof value !== "string") return fallback || "#000000";
    var v = value.trim();
    if (/^#[0-9a-fA-F]{3}$/.test(v)) {
      return (
        "#" +
        v[1] +
        v[1] +
        v[2] +
        v[2] +
        v[3] +
        v[3]
      ).toUpperCase();
    }
    if (/^#[0-9a-fA-F]{6}$/.test(v)) return v.toUpperCase();
    return fallback || "#000000";
  }

  function defaultStyleForObjectType(objectType) {
    var override = _STYLE_OVERRIDES[objectType] || {};
    return _deepMergeStyle(deepClone(_BASE_STYLE), override);
  }

  function _deepMergeStyle(base, override) {
    for (var key in override) {
      if (
        override.hasOwnProperty(key) &&
        base[key] &&
        typeof base[key] === "object" &&
        !Array.isArray(base[key]) &&
        typeof override[key] === "object" &&
        !Array.isArray(override[key])
      ) {
        base[key] = _deepMergeStyle(deepClone(base[key]), override[key]);
      } else {
        base[key] = deepClone(override[key]);
      }
    }
    return base;
  }

  function cloneStyle(style) {
    return deepClone(style);
  }

  function normalizeStyleHints(raw, objectType) {
    var defaults = defaultStyleForObjectType(objectType);
    if (!raw || typeof raw !== "object") return defaults;
    var merged = _deepMergeStyle(defaults, raw);
    // Migrate legacy fill_enabled
    if (raw.hasOwnProperty("fill_enabled") && !raw.hasOwnProperty("fill_mode")) {
      merged.fill_mode = raw.fill_enabled ? "translucent" : "none";
    }
    if (merged.fill_color)
      merged.fill_color = normalizeHexColor(merged.fill_color, "#DCE8C8");
    if (merged.stroke_color)
      merged.stroke_color = normalizeHexColor(merged.stroke_color, "#333333");
    return merged;
  }

  function migrateLegacyObject(raw) {
    if (!raw || typeof raw !== "object") return raw;
    var obj = deepClone(raw);
    var geo = obj.geometry || {};
    var kind = geo.kind || "";

    // polygon -> path closed=true
    if (kind === "polygon") {
      obj.geometry = {
        kind: "path",
        closed: true,
        coords: geo.coords || [],
      };
      if (geo.segments) obj.geometry.segments = geo.segments;
    }
    // polyline/arrow -> path closed=false
    else if (kind === "polyline" || kind === "arrow") {
      obj.geometry = {
        kind: "path",
        closed: false,
        coords: geo.coords || [],
      };
      if (geo.segments) obj.geometry.segments = geo.segments;
    }
    // main_entrance point -> entrance_marker triangle
    else if (kind === "point" && raw.type === "main_entrance") {
      var center =
        geo.coords && geo.coords[0] ? geo.coords[0] : [0.5, 0.5];
      obj.type = "entrance_marker";
      obj.geometry = {
        kind: "triangle",
        center: center,
        size: 0.055,
        rotation_deg: 0,
      };
    }

    // Resolve aliases
    if (_LEGACY_ALIASES[obj.type]) {
      obj.type = _LEGACY_ALIASES[obj.type];
    }

    return obj;
  }

  function coordsToSegments(coords, closed) {
    if (!Array.isArray(coords) || coords.length < 2) return [];
    var segs = [];
    for (var i = 0; i < coords.length - 1; i++) {
      segs.push({ kind: "line", from: coords[i], to: coords[i + 1] });
    }
    if (closed && coords.length >= 3) {
      segs.push({
        kind: "line",
        from: coords[coords.length - 1],
        to: coords[0],
      });
    }
    return segs;
  }

  function segmentsToPathD(segments, closed) {
    if (!Array.isArray(segments) || segments.length === 0) return "";
    var parts = [];
    var first = segments[0].from;
    parts.push("M" + first[0] + "," + first[1]);
    for (var i = 0; i < segments.length; i++) {
      var seg = segments[i];
      if (seg.kind === "line") {
        parts.push("L" + seg.to[0] + "," + seg.to[1]);
      } else if (seg.kind === "quadratic") {
        parts.push(
          "Q" +
            seg.control[0] +
            "," +
            seg.control[1] +
            " " +
            seg.to[0] +
            "," +
            seg.to[1]
        );
      }
    }
    if (closed) parts.push("Z");
    return parts.join(" ");
  }

  function sampleSegments(segments, closed) {
    if (!Array.isArray(segments) || segments.length === 0) return [];
    var coords = [segments[0].from];
    var STEPS = 16;
    for (var i = 0; i < segments.length; i++) {
      var seg = segments[i];
      if (seg.kind === "line") {
        coords.push(seg.to);
      } else if (seg.kind === "quadratic") {
        var f = seg.from,
          c = seg.control,
          t = seg.to;
        for (var s = 1; s <= STEPS; s++) {
          var u = s / STEPS;
          var mu = 1 - u;
          coords.push([
            mu * mu * f[0] + 2 * mu * u * c[0] + u * u * t[0],
            mu * mu * f[1] + 2 * mu * u * c[1] + u * u * t[1],
          ]);
        }
      }
    }
    if (!closed && coords.length > 2) {
      var first = coords[0];
      var last = coords[coords.length - 1];
      if (
        Math.abs(first[0] - last[0]) < 1e-5 &&
        Math.abs(first[1] - last[1]) < 1e-5
      ) {
        coords.pop();
      }
    }
    return coords;
  }

  function trianglePoints(center, size, rotationDeg) {
    var cx = center[0],
      cy = center[1];
    var h = size;
    var halfBase = h / Math.sqrt(3);
    var pts = [
      [0, -h * (2 / 3)],
      [-halfBase, h * (1 / 3)],
      [halfBase, h * (1 / 3)],
    ];
    var rad = ((rotationDeg || 0) * Math.PI) / 180;
    var cos = Math.cos(rad),
      sin = Math.sin(rad);
    return pts.map(function (p) {
      return [
        cx + p[0] * cos - p[1] * sin,
        cy + p[0] * sin + p[1] * cos,
      ];
    });
  }

  function lineAngleDeg(coordsOrSegments) {
    var from, to;
    if (
      Array.isArray(coordsOrSegments) &&
      coordsOrSegments.length >= 2 &&
      Array.isArray(coordsOrSegments[0])
    ) {
      // coords array
      from = coordsOrSegments[0];
      to = coordsOrSegments[coordsOrSegments.length - 1];
    } else if (
      Array.isArray(coordsOrSegments) &&
      coordsOrSegments.length > 0
    ) {
      // segments array
      from = coordsOrSegments[0].from;
      to = coordsOrSegments[coordsOrSegments.length - 1].to;
    } else {
      return 0;
    }
    var dx = to[0] - from[0];
    var dy = to[1] - from[1];
    return (Math.atan2(dy, dx) * 180) / Math.PI;
  }

  function legendGroupKey(obj) {
    if (!obj) return "";
    var s = obj.style_hints || {};
    var geometry = obj.geometry || {};
    var kind = geometry.kind || "path";
    var closed = geometry.closed === true;
    var parts = [kind, String(closed)];

    if (kind === "text") {
      parts.push(s.stroke_color || "", String(s.font_size || ""), s.text_content || "");
    } else if (kind === "circle") {
      parts.push(
        s.fill_mode || "",
        s.fill_color || "",
        String(s.fill_opacity || ""),
        s.border_style || "",
        s.stroke_color || "",
        String(s.stroke_width || ""),
        String(s.dash_scale || ""),
        String(s.double_border_gap || "")
      );
    } else if (kind === "triangle") {
      parts.push(
        s.fill_mode || "",
        s.fill_color || "",
        String(s.fill_opacity || ""),
        s.border_style || "",
        s.stroke_color || "",
        String(s.stroke_width || ""),
        String(s.dash_scale || "")
      );
    } else {
      // path
      if (closed) {
        parts.push(
          s.fill_mode || "",
          s.fill_color || "",
          String(s.fill_opacity || ""),
          String(s.hatch_angle_deg || ""),
          String(s.hatch_spacing || ""),
          s.border_style || "",
          s.stroke_color || "",
          String(s.stroke_width || ""),
          String(s.dash_scale || "")
        );
      } else {
        parts.push(
          s.stroke_color || "",
          String(s.stroke_width || ""),
          s.stroke_style || "",
          String(s.dash_scale || ""),
          String(s.start_arrow || false),
          String(s.end_arrow || false),
          String(s.arrow_size || "")
        );
      }
    }
    return parts.join("|");
  }

  function buildLegendGroups(objects) {
    if (!Array.isArray(objects)) return [];
    var map = {};
    var order = [];
    for (var i = 0; i < objects.length; i++) {
      var obj = objects[i];
      var s = obj.style_hints || {};
      if (s.legend_enabled === false) continue;
      var key = legendGroupKey(obj);
      if (!map[key]) {
        var geo = obj.geometry || {};
        map[key] = {
          key: key,
          type: obj.type,
          label: obj.label || s.legend_label || "",
          geometry_kind: geo.kind || "path",
          geometry_closed: geo.closed === true,
          first_object: obj,
          style: cloneStyle(s),
          count: 0,
        };
        order.push(key);
      }
      map[key].count++;
    }
    return order.map(function (k) {
      return map[k];
    });
  }

  return {
    normalizeHexColor: normalizeHexColor,
    normalizeStyleHints: normalizeStyleHints,
    defaultStyleForObjectType: defaultStyleForObjectType,
    migrateLegacyObject: migrateLegacyObject,
    cloneStyle: cloneStyle,
    coordsToSegments: coordsToSegments,
    segmentsToPathD: segmentsToPathD,
    sampleSegments: sampleSegments,
    trianglePoints: trianglePoints,
    lineAngleDeg: lineAngleDeg,
    legendGroupKey: legendGroupKey,
    buildLegendGroups: buildLegendGroups,
  };
});

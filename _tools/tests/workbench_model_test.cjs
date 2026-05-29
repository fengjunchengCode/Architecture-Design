"use strict";

/**
 * Node tests for workbench_model.js pure logic module.
 */

const path = require("path");
const modelPath = path.resolve(__dirname, "..", "uploader", "static", "workbench", "workbench_model.js");
const M = require(modelPath);

let passed = 0;
let failed = 0;

function assert(condition, msg) {
  if (!condition) {
    console.error("FAIL: " + msg);
    failed++;
  } else {
    passed++;
  }
}

function assertEq(actual, expected, msg) {
  if (actual !== expected) {
    console.error("FAIL: " + msg + " — expected " + JSON.stringify(expected) + ", got " + JSON.stringify(actual));
    failed++;
  } else {
    passed++;
  }
}

function assertArrayLen(arr, len, msg) {
  assert(Array.isArray(arr) && arr.length === len, msg + " (length " + (Array.isArray(arr) ? arr.length : "not array") + ")");
}

// Test 1: segmentsToPathD open does not end with Z
(function () {
  const segs = [
    { kind: "line", from: [0.1, 0.1], to: [0.3, 0.3] },
  ];
  const d = M.segmentsToPathD(segs, false);
  assert(!d.endsWith("Z"), "open path should not end with Z");
  assert(d.indexOf("M") >= 0, "open path should start with M");
})();

// Test 2: segmentsToPathD closed ends with Z
(function () {
  const segs = [
    { kind: "line", from: [0.1, 0.1], to: [0.3, 0.1] },
    { kind: "line", from: [0.3, 0.1], to: [0.3, 0.3] },
    { kind: "line", from: [0.3, 0.3], to: [0.1, 0.1] },
  ];
  const d = M.segmentsToPathD(segs, true);
  assert(d.endsWith("Z"), "closed path should end with Z: " + d);
})();

// Test 3: trianglePoints returns 3 points inside [0,1]
(function () {
  const pts = M.trianglePoints([0.5, 0.5], 0.06, 0);
  assertArrayLen(pts, 3, "triangle should have 3 points");
  for (const p of pts) {
    assert(p[0] >= 0 && p[0] <= 1, "x in range: " + p[0]);
    assert(p[1] >= 0 && p[1] <= 1, "y in range: " + p[1]);
  }
})();

// Test 4: normalizeHexColor
(function () {
  assertEq(M.normalizeHexColor("#abc", "#000000"), "#AABBCC", "3-digit hex expands");
  assertEq(M.normalizeHexColor("#ABCDEF", "#000000"), "#ABCDEF", "6-digit hex upper");
  assertEq(M.normalizeHexColor("invalid", "#111111"), "#111111", "invalid falls back");
})();

// Test 5: lineAngleDeg
(function () {
  const horiz = M.lineAngleDeg([[0.1, 0.5], [0.9, 0.5]]);
  assertEq(horiz, 0, "horizontal angle should be 0");
  const vert = M.lineAngleDeg([[0.5, 0.1], [0.5, 0.9]]);
  assertEq(vert, 90, "vertical angle should be 90");
})();

// Test 6: legendGroupKey splits by style
(function () {
  const o1 = {
    type: "vehicle_flow",
    style_hints: { stroke_color: "#FF0000", stroke_width: 0.005, stroke_style: "solid", legend_enabled: true, legend_label: "" },
  };
  const o2 = {
    type: "vehicle_flow",
    style_hints: { stroke_color: "#FF0000", stroke_width: 0.005, stroke_style: "dashed", legend_enabled: true, legend_label: "" },
  };
  const o3 = {
    type: "vehicle_flow",
    style_hints: { stroke_color: "#0000FF", stroke_width: 0.005, stroke_style: "solid", legend_enabled: true, legend_label: "" },
  };
  assert(M.legendGroupKey(o1) !== M.legendGroupKey(o2), "solid vs dashed should differ");
  assert(M.legendGroupKey(o1) !== M.legendGroupKey(o3), "red vs blue should differ");
})();

// Test 7: buildLegendGroups
(function () {
  const objects = [
    { type: "vehicle_flow", style_hints: { stroke_color: "#FF0000", stroke_width: 0.005, stroke_style: "solid", legend_enabled: true, legend_label: "car" } },
    { type: "vehicle_flow", style_hints: { stroke_color: "#FF0000", stroke_width: 0.005, stroke_style: "solid", legend_enabled: true, legend_label: "car" } },
    { type: "pedestrian_flow", style_hints: { stroke_color: "#0000FF", stroke_width: 0.003, stroke_style: "solid", legend_enabled: true, legend_label: "walk" } },
    { type: "vehicle_flow", style_hints: { stroke_color: "#FF0000", stroke_width: 0.005, stroke_style: "solid", legend_enabled: false } },
  ];
  const groups = M.buildLegendGroups(objects);
  assertEq(groups.length, 2, "should be 2 legend groups");
})();

// Test 8: cloneStyle deep-copies nested objects
(function () {
  const style = {
    fill_color: "#FF0000",
    label_box: { enabled: true, text: "R=9M", width: 0.09 },
    inline_text: { enabled: true, text: "0.3%" },
  };
  const clone = M.cloneStyle(style);
  assert(clone.label_box !== style.label_box, "label_box should be different reference");
  assert(clone.inline_text !== style.inline_text, "inline_text should be different reference");
  assertEq(clone.label_box.text, "R=9M", "label_box text preserved");
  assertEq(clone.inline_text.text, "0.3%", "inline_text text preserved");
})();

// Test 9: migrateLegacyObject polygon -> path closed=true
(function () {
  const raw = {
    type: "functional_zone",
    geometry: { kind: "polygon", coords: [[0.1, 0.1], [0.3, 0.1], [0.3, 0.3]] },
    label: "zone",
    style_hints: { fill_enabled: true, fill_color: "#DCE8C8", border_style: "solid", stroke_width: 0.003 },
  };
  const migrated = M.migrateLegacyObject(raw);
  assertEq(migrated.geometry.kind, "path", "polygon->path");
  assertEq(migrated.geometry.closed, true, "polygon->closed=true");
})();

// Test 10: defaultStyleForObjectType
(function () {
  const style = M.defaultStyleForObjectType("functional_zone");
  assert("fill_mode" in style, "should have fill_mode");
  assert("stroke_color" in style, "should have stroke_color");
})();

console.log("Passed: " + passed + ", Failed: " + failed);
process.exit(failed > 0 ? 1 : 0);

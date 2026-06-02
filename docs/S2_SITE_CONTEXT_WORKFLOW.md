# S2 Site Context Workflow

S2 now produces a rough site-context artifact for S3 instead of a point-by-point CAD/map registration.

## Current Flow

1. S1 writes `05_output/amap/s1_map_context.json` with the GCJ-02 center point and surrounding context.
2. S2 reads `05_output/cad/redline_candidate_*.geojson`, normalizes the CAD redline polygon, and draws it as a translucent overlay on the S1 map surface.
3. The user roughly drags, rotates, and optionally scales the redline until it visually faces the surrounding roads.
4. The user clicks the redline edge to add one or more entrances, then selects the road each entrance faces from the S1-derived road list.
5. S2 saves `05_output/site_context/site_context.json`.

## Artifact Contract

`site_context.json` contains:

```json
{
  "north_deg": 0,
  "redline_transform": {
    "x": 0.5,
    "y": 0.5,
    "scale": 1,
    "rotation_deg": 0
  },
  "site_polygon_geo": {
    "coordinate_system": "GCJ-02 / AMap approximate",
    "confidence": "rough_overlay",
    "points": [{"lng": 0, "lat": 0}]
  },
  "entrances": [
    {
      "id": "ENT-1",
      "label": "出入口 1",
      "point_on_redline": {"lng": 0, "lat": 0, "edge_index": 0, "edge_t": 0.5},
      "faces_road": "G317"
    }
  ],
  "surroundings": {
    "roads": [{"name": "G317"}],
    "land_uses": [{"name": "巴青县第一小学", "category": "education_culture"}],
    "notes": []
  }
}
```

`site_polygon_geo` is only an approximate map-side footprint for orientation and semantic binding. CAD remains authoritative for dimensions and area.

## Redline Coordinate Reliability

For `26-BQ-PARK`, `05_output/cad/redline_candidate_1306.geojson` is not reliable geographic data. Its coordinates are in the range `597408..597602 / 3534240..3534370`, and the file states that coordinates are CAD/projected coordinates, not WGS84. The UI therefore defaults to manual rough placement rather than geographic pre-positioning.

## Deprecated Path

The S2 UI no longer requires control point picking, candidate extraction, stale control point management, or registration quality scoring. Existing `05_output/amap/control_points.json` may remain as legacy evidence, but it is not part of the current S2 happy path.

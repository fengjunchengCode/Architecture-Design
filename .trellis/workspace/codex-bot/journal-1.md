# Journal - codex-bot (Part 1)

> AI development session journal
> Started: 2026-06-02

---



## Session 1: S2 redline site context refactor

**Date**: 2026-06-02
**Task**: S2 redline site context refactor
**Branch**: `main`

### Summary

Replaced S2 control-point registration UI with CAD redline rough alignment, entrance road selection, S1-derived surroundings, and site_context.json output. Added API/browser smoke coverage and documented the new workflow.

### Main Changes

- Replaced S2 display basemap with server-generated Tianditu satellite imagery from `_fetch_tdt_tile`.
- Added S1/S2 env self-check for `TIANDITU_KEY` and `AMAP_WEBSERVICE_KEY`.
- Added on-map redline scale handle alongside drag and rotate.
- Merged S1/S2 upload buckets back into S0.
- Added road levels and auto candidate entrances for `site_context.json`, including `road_level` persistence.
- Updated S2 workflow docs and smoke coverage.

### Git Commits

| Hash | Message |
|------|---------|
| `7d9ddbf` | (see git log) |

### Testing

- [OK] `python -m py_compile` for `_tools/drawing_workbench/*.py` and `_tools/uploader/server.py`
- [OK] `node --check _tools/uploader/static/workbench/workbench.js`
- [OK] `node --check _tools/uploader/static/app.js`
- [OK] `python _tools/tests/drawing_workbench_api_smoke.py`
- [OK] `python _tools/tests/drawing_workbench_browser_smoke.py`
- [OK] Real service screenshot/save check for `26-BQ-PARK` S2

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 2: S2 Tianditu site-context fixes

**Date**: 2026-06-02
**Task**: S2 Tianditu site-context fixes
**Branch**: `main`

### Summary

Implemented S2 Tianditu satellite basemap, env self-check, redline scale handle, S0 upload consolidation, road levels, candidate entrances, site_context road_level persistence, smoke coverage, and workflow docs.

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `231959a` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete

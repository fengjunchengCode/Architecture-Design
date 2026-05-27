# Handoff: Functional-Zoning Continuous-Drawing Fix

Date: 2026-05-27  
Project: `26-BQ-PARK`  
Repo: `D:\MyProject\Architecture-Design`  
Intended implementer: local Claude  
Review status: Codex plan reviewed by remote Claude at `1a7fc25`

## 1. Purpose

This handoff is a direct implementation brief. Do not re-plan the feature from scratch. Implement only the approved scope below, then run the listed verification.

The user is testing the architecture workflow on `26-BQ-PARK`, a temporary project based on an already completed design. The current focus is the semantic drawing workbench, especially the `functional_zoning` page where the user hand-draws zoning polygons over a base plan. These polygons later become evidence for Stage 7 technical SVG/PDF drawing generation.

The user wants the drawing workbench to feel closer to PPT/PS/Figma style manual drafting: precise, continuous, zoomable, and able to preserve the user's chosen visual style while drawing multiple zones.

## 2. Repository Rules

Follow these rules before editing:

- Read and obey `AGENTS.md`.
- Read and obey `skills/_shared/development_contract.md`.
- This is a UI/workflow fix. Keep changes minimal and directly tied to the issues below.
- Do not edit `projects/26-BQ-PARK/05_output/record.md`.
- Do not edit or commit `projects/26-BQ-PARK/05_output/inventory.json`.
- Do not commit `projects/26-BQ-PARK/05_output/drawings/semantic/` unless the user explicitly asks.
- Do not touch `traffic_analysis`.
- Do not touch `style_spec.json`, `style_schema.py`, `task_pack.py`, `agent_drawing_protocol.md`, backend APIs, or schema marker files in this wave.
- Do not write `stroke_width_key` to newly saved JSON. It is read-only legacy compatibility.

Local dirty state observed before this handoff:

```text
 M projects/26-BQ-PARK/05_output/inventory.json
?? projects/26-BQ-PARK/05_output/drawings/semantic/
```

Treat those as user/test artifacts. Do not stage them.

## 3. Current Progress

Important recent commits:

- `8c60062` split drawing workbench by drawing type.
- `326780d` refined functional zoning workbench:
  - functional zoning now uses only user-drawn polygons;
  - object type / geometry type / source controls were hidden;
  - labels are not drawn on canvas;
  - style panel added color, fill, border, line width;
  - object-level `style_hints` added.
- `0c7d1a6` fixed canvas coordinate drift and zoom basics:
  - DOM is now `workbenchCanvas` viewport + `workbenchStage` coordinate surface;
  - overlay and image share the same stage;
  - `stroke_width` numeric field replaced write-out of legacy `stroke_width_key`;
  - button zoom exists from 50% to 400%;
  - handles use screen-constant `<ellipse>` to stay 12x12 px at different zooms.
- `1a7fc25` remote Claude approved this next wave and added constraints.

Current relevant files:

- `_tools/uploader/static/index.html`
- `_tools/uploader/static/workbench/workbench.css`
- `_tools/uploader/static/workbench/workbench.js`
- `_tools/drawing_workbench/schema.py`
- `docs/CLAUDE_CODEX_REVIEW_THREAD.md`

Current `schema.py` already supports:

```json
"style_hints": {
  "fill_color": "#DCE8C8",
  "fill_enabled": true,
  "border_style": "solid",
  "stroke_width": 0.003
}
```

Legacy `stroke_width_key` may be read and mapped to a number, but new normalized output must not include it.

## 4. User-Reported Issues For This Wave

The user reports five problems after `0c7d1a6`:

1. A polygon can only be closed by clicking the finish button.
2. After finishing one object, the next object does not inherit the previous object's color, border, fill, or line width.
3. Mouse wheel cannot zoom the base plan.
4. After saving the sketch, switching away and back to functional zoning shows objects in the list, but the sketch is not automatically loaded onto the base plan.
5. A color chosen through the color picker is not remembered; reopening the color area loses the previous custom color.

Remote Claude approved the diagnosis and named this wave:

```text
Wave Functional-Zoning Continuous-Drawing Fix
```

## 5. Approved Implementation Plan

### 5.1 Close Polygon From Canvas

Add an explicit close gesture on the first draft point.

Rules:

- When `state.currentPoints.length >= 3`, render the first draft point as a close handle.
- The close handle must be visually distinct:
  - visible inner mark uses current `fill_color`;
  - outer ring uses a dark stroke;
  - hover state uses pointer cursor and a subtle glow.
- Hit radius must be larger than ordinary handles:
  - ordinary handle: 6 px radius;
  - close handle hit target: at least 10 px radius.
- Because the SVG uses `viewBox="0 0 1 1"` and `preserveAspectRatio="none"`, use ellipse radii derived separately from stage width and height, as the previous wave already did for handles.
- Add a transparent hit ellipse around the visible close handle:
  - class example: `.zone-close-hit`;
  - `pointer-events="all"`;
  - click handler must `stopPropagation()` and call `finishFunctionalZone()`;
  - it must not add an extra point.
- Add `Enter` shortcut:
  - if functional zoning is active and `currentPoints.length >= 3`, finish the polygon;
  - do not intercept when input / textarea / select / contenteditable is focused.
- Keep the existing "完成分区" button as a fallback.
- Existing dblclick may remain, but do not rely on it for the main UX. Avoid adding duplicate points on close.

Add `Esc` behavior:

- If draft points exist, clear `state.currentPoints` and re-render.
- If no draft points but an object is selected, clear `selectedId`.
- Do not intercept while editing text inputs.

Add `Delete` / `Backspace`:

- If an object is selected and focus is not in an input, delete selected object.
- Prevent browser back-navigation on Backspace.

Do not add vertex drag editing in this wave.

### 5.2 Preserve Style For Continuous Drawing

Define `state.zoneDraftStyle` as:

```text
The default style for the next new functional zone, and the most recent style the user intentionally used or edited.
```

Only inherit these fields:

- `fill_color`
- `fill_enabled`
- `border_style`
- `stroke_width`

Do not inherit:

- label
- confidence
- source

Required rules:

1. `finishFunctionalZone()`:
   - uses `normalizeZoneStyle(state.zoneDraftStyle)`;
   - after creating the object, keeps `state.zoneDraftStyle = object.style_hints`;
   - clears `state.zoneDraftLabel`;
   - does not auto-select the finished object.
2. `updateZoneStyle()` when a selected object exists:
   - update selected object;
   - also set `state.zoneDraftStyle = next`;
   - this makes the next object inherit the edited style.
3. `addPoint()` when starting a new polygon while an object is selected:
   - before clearing `selectedId`, copy selected object's `style_hints` into `state.zoneDraftStyle`;
   - then clear `selectedId`;
   - then add the new point.
4. Pure selection must not pollute draft style:
   - selecting a green object and then deselecting without editing must not change `zoneDraftStyle`;
   - only `updateZoneStyle()` or starting a new polygon from selected object should sync it.

This boundary was explicitly required by remote Claude.

### 5.3 Ctrl/Cmd + Mouse Wheel Zoom

Add wheel zoom on `#workbenchCanvas`.

Rules:

- Use `Ctrl + wheel` / `Cmd + wheel`, not plain wheel.
- Plain wheel must remain available for scrolling the viewport/page.
- When Ctrl/Cmd is held:
  - `preventDefault()`;
  - `deltaY < 0` zooms in;
  - `deltaY > 0` zooms out;
  - use factor about `1.1` per wheel step;
  - clamp to 50%-400%.
- Button zoom can keep the existing 25% step.
- Keep `transform: scale()` forbidden. Continue changing `workbenchStage.style.width`.

Add a visible hint near the zoom toolbar:

```text
Ctrl + 滚轮缩放
```

Zoom center algorithm:

```js
const rect = stage.getBoundingClientRect();
const xRatio = (event.clientX - rect.left) / rect.width;
const yRatio = (event.clientY - rect.top) / rect.height;

setCanvasZoom(state.canvasZoom * (event.deltaY < 0 ? 1.1 : 1 / 1.1));

const newRect = stage.getBoundingClientRect();
const targetX = newRect.left + xRatio * newRect.width;
const targetY = newRect.top + yRatio * newRect.height;
viewport.scrollLeft += targetX - event.clientX;
viewport.scrollTop += targetY - event.clientY;
```

Use the actual implementation shape that fits the current code, but preserve this behavior.

### 5.4 Reliable Canvas Re-render After Save/Switch/Reload

Fix the case where object list exists but overlay is blank after switching away and back.

Add a central function, for example:

```js
function renderCanvasLayers(reason = "") {
  applyCanvasZoom();
  renderObjects();
}
```

Current code has `setCanvasZoom()` combining stage width update and render. If you do not add `applyCanvasZoom()`, split the non-render part out so image-ready paths can apply width without causing loops.

Must handle these cases:

1. Image cache hit:
   - if `image.complete && image.naturalWidth > 0`, immediately run the image-ready path;
   - do not wait only for `onload`.
2. Normal image load:
   - `image.onload` runs image-ready path.
3. Switching back to functional zoning:
   - after `loadDrawing()` resolves, schedule `requestAnimationFrame(() => renderCanvasLayers("tab-switch"))`.
4. Style loading:
   - `loadStyle()` may normalize palette/style, but overlay visibility must not depend only on `loadStyle()` finishing.
5. Optional one-shot self-heal:
   - if `state.objects.length > 0` and overlay has no rendered children, log a warning and retry once via `requestAnimationFrame(renderObjects)`;
   - do not create an infinite retry loop.

Do not change backend APIs.

### 5.5 Recent Colors And Custom Color Persistence

Add session-level recent colors:

```js
state.zoneRecentColors = []
```

Remote Claude constraints:

- Recent colors are session-only.
- Do not write recent colors to `style_spec.json`.
- Do not write recent colors to semantic JSON top-level.
- Page refresh clears session state, but `loadDrawing()` rebuilds useful recent colors from saved objects.

Rules:

1. User picks a fixed swatch:
   - update selected object or draft style;
   - update `zoneDraftStyle`;
   - call recent color helper, but avoid showing duplicate colors already present in the base palette.
2. User uses `<input type="color">`:
   - update selected object or draft style;
   - update `zoneDraftStyle`;
   - add color to recent colors.
3. `loadDrawing()`:
   - scan `objects[].style_hints.fill_color`;
   - add non-palette colors to recent colors.
4. UI:
   - first row remains the 10 style/fallback colors;
   - second row shows "最近使用" swatches, up to 6;
   - oldest recent color is removed when over 6;
   - `zoneCustomColor.value` always reflects active style:
     - selected object style if selected;
     - otherwise `zoneDraftStyle`.

Note: The remote Claude response includes both "fixed swatch enters recent" and "colors already in palette should not enter recent." Implement the more specific de-duplication rule: do not display palette/fallback duplicates in the recent row. It is fine if a helper is called for every color and internally drops palette colors.

### 5.6 Keyboard Shortcut Table

Functional zoning tab, when input fields are not focused:

| Key | Behavior |
|---|---|
| `Enter` | Finish current polygon if `currentPoints.length >= 3` |
| `Esc` | Clear draft points; if no draft, clear selected object |
| `Ctrl/Cmd + Z` | Undo (existing) |
| `Ctrl/Cmd + Shift + Z` | Redo (existing) |
| `Delete` / `Backspace` | Delete selected object |
| `Ctrl/Cmd + Wheel` | Zoom |

Do not add arrow-key nudging or space-drag pan in this wave.

## 6. Suggested Code Touch Points

Likely changes are only in:

- `_tools/uploader/static/workbench/workbench.js`
- `_tools/uploader/static/workbench/workbench.css`
- possibly `_tools/uploader/static/index.html`

Expected areas in `workbench.js`:

- State declaration near top:
  - add `zoneRecentColors`.
- `renderFunctionalZoningTools()`:
  - render recent colors row;
  - ensure color input value follows active style;
  - add zoom hint if not done in HTML.
- `normalizeZoneStyle()`:
  - keep returning `stroke_width`, not `stroke_width_key`.
- `updateZoneStyle()`:
  - sync selected changes to `zoneDraftStyle`;
  - update recent colors on fill color change;
  - avoid re-rendering tools on every slider input unless needed.
- `addPoint()`:
  - if selected object exists, copy its style into `zoneDraftStyle` before clearing selection.
- `finishFunctionalZone()`:
  - keep no auto-select;
  - preserve `zoneDraftStyle`;
  - no duplicate closing point.
- `renderDraftSvg()`:
  - render close handle when point count >= 3;
  - use screen-constant ellipse functions.
- Overlay binding:
  - bind close handle click separately and stop propagation.
- `setCanvasZoom()` / zoom helpers:
  - add wheel zoom with center preservation.
- `loadDrawing()` / `loadBaseImage()`:
  - add image cache ready path and renderCanvasLayers.
- `handleShortcuts()`:
  - add Enter, Esc, Delete/Backspace behavior.

Expected CSS additions:

- `.zone-close-hit`
- `.zone-close-ring` or equivalent
- hover state for close handle
- `.zone-recent-colors`
- zoom toolbar hint styling

## 7. Do Not Do

- Do not modify `schema.py` in this wave.
- Do not modify `traffic_analysis`.
- Do not implement plain wheel zoom.
- Do not persist `zoneRecentColors`.
- Do not write recent colors to `style_spec.json` or semantic JSON.
- Do not update `agent_drawing_protocol.md` yet.
- Do not touch `record.md`, `inventory.json`, or project semantic output files.
- Do not add vertex dragging or shape editing.
- Do not introduce a new framework or large refactor.

## 8. Verification

Run these commands:

```powershell
node --check _tools\uploader\static\workbench\workbench.js
git diff --check -- _tools\uploader\static\index.html _tools\uploader\static\workbench\workbench.css _tools\uploader\static\workbench\workbench.js
python _tools\validate_record.py 26-BQ-PARK
```

If `schema.py` is not changed, no Python compile is required, but running it is harmless:

```powershell
python -m py_compile _tools\drawing_workbench\schema.py
```

Browser smoke:

1. Open `http://127.0.0.1:8765/?project=26-BQ-PARK&page=workbench&drawing=functional_zoning`.
2. Draw 3 points.
3. Click the first draft point close handle:
   - polygon finishes;
   - no duplicate point is added;
   - draft handles disappear after finish.
4. Draw 2 points and press `Esc`:
   - draft line disappears.
5. Select an object and press `Delete`:
   - selected object is removed.
6. Create a zone with custom color, dashed border, and `stroke_width=0.009`.
7. Without reselecting style, draw a second zone:
   - it inherits color, border, fill, and stroke width.
8. Select first zone, change color, then start drawing a third zone:
   - third zone inherits the edited color.
9. Select a zone without editing, deselect, then draw:
   - draft style should not be polluted by that mere selection.
10. Use `Ctrl + wheel` over canvas:
    - zoom changes;
    - zoom stays between 50% and 400%;
    - normal wheel still scrolls.
11. Save sketch, switch to `traffic_analysis`, switch back:
    - object list and overlay both appear automatically.
12. Refresh page:
    - saved overlay appears automatically.
13. Use color input to choose a non-palette color:
    - it appears in "最近使用";
    - it remains reusable after tab switch if used by a saved object.

## 9. Expected Completion Report

After implementation, report:

- files changed;
- how each of the 5 user issues was addressed;
- command verification results;
- browser smoke results;
- whether any project output files were generated or left uncommitted.

If committing, stage only code/docs for this wave. Do not stage:

```text
projects/26-BQ-PARK/05_output/inventory.json
projects/26-BQ-PARK/05_output/drawings/semantic/
```

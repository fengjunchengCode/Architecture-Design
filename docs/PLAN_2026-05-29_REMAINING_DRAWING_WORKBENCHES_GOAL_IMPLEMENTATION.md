# 剩余图纸工作台一次性实施计划（Windows Claude /goal 版）

日期：2026-05-29

状态：待 Mac Claude 二审。本文是给 Windows Claude 使用 `/goal` 模式长时间自主实施的详细计划，不是讨论稿。

依据：

- 需求讨论稿：`docs/PLAN_2026-05-28_REMAINING_DRAWING_WORKBENCHES_DISCUSSION.md`
- 终审意见：`docs/CLAUDE_CODEX_REVIEW_THREAD.md`
- 终审结论：需求层面通过，可写 `/goal` 实施计划。

## 0. 给执行 agent 的总指令

你是 Windows Claude，目标是一次性完成“剩余图纸工作台语义层重构”。你没有视觉能力，所以不要依赖截图判断 UI 是否好看；你必须通过本文定义的字段、DOM 状态、semantic JSON、manifest、task pack 和自动测试来证明完成。

本轮只做语义层：

- 做：工作台绘制/编辑语义对象、保存 `semantic JSON`、生成 `task pack`、上传配图并生成 `manifest`。
- 不做：最终 SVG 渲染、PNG/PDF 导出、PPT 排版、日照分析工作台、自动成品图生成。
- 保留：已有工作台 studio 布局、功能分区已有绘制体验、旧导出按钮/接口可不扩展，但不得破坏现有可用路径。

必须遵守：

- 不提交 `projects/26-BQ-PARK/05_output/` 下已有运行输出脏文件，除非用户明确要求。
- 不重置、不清理用户未要求清理的工作区改动。
- 修改前先按本文建立测试和 fixture，实施过程中持续跑测试。
- 所有新图纸都必须通过自动验收脚本，不允许用“看起来应该可以”作为完成证据。

## 1. 完成定义

只有满足下面全部条件，才算完成：

1. `functional_zoning` 仍可加载旧 JSON，旧 `polygon + segments` 弧线不丢失。
2. 所有 9 个图纸类型进入 registry、schema、前端工作台、保存路径和 task pack：
   - `planting_design`
   - `landscape_analysis`
   - `traffic_analysis`
   - `fire_route`
   - `vertical_analysis`
   - `supporting_facilities`
   - `sponge_city`
   - `accessibility_design`
   - `civil_defense`
3. 工作台支持共享图元：
   - 闭合 path：多边形，支持每段弧线。
   - 开放 path：N 点线段/流线，支持每段弧线。
   - circle：圆形标记，半径为 0-1 归一化坐标单位，随图缩放。
   - triangle：等边三角形标记，尺寸为 0-1 归一化坐标单位，随图缩放。
   - labeled arrow：转弯半径直箭头，带半透明标注框。
   - slope arrow：坡度箭头，文字自动平行于箭头方向。
4. 图例按本文第 7 节分组规则生成。
5. 配图上传按图纸类型保存，并生成 manifest；配图不在画布摆放。
6. task pack 包含 semantic JSON、底图、上下文、参考页和配图 manifest/图片。
7. 所有自动测试命令通过。
8. `git status --short` 中只出现本次计划允许提交的代码/文档/测试文件，不出现 `projects/26-BQ-PARK/05_output/` 输出文件。

## 2. 非目标

不要在本轮做这些事：

- 不恢复 deterministic render / SVG / PNG / PDF 成品出图。
- 不让 VLM 或脚本自动生成设计结论。
- 不做日照分析工作台。
- 不做配图在画布上的拖拽摆放。
- 不把景观节点拆成主/次固定子类型。
- 不把出入口拆成主入口/次入口/车库入口固定子类型。
- 不做交通“沿线重复箭头”；P54 中此前误判的符号已确认是出入口标记。
- 不添加 React/Vue/构建链。继续使用原生 HTML/CSS/JS。

## 3. 受影响文件

必须修改：

| 文件 | 目的 |
|---|---|
| `_tools/drawing_workbench/schema.py` | 扩展 schema、图元、样式、兼容迁移 |
| `_tools/drawing_workbench/task_pack.py` | 扩展 drawing types、配图输入、task manifest |
| `_tools/uploader/server.py` | 新增 registry / supporting images API，扩展 load/save/task-pack |
| `_tools/uploader/static/workbench/workbench.js` | 前端工作台通用图元、控件、保存、加载、图例 |
| `_tools/uploader/static/workbench/workbench.css` | 新控件和 supporting image panel 样式 |
| `docs/reference_pdfs/page_index.json` | 增加启泰 P51/P53-P60 参考页索引 |
| `docs/agent_drawing_protocol.md` | 只补语义对象和 task_pack 输入说明，不恢复最终渲染方案 |

建议新增：

| 文件 | 目的 |
|---|---|
| `_tools/drawing_workbench/registry.py` | 后端唯一 drawing/object registry |
| `_tools/uploader/static/workbench/workbench_model.js` | 前端可测试纯逻辑：默认样式、迁移、图例分组、几何计算 |
| `_tools/tests/test_drawing_workbench_schema.py` | Python schema 单测 |
| `_tools/tests/test_drawing_workbench_task_pack.py` | task pack 和配图 manifest 单测 |
| `_tools/tests/test_drawing_workbench_server_api.py` | server handler 级 API 单测或轻量 smoke |
| `_tools/tests/workbench_model_test.cjs` | Node 纯逻辑测试 |
| `_tools/tests/drawing_workbench_api_smoke.py` | 启动本地 server 的 API smoke |
| `_tools/tests/drawing_workbench_browser_smoke.py` | 无视觉浏览器 smoke；必须自动化 Chrome/Edge 并通过，不能跳过 |

不要修改，除非为了避免测试失败必须小范围补充：

- `_tools/drawing_workbench/svg_to_png.py`
- `_tools/drawing_workbench/pdf_page_extract.py`
- S0/S1/S2 业务 skill
- `record.md` schema

## 4. 数据模型硬规格

### 4.1 Schema 版本

将 `_tools/drawing_workbench/schema.py` 中：

- `SCHEMA_VERSION` 提升为 `"1.2"`。
- `ACCEPTED_SCHEMA_VERSIONS` 变为 `{"1.0", "1.1", "1.2"}`。
- `normalize_drawing()` 输出统一使用 `"1.2"`，除非你有非常强理由保留旧版本输出；如果保留旧版本输出，测试必须证明所有新对象仍能被识别。

### 4.2 Drawing registry

新增 `_tools/drawing_workbench/registry.py`，作为后端唯一 registry。至少暴露：

```python
DRAWING_REGISTRY: dict[str, dict]
DRAWING_ALIASES: dict[str, str]
OBJECT_TYPE_REGISTRY: dict[str, dict]
OBJECT_TYPE_ALIASES: dict[str, str]
DRAWING_TYPES: set[str]
OBJECT_TYPES: set[str]
normalize_drawing_type(value: object) -> str
normalize_object_type(value: object) -> str
default_base_path_for(drawing_type: str) -> str
default_object_style(object_type: str) -> dict
```

`schema.py`、`task_pack.py`、`server.py` 都从 `registry.py` 取 drawing/object 常量，不再各自维护字符串集合。

前端可保留 JS registry，但必须通过测试保证与后端 registry 的 drawing ids 和 object type ids 一致。更推荐新增 `/api/drawing/registry`，前端初始化时读取后端 registry。

### 4.3 Drawing types

Registry 必须包含：

| ID | 中文名 | 状态 | 默认底图 |
|---|---|---|---|
| `functional_zoning` | 功能分区 | enabled | `05_output/drawings/base/master_plan.jpg` |
| `planting_design` | 绿化设计图 | enabled | `05_output/drawings/base/master_plan.jpg` |
| `landscape_analysis` | 景观绿地规划设计分析 | enabled | `05_output/drawings/base/master_plan.jpg` |
| `traffic_analysis` | 交通组织 | enabled | `05_output/drawings/base/master_plan.jpg` |
| `fire_route` | 消防流线 | enabled | `05_output/drawings/base/master_plan.jpg` |
| `vertical_analysis` | 竖向分区图 | enabled | `05_output/drawings/base/master_plan.jpg` |
| `supporting_facilities` | 配套分析图 | enabled | `05_output/drawings/base/master_plan.jpg` |
| `sponge_city` | 海绵城市专篇 | enabled | `05_output/drawings/base/master_plan.jpg` |
| `accessibility_design` | 无障碍设计专篇 | enabled | `05_output/drawings/base/master_plan.jpg` |
| `civil_defense` | 人防设计专篇 | enabled | `05_output/drawings/base/civil_defense_base.jpg` |

说明：

- 每张图纸的 `base_image.path` 必须保存在自己的 semantic JSON 中。
- 除 `civil_defense` 外默认可指向 `master_plan.jpg`，但用户一旦上传/选择底图，保存后只影响当前 drawing_type。
- `civil_defense` 默认使用独立底图路径，避免误用总平底图。

### 4.4 Object types

必须包含：

| Object type | 默认 geometry | 用途 |
|---|---|---|
| `functional_zone` | closed path | 功能分区多边形 |
| `planting_zone` | closed path | 普通绿化区域 |
| `key_planting_zone` | closed path | 重点绿化区域 |
| `planting_edge_line` | open path | 绿化线性表达 |
| `landscape_axis_primary` | open path | 主要景观轴线 |
| `landscape_axis_secondary` | open path | 次要景观轴线 |
| `landscape_node` | circle | 景观节点 |
| `vehicle_flow` | open path | 车行流线 |
| `pedestrian_flow` | open path | 人行流线 |
| `underground_flow` | open path | 地下车库流线 |
| `entrance_marker` | triangle | 出入口 |
| `fire_route_line` | open path | 消防流线 |
| `turning_radius` | open path | 转弯半径直箭头和标注框 |
| `elevation_marker` | triangle | 标高三角形和标注框 |
| `slope_arrow` | open path | 坡度箭头和旋转文字 |
| `facility_zone` | closed path | 配套设施区域 |
| `trash_collection_point` | circle | 垃圾收集点 |
| `sponge_zone` | closed path | 海绵城市分区 |
| `ecological_ditch_line` | open path | 生态草沟线性设施 |
| `runoff_line` | open path | 雨水径流线 |
| `accessible_facility_zone` | closed path | 无障碍设施区域 |
| `accessible_point` | circle | 无障碍设施点 |
| `civil_defense_zone` | closed path | 人防分区 |

兼容 alias：

| 旧 object type | 新 object type |
|---|---|
| `main_entrance` | `entrance_marker` |
| `label` | 保留兼容读取，但不作为新建主工具 |

### 4.5 Geometry kinds

`GEOMETRY_KINDS` 至少包含：

- `path`
- `circle`
- `triangle`

允许兼容读入旧值：

- `polygon` -> `path` + `closed=true`
- `polyline` -> `path` + `closed=false`
- `arrow` -> `path` + `closed=false`
- `point` -> 按 object type 迁移。旧 `main_entrance` point 迁移为 `entrance_marker` triangle，使用默认 `size` 和 `rotation_deg=0`。

#### Path geometry

```json
{
  "kind": "path",
  "closed": true,
  "coords": [[0.1, 0.1], [0.3, 0.1], [0.3, 0.3]],
  "segments": [
    {"kind": "line", "from": [0.1, 0.1], "to": [0.3, 0.1]},
    {"kind": "quadratic", "from": [0.3, 0.1], "control": [0.36, 0.2], "to": [0.3, 0.3]},
    {"kind": "line", "from": [0.3, 0.3], "to": [0.1, 0.1]}
  ]
}
```

Rules:

- `closed=true`: minimum 3 coords.
- `closed=false`: minimum 2 coords.
- `segments` is optional. If present, it must be continuous.
- For `closed=true`, `segments[-1].to == segments[0].from`.
- For `closed=false`, do not require closure.
- If `segments` exists, derive `coords` by sampling; keep original endpoints stable.
- Segment kinds: `line`, `quadratic` only.
- Do not implement cubic.

#### Circle geometry

```json
{
  "kind": "circle",
  "center": [0.45, 0.38],
  "radius": 0.035
}
```

Rules:

- `center` is normalized `[x, y]`.
- `radius` is normalized drawing coordinate, not screen pixels.
- Circle radius must scale with the drawing when zooming.
- Default radius: `0.035`.
- Minimum radius: `0.006`.
- Maximum radius: `0.25`.
- Edit handles may be screen-constant; the saved radius must not be screen-constant.

#### Triangle geometry

```json
{
  "kind": "triangle",
  "center": [0.52, 0.42],
  "size": 0.055,
  "rotation_deg": 0
}
```

Rules:

- `center` is normalized `[x, y]`.
- `size` is normalized drawing coordinate, representing triangle height.
- `size` must scale with the drawing when zooming.
- Default size: `0.055`.
- Minimum size: `0.01`.
- Maximum size: `0.3`.
- `rotation_deg` is numeric, normalized to `[0, 360)`.
- Render as an equilateral triangle centered on `center`.

### 4.6 Style hints

Unify `style_hints` for all object types. Missing fields must be filled from object defaults.

Recommended normalized shape:

```json
{
  "fill_mode": "translucent",
  "fill_color": "#DCE8C8",
  "fill_opacity": 0.42,
  "hatch_angle_deg": 45,
  "hatch_spacing": 0.018,
  "hatch_width": 0.002,
  "stroke_color": "#7AA35A",
  "stroke_width": 0.003,
  "stroke_style": "solid",
  "border_style": "solid",
  "double_border_gap": 0.006,
  "start_arrow": false,
  "end_arrow": false,
  "arrow_size": 0.028,
  "legend_enabled": true,
  "legend_label": "",
  "label_box": {
    "enabled": false,
    "text": "",
    "width": 0.09,
    "height": 0.035,
    "font_size": 0.018,
    "opacity": 0.18,
    "offset": [0.02, -0.02]
  },
  "inline_text": {
    "enabled": false,
    "text": "",
    "font_size": 0.018,
    "position": 0.5,
    "offset": [0, -0.018]
  }
}
```

Validation:

- Hex colors must be `#RRGGBB`.
- `fill_mode`: `none`, `translucent`, `solid`, `hatch`.
- `fill_opacity`: `0` to `1`.
- `hatch_angle_deg`: `0` to `180`; default `45`.
- `hatch_spacing`: normalized, default `0.018`, range `0.004` to `0.08`.
- `hatch_width`: normalized, default `0.002`, range `0.0005` to `0.02`.
- `stroke_style`: `solid`, `dashed`.
- `border_style`: `none`, `solid`, `dashed`, `double`.
- `stroke_width`: normalized, default per object type, range `0.0005` to `0.03`.
- `double_border_gap`: normalized, default `0.006`, range `0.001` to `0.04`.
- `arrow_size`: normalized, default `0.028`, range `0.006` to `0.12`.
- label/inline text font sizes are normalized drawing coordinates, not CSS pixels.

Compatibility:

- Old `fill_enabled=true` -> `fill_mode="translucent"`.
- Old `fill_enabled=false` -> `fill_mode="none"`.
- Old functional zone `border_style` maps to new `border_style`.
- Old functional zone `fill_color` maps to both `fill_color` and default `stroke_color` when no explicit stroke exists.

## 5. Per drawing workbench configuration

### 5.1 Functional zoning

Keep existing behavior, but migrate internally to closed path.

Allowed object types:

- `functional_zone`

Tools:

- Closed path polygon.

Required:

- Existing fill/no-fill UI still works.
- Existing arc handles still work.
- New schema may store `fill_mode`, but UI can continue presenting functional zoning’s simple controls unless easy to upgrade.

Regression:

- Old `functional_zoning.json` loads.
- Old `polygon + segments` saves back without losing arcs.

### 5.2 Planting design

Allowed object types:

- `planting_zone`
- `key_planting_zone`
- `planting_edge_line`

Tools:

- Closed path.
- Open path.
- Supporting image panel.

Defaults:

- `planting_zone`: green translucent fill, solid border.
- `key_planting_zone`: green hatch fill, solid border.
- `planting_edge_line`: green stroke, no fill, no arrows, legend enabled.

Controls:

- Fill mode includes `hatch`.
- Open path can be N points and per-segment arc.
- Legend enabled/name.

### 5.3 Landscape analysis

Allowed object types:

- `landscape_axis_primary`
- `landscape_axis_secondary`
- `landscape_node`

Tools:

- Open path.
- Circle marker.
- Supporting image panel.

Defaults:

- Primary axis: red/orange stroke, width `0.006`, dashed.
- Secondary axis: blue stroke, width `0.004`, dashed.
- Landscape node: circle radius `0.035`, translucent fill, double border.

Controls:

- Stroke width numeric/range.
- Stroke solid/dashed.
- Circle resize with normalized radius.
- Circle fill: none/translucent/solid.
- Circle border: none/solid/dashed/double.
- Style clone from selected node or last style.

### 5.4 Traffic analysis

Allowed object types:

- `vehicle_flow`
- `pedestrian_flow`
- `underground_flow`
- `entrance_marker`

Tools:

- Open path.
- Triangle marker.

Defaults:

- `vehicle_flow`: orange stroke, width `0.007`, solid, `end_arrow=true`.
- `pedestrian_flow`: blue stroke, width `0.005`, solid, `end_arrow=true`.
- `underground_flow`: blue stroke, width `0.004`, dashed, `end_arrow=true`.
- `entrance_marker`: triangle size `0.055`, solid or translucent fill configurable.

Controls:

- Start arrow and end arrow independently.
- Arrow size.
- Triangle rotation and size.
- Triangle fill solid/translucent/none.
- Legend label.

Compatibility:

- Old `main_entrance` point objects load as `entrance_marker` triangles with default size/rotation.

### 5.5 Fire route

Allowed object types:

- `fire_route_line`
- `turning_radius`

Tools:

- Open path.
- Turning-radius arrow.

Defaults:

- Fire route line: orange stroke, width `0.008`, solid, end arrow on.
- Turning radius: cyan/blue stroke, width `0.004`, end arrow on, label box enabled with text `R=9M`.

Rules:

- Turning radius is a straight two-point open path.
- It has `label_box.enabled=true`.
- Label text color equals arrow/stroke color.
- Label box background uses the same color with opacity.
- Creating a new turning radius copies selected/last turning radius style.

### 5.6 Vertical analysis

Allowed object types:

- `elevation_marker`
- `slope_arrow`

Tools:

- Triangle marker with label box.
- Open path slope arrow with inline text.

Defaults:

- Elevation marker: triangle size `0.055`, orange fill, label box enabled.
- Elevation label default text: empty or `3660.9`; user edits.
- Slope arrow: stroke width `0.004`, end arrow on, inline text enabled, default text `0.3%`.

Rules:

- Slope text has no label box.
- Slope text rotates parallel to the first-to-last direction of the path.
- Text color equals stroke color.

### 5.7 Supporting facilities

Allowed object types:

- `facility_zone`
- `trash_collection_point`

Tools:

- Closed path.
- Circle marker.
- Supporting image panel.

Defaults:

- Facility zone: translucent fill, solid border.
- Trash collection point: circle radius `0.03`, solid fill default, legend enabled.

### 5.8 Sponge city

Allowed object types:

- `sponge_zone`
- `ecological_ditch_line`
- `runoff_line`

Tools:

- Closed path.
- Open path.
- Supporting image panel.

Defaults:

- Sponge zone: translucent fill.
- Ecological ditch line: green dashed stroke.
- Runoff line: blue solid or dashed stroke with optional end arrow.

### 5.9 Accessibility design

Allowed object types:

- `accessible_facility_zone`
- `accessible_point`

Tools:

- Closed path.
- Circle marker.
- Supporting image panel.

Do not enable `accessible_route` this round.

### 5.10 Civil defense

Allowed object types:

- `civil_defense_zone`

Tools:

- Closed path.

Default base:

- `05_output/drawings/base/civil_defense_base.jpg`

Rules:

- User can upload/select a separate base image.
- Do not assume master plan base image is correct.

## 6. Backend implementation plan

### Wave B1: Registry

1. Add `_tools/drawing_workbench/registry.py`.
2. Move drawing/object constants into registry.
3. Update imports in `schema.py`, `task_pack.py`, `server.py`.
4. Add `/api/drawing/registry` in `server.py`.

API response shape:

```json
{
  "ok": true,
  "schema_version": "1.0",
  "default_drawing_type": "functional_zoning",
  "drawings": {
    "planting_design": {
      "label": "绿化设计图",
      "status": "enabled",
      "category": "analysis_a",
      "default_base_path": "05_output/drawings/base/master_plan.jpg",
      "object_types": ["planting_zone", "key_planting_zone", "planting_edge_line"],
      "tools": ["closed_path", "open_path", "supporting_images"]
    }
  },
  "objects": {
    "planting_edge_line": {
      "label": "绿化线",
      "geometry": "path",
      "closed": false,
      "default_style": {}
    }
  }
}
```

Acceptance:

- `python - <<'PY' ... import registry ...` prints all 10 drawing types.
- `/api/drawing/registry` returns all drawing types.

### Wave B2: Schema

Modify `_tools/drawing_workbench/schema.py`.

Required functions:

- `_normalize_geometry()`
- `_normalize_path_geometry()`
- `_normalize_circle_geometry()`
- `_normalize_triangle_geometry()`
- `_normalize_segments(value, object_index, closed)`
- `_sample_segments(segments, closed)`
- `_normalize_style_hints()`
- `_migrate_legacy_geometry(raw_geometry, object_type)`
- `_migrate_legacy_style(raw_style)`

Important details:

- `segmentsToPathD` equivalent in Python is not needed, but sampling is.
- Open path segments must not be forced closed.
- Closed path segments must be forced closed.
- If coords are present but segments absent, do not materialize segments in schema unless needed; frontend can create temporary segments for editing.
- Normalize object labels:
  - Keep existing `label` for human-readable name.
  - Add/use `style_hints.legend_label`; if empty, frontend can mirror from `label`.

Acceptance:

- Unit tests cover every accepted/rejected case in section 12.

### Wave B3: Supporting images

Modify `server.py`.

Routes:

- `GET /api/drawing/supporting/list?project={code}&drawing_type={id}`
- `POST /api/drawing/supporting/upload?project={code}&drawing_type={id}`
- `POST /api/drawing/supporting/update`
- `POST /api/drawing/supporting/delete`

Storage:

- Directory: `projects/{code}/05_output/drawings/supporting/{drawing_type}/`
- Manifest: `projects/{code}/05_output/drawings/supporting/{drawing_type}/manifest.json`

Manifest shape:

```json
{
  "schema_version": "1.0",
  "project_code": "26-BQ-PARK",
  "drawing_type": "planting_design",
  "updated_at": "2026-05-29T10:00:00+08:00",
  "images": [
    {
      "id": "img-20260529-100000-001",
      "file": "05_output/drawings/supporting/planting_design/img-20260529-100000-001.jpg",
      "original_name": "tree.jpg",
      "caption": "",
      "sort_order": 1,
      "notes": "",
      "uploaded_at": "2026-05-29T10:00:00+08:00"
    }
  ]
}
```

Validation:

- Allowed extensions: `.jpg`, `.jpeg`, `.png`, `.webp`.
- Sanitize filenames with existing `sanitize_filename()`.
- Never allow paths outside `projects/{code}/05_output/drawings/supporting/{drawing_type}/`.
- Delete route must only delete files listed in manifest and inside that folder.

### Wave B4: Base image per drawing

Current `handle_drawing_base_upload()` only takes project. Update it to accept optional `drawing_type`.

Rules:

- Upload still stores under `05_output/drawings/base/`.
- Response returns path and URL.
- Frontend updates current drawing’s `base_image.path`; save persists it.
- `default_drawing_for_project()` uses `default_base_path_for(drawing_type)`.

Do not make base upload automatically mutate semantic JSON on the server; frontend should still call save after changing base.

### Wave B5: Task pack

Modify `task_pack.py`.

Add supporting images to task pack:

- Read manifest for `drawing_type`.
- Copy manifest to `supporting/manifest.json`.
- Copy each image into `supporting/images/`.
- Add task input:

```json
"supporting_images": {
  "manifest": "supporting/manifest.json",
  "images_dir": "supporting/images",
  "count": 3
}
```

Keep task pack usable if supporting manifest does not exist:

```json
"supporting_images": {
  "manifest": null,
  "images_dir": null,
  "count": 0
}
```

Reference pages:

- Update `docs/reference_pdfs/page_index.json` only for known 启泰 pages:
  - `planting_design`: `[51]`
  - `landscape_analysis`: `[53]`
  - `traffic_analysis`: `[54]`
  - `fire_route`: `[55]`
  - `vertical_analysis`: `[56]`
  - `supporting_facilities`: `[57]`
  - `sponge_city`: `[58]`
  - `accessibility_design`: `[59]`
  - `civil_defense`: `[60]`
- Leave Changjiang unknown pages unchanged unless already indexed.

## 7. Frontend implementation plan

### Wave F1: Pure model module

Add `_tools/uploader/static/workbench/workbench_model.js`.

Expose both browser global and Node export:

```js
(function (root, factory) {
  const model = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = model;
  root.DrawingWorkbenchModel = model;
})(typeof window !== "undefined" ? window : globalThis, function () {
  return { ... };
});
```

Functions to include:

- `normalizeHexColor(value, fallback)`
- `normalizeStyleHints(raw, objectType, registry)`
- `migrateLegacyObject(raw, registry)`
- `coordsToSegments(coords, closed)`
- `segmentsToPathD(segments, closed)`
- `sampleSegments(segments, closed)`
- `trianglePoints(center, size, rotationDeg)`
- `lineAngleDeg(coordsOrSegments)`
- `legendGroupKey(object)`
- `buildLegendGroups(objects)`
- `defaultStyleForObjectType(objectType, registry)`
- `cloneStyle(style)`

Node tests must cover this module.

### Wave F2: Registry loading

Modify `workbench.js`:

- Replace static `DRAWING_WORKBENCHES` as source of truth with registry loaded from `/api/drawing/registry`.
- Keep a minimal fallback for `functional_zoning` only, so the page does not crash if registry fails.
- `init()` must wait for registry before `renderDrawingTabs()`.

Acceptance:

- Browser smoke can assert tabs contain all enabled drawing ids.
- If registry API fails, workbench shows a clear error, not a blank page.

### Wave F3: State model

Extend state:

```js
state.activeTool = "closed_path";
state.currentPoints = [];
state.selectedId = "";
state.styleDrafts = {};        // objectType -> style_hints
state.lastStyleByType = {};    // objectType -> style_hints
state.supportingImages = {};   // drawingType -> manifest
state.registry = null;
```

Style cloning rules:

- When user selects an object, inspector shows that object’s style.
- Creating a new object uses:
  1. selected object style if selected object type equals new object type;
  2. otherwise `lastStyleByType[objectType]`;
  3. otherwise registry default.
- After creating/editing object, update `lastStyleByType[objectType]`.

### Wave F4: Tool modes

Replace generic old `GEOMETRY_OPTIONS` UI with registry-driven tool buttons.

Tools:

- `closed_path`
- `open_path`
- `circle`
- `triangle`
- `turning_radius`
- `elevation_marker`
- `slope_arrow`
- `supporting_images`

DOM expectations:

- A container inside `#drawingSpecificTools` renders object type select and style controls.
- Tool buttons are buttons, not text-only pseudo elements.
- Existing `#finishObject`, `#undoPoint`, `#redoAction`, `#deleteObject`, `#clearDraft` remain bound.
- Finish button label changes:
  - closed path: `完成多边形`
  - open path: `完成线段`
  - circle/triangle: no finish required after click creation, but button can be disabled
  - turning radius/slope arrow: `完成箭头` if using two clicks

### Wave F5: Drawing interactions

Click behavior:

- Closed path:
  - Each click adds one point.
  - User clicks finish button or Enter to complete.
  - Minimum 3 points.
- Open path:
  - Each click adds one point.
  - Minimum 2 points.
  - User clicks finish button or double-clicks to complete.
- Circle:
  - One click creates circle at point with default/clone radius.
  - Selection handles allow radius change.
- Triangle:
  - One click creates triangle at point with default/clone size/rotation.
  - Inspector numeric controls edit size/rotation.
- Turning radius:
  - First click start, second click end and object is created.
  - Geometry is open path with 2 coords.
  - `end_arrow=true`, `label_box.enabled=true`.
- Elevation marker:
  - One click creates triangle with label box.
- Slope arrow:
  - First click start, second click end and object is created.
  - `end_arrow=true`, `inline_text.enabled=true`.

Arc handles:

- Use current center-handle idea for all path objects.
- For open paths, `ensureSegments(obj)` must not add a closing segment.
- For closed paths, `ensureSegments(obj)` must add closing segment.
- `segmentsToPathD(segments, closed)` appends `Z` only when `closed=true`.

Selection:

- Clicking any rendered object selects it.
- Clicking selected object again keeps selection.
- Clicking empty canvas while not drawing clears selection.
- Object list selection remains working.

### Wave F6: Rendering

Implement rendering for:

- Path:
  - closed path: SVG `<path>` or `<polygon>` with fill/border.
  - open path: SVG `<path>` with stroke, no fill.
  - dashed: `stroke-dasharray`.
  - arrows: SVG marker at start/end.
  - hatch fill: SVG `<pattern>` with stable id.
  - double border: render two paths/circles/triangles with gap.
- Circle:
  - SVG `<circle>` with normalized radius.
  - Hit target should be larger but invisible.
- Triangle:
  - SVG `<polygon>` using `trianglePoints()`.
  - Hit target should be larger but invisible.
- Label box:
  - SVG `<rect>` + `<text>`.
  - Background fill color = parent stroke/fill color, opacity from style.
  - Text fill = same parent color.
- Inline text:
  - SVG `<text transform="rotate(angle cx cy)">`.
  - No background.

Important:

- Saved radius/size/font size/box size are normalized drawing units.
- Edit handles can use screen-constant radii via current handle logic.

### Wave F7: Inspector controls

Controls must be explicit and testable:

- Object type select.
- Legend label input.
- Legend enabled checkbox.
- Color inputs:
  - fill color
  - stroke color
- Fill mode segmented control:
  - none
  - translucent
  - solid
  - hatch
- Fill opacity range.
- Hatch controls:
  - angle
  - spacing
  - width
- Stroke controls:
  - width
  - solid/dashed
- Border controls:
  - none/solid/dashed/double
  - double gap
- Arrow controls:
  - start arrow
  - end arrow
  - arrow size
- Circle controls:
  - radius
- Triangle controls:
  - size
  - rotation
- Label box controls:
  - text
  - box width
  - box height
  - font size
  - opacity
  - x/y offset
- Inline text controls:
  - text
  - font size
  - position
  - x/y offset

Controls shown should depend on selected object/tool. Do not show irrelevant controls for every tool.

### Wave F8: Supporting images UI

Add a supporting images panel inside the inspector/workflow rail for drawing types that include `supporting_images` tool.

UI requirements:

- File input accepts `.jpg,.jpeg,.png,.webp`.
- Upload button.
- List rows with:
  - thumbnail or filename
  - caption input
  - notes input
  - sort order controls
  - delete button
- The panel must state through data, not prose, that images are for PPT layout and are not canvas objects. Avoid long instructional text in UI.

API interactions:

- On drawing load, call supporting list for current drawing type if tool is enabled.
- Upload refreshes manifest.
- Caption/notes/order update persists through update API.
- Delete removes file and manifest entry.

### Wave F9: Save/load

Update `buildDrawing()`:

- Use normalized model functions before POST.
- Save all objects in schema 1.2.
- Preserve `base_image.path` per drawing type.
- Do not include supporting images in drawing JSON; supporting images stay in manifest.

Update `loadDrawing()`:

- Normalize/migrate objects returned by backend.
- Do not filter functional zoning to only old `geometry.kind==="polygon"`; accept `path closed=true`.
- Load supporting manifest separately.

## 8. CSS plan

Modify `_tools/uploader/static/workbench/workbench.css` only for new controls.

Requirements:

- Do not rework global studio layout.
- Keep right inspector scrollable.
- Add compact controls; no nested cards inside cards.
- Buttons use icon/text only where commands are clear.
- Stable dimensions for marker previews, swatches, upload rows, icon buttons.
- Do not use large hero/marketing styling.

Suggested classes:

- `.wb-tool-grid`
- `.wb-tool-btn`
- `.wb-field-grid`
- `.wb-style-row`
- `.wb-swatch-grid`
- `.wb-supporting-list`
- `.wb-supporting-row`
- `.wb-legend-preview`

## 9. Task pack and docs plan

### 9.1 Task pack

Update task `schema_version` to `"1.1"` if adding supporting images. Keep old consumers tolerant.

`task.json` must include:

- `drawing_type`
- `inputs.sketch`
- `inputs.base_image`
- `inputs.style_spec`
- `inputs.context`
- `inputs.references`
- `inputs.supporting_images`

No final SVG generation is required by this work.

### 9.2 `docs/agent_drawing_protocol.md`

Add a short section:

- New semantic object kinds in schema 1.2.
- Supporting images are optional inputs to task pack.
- This round does not require generating SVG/PPT.
- If a future agent consumes task pack, it must read `supporting/manifest.json`.

Do not expand detailed SVG rendering rules for the new object types in this PR.

## 10. Implementation order

Follow this exact order to reduce breakage.

### Phase 0: Baseline checks

Run:

```powershell
git status --short --branch
node --check _tools\uploader\static\app.js
node --check _tools\uploader\static\workbench\workbench.js
python -m py_compile _tools\drawing_workbench\schema.py _tools\drawing_workbench\task_pack.py _tools\uploader\server.py
```

Record failures in final notes. Do not fix unrelated failures unless they block this work.

### Phase 1: Add tests first

Add `_tools/tests/` if absent.

Create unit tests with fixtures:

- Old functional zoning polygon with quadratic segments.
- Open N-point path with one quadratic segment.
- Circle with double border.
- Triangle with rotation.
- Turning radius with label box.
- Slope arrow with inline text.
- Supporting image manifest.

Tests may initially fail. Commit is not required per phase, but do not move to final until all pass.

### Phase 2: Registry + schema

Implement `registry.py` and schema changes. Make Python unit tests pass.

### Phase 3: Backend APIs

Implement:

- `/api/drawing/registry`
- supporting image APIs
- base upload drawing_type handling
- task pack supporting images

Make API tests pass.

### Phase 4: Frontend model

Implement `workbench_model.js` and Node tests. Make Node tests pass.

### Phase 5: Frontend UI/interactions

Refactor `workbench.js` to use registry/model. Enable all drawing types.

Keep functional zoning usable after each major edit.

### Phase 6: Browser/API smoke

Add smoke scripts and run them. Fix failures.

### Phase 7: Docs/page index/final checks

Update docs and page index. Run all commands in section 12.

## 11. Automatic test specifications

### 11.1 Python unit tests

Create `_tools/tests/test_drawing_workbench_schema.py`.

Must test:

1. `functional_zoning` old polygon with quadratic segments normalizes to schema 1.2 path closed true.
2. Open path with 4 coords and 3 segments accepts.
3. Open path with 1 coord rejects.
4. Closed path with 2 coords rejects.
5. Open path discontinuous segments rejects.
6. Closed path non-closing segments rejects.
7. Circle accepts radius, rejects missing radius, rejects screen-like bad values outside range.
8. Triangle accepts size/rotation, rejects missing size.
9. `fill_enabled` migrates to `fill_mode`.
10. `main_entrance` migrates to `entrance_marker`.
11. `turning_radius` has default `label_box.text == "R=9M"` when missing.
12. `slope_arrow` has default `inline_text.text == "0.3%"` when missing.

Create `_tools/tests/test_drawing_workbench_task_pack.py`.

Must test:

1. Task pack builds for every drawing type with minimal valid sketch.
2. Missing supporting manifest gives count 0.
3. Existing supporting manifest copies manifest and images into task pack.
4. Page index references for qitai new drawings are discovered or safely produce reference errors without crashing.

Create `_tools/tests/test_drawing_workbench_server_api.py` or include in API smoke.

Must test supporting manifest update/delete path safety.

### 11.2 Node model tests

Create `_tools/tests/workbench_model_test.cjs`.

Must test:

1. `segmentsToPathD(openSegments, false)` does not end with `Z`.
2. `segmentsToPathD(closedSegments, true)` ends with `Z`.
3. `trianglePoints([0.5,0.5],0.06,0)` returns 3 points inside `[0,1]`.
4. Circle/triangle size values are preserved as normalized numbers.
5. `lineAngleDeg()` returns expected angle for horizontal/vertical arrows.
6. Legend groups split by stroke width, dash, fill mode, legend label.
7. Style clone deep-copies nested `label_box` and `inline_text`.
8. Legacy object migration maps `polygon` to `path closed=true`.

### 11.3 API smoke

Create `_tools/tests/drawing_workbench_api_smoke.py`.

Behavior:

- Create a temporary project `99-ZZ-WBTEST` under `projects/`.
- Ensure cleanup in `finally`, after checking resolved path is under `projects/99-ZZ-WBTEST`.
- Start uploader server on a free localhost port with `--no-browser`.
- Exercise HTTP API:
  - `GET /api/drawing/registry`
  - `GET /api/drawing/load` for every drawing type
  - `POST /api/drawing/save` with one valid object for every drawing type
  - `POST /api/drawing/supporting/upload` for drawing types with supporting images
  - `GET /api/drawing/supporting/list`
  - `POST /api/drawing/task-pack`
- Assert JSON fields, paths, object counts, and manifest counts.

This test must not require visual perception.

### 11.4 Browser smoke

Create `_tools/tests/drawing_workbench_browser_smoke.py`.

This test is mandatory. It must run without visual inspection and must fail if it cannot automate a browser.

- Use installed Chrome or Edge headless. On Windows, try these paths in order:
  - `C:\Program Files\Google\Chrome\Application\chrome.exe`
  - `C:\Program Files (x86)\Google\Chrome\Application\chrome.exe`
  - `C:\Program Files\Microsoft\Edge\Application\msedge.exe`
  - `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`
- Start server.
- Navigate to workbench page for test project.
- Use browser automation to execute JavaScript in page context.
- Assert DOM state and internal data, not screenshots.

Implementation options:

- If Playwright is already available in the execution environment, use it.
- If Playwright is not available, implement a minimal Chrome DevTools Protocol client inside the Python script or use another deterministic headless browser automation method available on the machine.
- Do not skip this test silently. The final acceptance command includes this script and it must exit 0.

Minimum assertions:

- Left drawing tabs contain all enabled drawing types.
- Selecting each drawing type updates hidden `#drawingType`.
- Tool panel renders at least one expected tool for that drawing.
- Creating through exposed test helper or DOM clicks results in object count increase.
- Save button persists semantic JSON and reload restores object.

## 12. Final acceptance command block

At the end, run exactly:

```powershell
git status --short --branch
python -m py_compile _tools\drawing_workbench\registry.py _tools\drawing_workbench\schema.py _tools\drawing_workbench\task_pack.py _tools\uploader\server.py
node --check _tools\uploader\static\app.js
node --check _tools\uploader\static\workbench\workbench_model.js
node --check _tools\uploader\static\workbench\workbench.js
python -m unittest discover -s _tools\tests -p "test_drawing_workbench*.py"
node _tools\tests\workbench_model_test.cjs
python _tools\tests\drawing_workbench_api_smoke.py
python _tools\tests\drawing_workbench_browser_smoke.py
python _tools\validate_record.py 26-BQ-PARK
git status --short --branch
```

Expected:

- All commands pass.
- Final `git status --short --branch` shows only intended source/doc/test files before staging.
- It must not show staged or unstaged `projects/26-BQ-PARK/05_output/` files caused by this task.

If `projects/26-BQ-PARK/05_output/` files were dirty before starting, leave them unstaged and explicitly mention they were pre-existing.

## 13. Per drawing smoke payloads

Use these payloads in tests and API smoke.

### Functional zoning

```json
{
  "type": "functional_zone",
  "geometry": {
    "kind": "path",
    "closed": true,
    "coords": [[0.1,0.1],[0.3,0.1],[0.3,0.3]],
    "segments": [
      {"kind":"line","from":[0.1,0.1],"to":[0.3,0.1]},
      {"kind":"quadratic","from":[0.3,0.1],"control":[0.36,0.2],"to":[0.3,0.3]},
      {"kind":"line","from":[0.3,0.3],"to":[0.1,0.1]}
    ]
  },
  "label": "功能区A"
}
```

### Planting

- `planting_zone`: closed path with `fill_mode="hatch"`.
- `planting_edge_line`: open path with 3 coords and one quadratic segment.

### Landscape

- `landscape_axis_primary`: open dashed path, width `0.006`.
- `landscape_node`: circle radius `0.035`, `border_style="double"`.

### Traffic

- `vehicle_flow`: open path, `end_arrow=true`.
- `pedestrian_flow`: open path, `start_arrow=true`, `end_arrow=true`.
- `underground_flow`: open dashed path.
- `entrance_marker`: triangle, `fill_mode="solid"`, `rotation_deg=45`.

### Fire

- `fire_route_line`: open path with one quadratic.
- `turning_radius`: open two-point path with label box `R=9M`.

### Vertical

- `elevation_marker`: triangle with label box text `3660.9`.
- `slope_arrow`: open two-point path with inline text `0.3%`.

### Supporting facilities

- `facility_zone`: closed path.
- `trash_collection_point`: circle with solid fill.

### Sponge

- `sponge_zone`: closed path.
- `ecological_ditch_line`: open dashed path.
- `runoff_line`: open path with end arrow.

### Accessibility

- `accessible_facility_zone`: closed path.
- `accessible_point`: circle.

### Civil defense

- `civil_defense_zone`: closed path.
- Base path should default to `05_output/drawings/base/civil_defense_base.jpg`.

## 14. Commit and review handoff

After all tests pass:

1. Stage only intended files.
2. Commit with:

```powershell
git commit -m "feat(workbench): implement semantic drawing workbenches"
```

3. Push current branch.
4. Update or append `docs/CLAUDE_CODEX_REVIEW_THREAD.md` only if the user asks; otherwise leave review thread to Mac Claude.
5. Final message must include:
   - commit hash
   - tests run
   - explicit statement that no required checks were skipped; if any required check is blocked, do not claim completion
   - note that `projects/26-BQ-PARK/05_output/` pre-existing dirty files were not staged

## 15. Common failure modes to avoid

- Do not make circle radius or triangle size screen-pixel based. Saved geometry uses normalized coordinates.
- Do not filter functional zoning objects by `geometry.kind === "polygon"` after migration; accept `path closed=true`.
- Do not close open path segments.
- Do not append `Z` to open path SVG.
- Do not treat edit handles as saved geometry.
- Do not merge legend entries only by object type; use style and legend label grouping keys.
- Do not put supporting images into semantic drawing JSON.
- Do not require reference page extraction to succeed for task pack creation; keep current graceful `reference_errors` behavior.
- Do not let base image upload mutate every drawing type’s base path.
- Do not add fixed marker subtypes for landscape node or entrance marker.

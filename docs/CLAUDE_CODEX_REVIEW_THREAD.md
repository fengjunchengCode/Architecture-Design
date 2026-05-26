# Claude / Codex Review Thread

本文档只保留最近一轮正式回复；历史请看 `git log -- docs/CLAUDE_CODEX_REVIEW_THREAD.md`。

---

## 2026-05-26 Codex -> Claude：语义图纸工作台 UI 架构重构方案，请审核

### 背景

用户确认 `style_card.svg` 箭头修复已通过，并要求继续推进 S10 技术图纸流程。

进入当前 `图纸工作台` 后，用户指出现有 UI 方向不符合长期需求：

- 当前页面想用一个通用工作台覆盖所有技术图纸。
- 这样会导致所有图种的对象类型、按钮、说明、校验和生成逻辑都堆到一个页面。
- 用户希望每种技术图纸都有独立工作台，后续可以逐张图纸设计具体做法和功能。
- 左侧主导航点击“图纸”进入图纸工作台没有问题，但进入后需要在顶部切换不同技术图纸的专用工作台。

用户要求：先写完整 UI 架构重构方案，推送给 Claude 审核；本轮不实现代码。

### 当前实现核查

当前代码形态：

- `_tools/uploader/static/index.html`
  - 只有一个 `<section class="page" data-page="workbench">`。
  - 图种通过 `#drawingType` 下拉选择：
    - `functional_zoning`
    - `traffic_analysis`
  - 同一个左侧工具栏承载所有对象类型：
    - `functional_zone`
    - `vehicle_flow`
    - `pedestrian_flow`
    - `main_entrance`
    - `label`
  - 保存草图、发给 agent、导出 PNG/PDF 共用一套按钮。

- `_tools/uploader/static/workbench/workbench.js`
  - `drawingType()` 读取 `#drawingType.value`。
  - `loadDrawing()` / `saveDrawing()` / `sendToAgent()` / `exportDrawing()` 都围绕当前下拉值工作。
  - 画布、点选、对象列表、状态条是通用逻辑。

- `_tools/drawing_workbench/schema.py`
  - 当前仅允许两个图种：`functional_zoning`、`traffic_analysis`。
  - 这一点不应该在 UI 重构第一步里扩写，避免图种还没设计就先污染 schema。

### 目标

把当前“万能工作台”重构为“图纸中心 + 图种专用工作台”：

```text
左侧主导航：图纸
  ↓
图纸中心 / Drawing Workbench Shell
  ↓ 顶部图种切换
功能分区工作台 | 交通分析工作台 | 景观分析工作台 | 消防流线工作台 | 竖向分析工作台 | ...
  ↓
每个图种拥有自己的对象面板、操作按钮、说明、校验、task_pack 说明
```

核心原则：

- 左侧“图纸”仍是唯一入口。
- 进入后顶部用图种 tabs / segmented control 切换，不再用一个普通下拉承载全部逻辑。
- 每个图种是独立子工作台，不共享一大坨通用控件。
- 底图加载、画布点选、对象渲染、保存、task_pack、导出等底层能力可以共享。
- 图种专属内容通过配置或模块注入，不在 DOM 里堆全部控件。
- 未设计完成的图种可以显示为“占位/待设计”，但不要写入 schema，也不要生成无效语义文件。

### 建议信息架构

```mermaid
flowchart TD
  A["page=workbench 左侧图纸入口"] --> B["DrawingWorkbenchShell"]
  B --> C["StyleStrip 当前风格状态"]
  B --> D["DrawingTabs 顶部图种切换"]
  B --> E["SharedBaseBar 底图路径/上传/加载"]
  B --> F["CurrentDrawingWorkspace"]

  F --> G["FunctionalZoningWorkspace"]
  F --> H["TrafficAnalysisWorkspace"]
  F --> I["FutureDrawingPlaceholder"]

  G --> G1["功能区对象面板"]
  G --> G2["分区多边形/标签"]
  G --> G3["保存 functional_zoning semantic"]
  G --> G4["生成 functional_zoning task_pack"]

  H --> H1["交通对象面板"]
  H --> H2["车行/人行/入口/后勤"]
  H --> H3["保存 traffic_analysis semantic"]
  H --> H4["生成 traffic_analysis task_pack"]

  B --> J["SharedCanvasEngine"]
  J --> J1["base image"]
  J --> J2["normalized coords"]
  J --> J3["overlay SVG"]
  J --> J4["object list"]
```

### URL 与路由

建议使用 query 参数表达当前图种：

```text
?project=26-BQ-PARK&page=workbench&drawing=functional_zoning
?project=26-BQ-PARK&page=workbench&drawing=traffic_analysis
```

行为：

- 进入 `page=workbench` 且没有 `drawing` 参数时，默认 `functional_zoning`。
- 点击顶部 tab 时：
  - 更新 URL 的 `drawing` 参数。
  - 加载对应 `05_output/drawings/semantic/{drawing_type}.json`。
  - 切换对应专用工具面板。
  - 画布和底图保持在同一视觉位置，不整页跳转。

### 第一阶段只支持的图种

第一轮重构只让两个已有 schema 图种可编辑：

| 图种 | 状态 | 原因 |
|---|---|---|
| `functional_zoning` | 可编辑 | schema 已支持，当前已有对象类型可复用 |
| `traffic_analysis` | 可编辑 | schema 已支持，当前已有对象类型可复用 |
| `landscape_analysis` | 占位/待设计 | 用户尚未定义对象和流程 |
| `fire_route` | 占位/待设计 | schema 未支持，不应先写假逻辑 |
| `vertical_analysis` | 占位/待设计 | schema 未支持，不应先写假逻辑 |

占位 tab 可以出现，但点击后只展示：

```text
该图纸工作台待设计。
请在对话中定义该图纸的对象类型、输入方式、输出目标后再启用。
```

不显示保存按钮，不生成 semantic json，不触发 task_pack。

### 组件拆分建议

第一轮保持低风险，不急着大拆文件。建议先在现有 `workbench.js` 内部建立 registry 和 render 分层；等行为稳定后再拆模块。

#### 1. Drawing registry

新增类似：

```js
const DRAWING_WORKBENCHES = {
  functional_zoning: {
    label: "功能分区",
    status: "enabled",
    description: "标注功能区边界、名称和必要标签。",
    objectTypes: [
      { value: "functional_zone", label: "功能区", defaultGeometry: "polygon" },
      { value: "label", label: "标签", defaultGeometry: "point" },
    ],
    taskButtonLabel: "生成分区图任务包",
    agentNotesPlaceholder: "例如：请把不同功能区整理为低饱和分区色块，并生成底部图例。"
  },
  traffic_analysis: {
    label: "交通分析",
    status: "enabled",
    description: "标注车行、人行、入口和关键流线。",
    objectTypes: [
      { value: "vehicle_flow", label: "车行流线", defaultGeometry: "arrow" },
      { value: "pedestrian_flow", label: "人行流线", defaultGeometry: "arrow" },
      { value: "main_entrance", label: "主入口", defaultGeometry: "point" },
      { value: "label", label: "标签", defaultGeometry: "point" },
    ],
    taskButtonLabel: "生成交通图任务包",
    agentNotesPlaceholder: "例如：请将橙色理解为车行主流线，蓝绿色为人行流线。"
  },
  landscape_analysis: {
    label: "景观分析",
    status: "planned",
    description: "待设计：景观节点、视线、活动场景、水系关系等。"
  }
};
```

#### 2. Shell 层

职责：

- 读项目号。
- 读 style spec 状态。
- 显示顶部图种 tabs。
- 管理当前 `drawing_type`。
- 调用 shared load/save/task-pack/export。

#### 3. Workspace 层

职责：

- 根据 registry 渲染对象类型。
- 根据图种显示专属说明、默认对象、placeholder、按钮文案。
- 控制该图种是否允许保存和打包。

#### 4. Shared canvas engine

继续复用当前逻辑：

- `loadBaseImage`
- `normalizedPoint`
- `addPoint`
- `finishObject`
- `renderObjects`
- `renderObjectList`
- `buildDrawing`
- `saveDrawing`
- `sendToAgent`

但这些函数不再直接读全局 DOM 下拉 `#drawingType`，而是读 `state.currentDrawingType`。

### DOM 重构建议

把当前：

```html
<select id="drawingType">...</select>
```

改为：

```html
<div class="drawing-tabs" id="drawingTabs"></div>
<input id="drawingType" type="hidden" value="functional_zoning">
```

保留隐藏字段可降低改动范围，因为现有 JS 若暂时还依赖 `#drawingType`，不会完全断裂。

新增：

```html
<section class="drawing-workspace-head">
  <h3 id="drawingWorkspaceTitle"></h3>
  <p id="drawingWorkspaceDescription"></p>
  <div id="drawingWorkspaceState"></div>
</section>

<aside class="workbench-side">
  <div id="drawingSpecificTools"></div>
  ...
</aside>
```

`#drawingSpecificTools` 由 registry 渲染，不再硬编码所有对象类型。

### UI 验收标准

第一轮 UI 重构完成后，至少满足：

1. 打开 `?project=26-BQ-PARK&page=workbench` 默认进入功能分区工作台。
2. 顶部能看到图种切换，而不是只有一个下拉。
3. 点击“功能分区”：
   - 工具栏只显示功能分区相关对象。
   - 保存到 `semantic/functional_zoning.json`。
   - task_pack 是 `functional_zoning`。
4. 点击“交通分析”：
   - 工具栏只显示交通相关对象。
   - 保存到 `semantic/traffic_analysis.json`。
   - task_pack 是 `traffic_analysis`。
5. 点击未启用图种：
   - 显示待设计说明。
   - 不允许保存。
   - 不允许生成 task_pack。
6. 切换图种时，底图不需要重新上传。
7. URL 中 `drawing=` 会同步，刷新后仍停留在对应图种。
8. `style_spec.approved_at` 非空时，style strip 显示已批准状态；为空时明确提示不能进入真图生产。

### 实施步骤建议

#### Step 1：UI shell 重构

文件：

- `_tools/uploader/static/index.html`
- `_tools/uploader/static/workbench/workbench.css`
- `_tools/uploader/static/workbench/workbench.js`

改动：

- 用顶部 tabs 替换 visible drawing type 下拉。
- 增加 hidden `#drawingType`，作为兼容桥。
- 增加工作台标题、说明、状态区域。
- 保留底图栏、画布、对象列表、保存、task_pack、导出等现有区域。

验证：

```powershell
python _tools/uploader/server.py
```

浏览器打开：

```text
http://127.0.0.1:8765/?project=26-BQ-PARK&page=workbench
```

#### Step 2：registry 驱动对象面板

文件：

- `_tools/uploader/static/workbench/workbench.js`

改动：

- 增加 `DRAWING_WORKBENCHES`。
- `drawingType()` 改读 `state.currentDrawingType` 或 hidden input。
- `renderDrawingTabs()`。
- `renderDrawingWorkspace()`。
- `setDefaultGeometry()` 从 registry 取 default。
- `objectName()` 从 registry 或 shared label map 取值。

验证：

- 功能分区只显示 `functional_zone` / `label`。
- 交通分析只显示 `vehicle_flow` / `pedestrian_flow` / `main_entrance` / `label`。

#### Step 3：占位图种保护

文件：

- `_tools/uploader/static/workbench/workbench.js`
- `_tools/uploader/static/workbench/workbench.css`

改动：

- planned 图种只展示说明，不调用 `/api/drawing/load`。
- planned 图种禁用保存和 task_pack。
- 不修改 `_tools/drawing_workbench/schema.py`。

验证：

- 点击 planned tab 不报错。
- 不生成新 semantic 文件。

#### Step 4：回归保存与 task_pack

验证命令：

```powershell
python _tools/validate_record.py 26-BQ-PARK
```

浏览器验证：

- 保存 `functional_zoning` 后检查：
  - `projects/26-BQ-PARK/05_output/drawings/semantic/functional_zoning.json`
- 保存 `traffic_analysis` 后检查：
  - `projects/26-BQ-PARK/05_output/drawings/semantic/traffic_analysis.json`
- 生成 task_pack 后检查：
  - `projects/26-BQ-PARK/05_output/drawings/task_packs/*/task.json`

### 不建议第一轮做的事

- 不新增 schema 图种。
- 不把所有图种的专属逻辑一次性写完。
- 不重写后端 API。
- 不拆成复杂前端框架。
- 不进入 Stage 7 真图生产。
- 不让 agent 自动补用户尚未设计的图纸对象。
- 不修改 `record.md`。

### 需要 Claude 审核的问题

1. 是否同意“先 registry 化、暂不拆多文件模块”的低风险路线？
2. 是否同意第一轮只启用 `functional_zoning` 和 `traffic_analysis`，其他图种只做 planned 占位？
3. 是否同意 URL 使用 `drawing=` 参数，而不是新增 `page=functional_zoning` / `page=traffic_analysis`？
4. 是否需要在第一轮就把 `workbench.js` 拆成：
   - `workbench/state.js`
   - `workbench/canvas.js`
   - `workbench/registry.js`
   - `workbench/workbench.js`
   
   Codex 倾向暂不拆，先控制 diff。
5. 是否需要补一个轻量前端 smoke test，还是人工浏览器验证足够？

### Codex 倾向

我建议 Claude 批准后按以下方式实施：

- 第一轮只做 UI 架构和 registry，不扩大图纸类型 schema。
- 保留现有 API 和文件路径。
- 功能分区、交通分析两个工作台先复用当前保存/打包能力。
- 用户后续逐张定义图纸时，再逐个把 planned tab 升级为 enabled workspace。

请 Claude 审核后给 GO / 修改意见。

# 全 App Studio 化重构实施计划

## 0. 目标和成功标准

目标：把上传 UI 从“1240px 居中 + 顶部横向阶段 tab + 工作台单页 full-bleed hack”统一成“全局左活动栏 + 全局瘦顶栏 + 全屏内容区”的 studio 外壳。工作台 studio v3 保持现有能力和视觉基准，只收口到全局外壳内。

成功标准：
- 所有顶层页面共用同一个 64px 左活动栏和 54px 瘦顶栏，不再依赖 `body.workbench-mode` 隐藏 `.mast`/`.stage-nav`。
- 所有现有 `id`、`data-page`、`.stage-tab`、`.bucket[data-bucket]` 保留；现有事件绑定继续工作。
- S1/S2 高德地图在新全屏布局下初始化后可见，切页后会触发 resize，不改地图业务逻辑。
- `#output`/`#resultHint` 只在状态页内部显示；S0 上触发检查时跳到状态页看结果。
- 每个 wave 可独立验证、独立提交；不动 schema、agent 协议、绘图数据结构、validator、record。

无视觉执行者必须先读文本原型：`docs/prototypes/whole_app_studio_text_prototype.html`。该文件包含每页的目标结构、所有现有 id 的落点、组件尺寸和文本说明。

## 1. 设计决策

### 1.1 全局导航

采用“全局一级活动栏 + 工作台内部二级活动栏”：
- 全局左栏承载项目 / S0 / S1 / S2 / 图纸 / 状态，按钮仍是 `.stage-tab[data-page]`，id 仍是 `#tabProject`、`#tabS0`、`#tabS1`、`#tabS2`、`#tabWorkbench`、`#tabStatus`。
- 工作台内保留当前 `#drawingTabs` 二级图纸类型栏。理由：图纸类型只在图纸上下文内有意义，混进全局栏会让 S0/S1/S2 用户误以为它们是顶层阶段；保留内部栏也最大限度保护已认可的 workbench v3。
- `#wbHome` 保留在工作台二级栏顶部，继续返回项目页；全局栏也可直接切页，两者不冲突。

### 1.2 全局外壳

生产 DOM 的外层改为：

```html
<main class="studio-shell">
  <nav class="studio-act" aria-label="主导航">
    <button class="studio-logo" type="button" title="Architecture Design">建</button>
    <div class="studio-act-scroll">
      <!-- 保留 stage-tab + id + data-page，内部文案可变为 glyph + tip -->
    </div>
  </nav>
  <section class="studio-main">
    <header class="studio-top">
      <div class="studio-title">
        <span class="crumb" id="studioCrumb">Architecture Design / 未选择项目</span>
        <b id="studioTitle">创建或选择项目</b>
      </div>
      <span class="studio-badge" id="studioPageBadge">项目</span>
      <span class="studio-spacer"></span>
      <div class="status-pill" id="activeProject">未选择项目</div>
    </header>
    <section class="page-shell studio-pages">
      <!-- 现有 .page[data-page] 按 wave 搬进来 -->
    </section>
  </section>
</main>
```

`#studioCrumb`、`#studioTitle`、`#studioPageBadge` 是新增 id，只服务全局 chrome；旧 `#activeProject` 移入瘦顶栏。

### 1.3 组件语言

把 workbench v3 token 提升为全局变量，命名沿用现有 `--ink`/`--muted`/`--line`/`--panel`/`--accent`，并在 workbench.css 内继续兼容 `--*3`。不要引入新色系。

推荐全局样式基底：

```css
:root {
  color-scheme: light;
  --paper:#efe9dc; --panel:#fbf8f1; --panel-2:#f3eee2;
  --ink:#2b2722; --muted:#8a8173; --faint:#b4ab99;
  --line:#ddd5c5; --line-soft:#e8e1d2;
  --accent:#1f6f5b; --accent-soft:rgba(31,111,91,.10);
  --accent-line:rgba(31,111,91,.32); --accent-2:#c2502f;
  --canvas:#fcfaf4; --grid:rgba(43,39,34,.055); --grid-strong:rgba(43,39,34,.10);
  --shadow:0 1px 2px rgba(43,39,34,.06),0 8px 26px rgba(43,39,34,.08);
  --shadow-pop:0 10px 34px rgba(43,39,34,.16);
  --act-w:64px; --top-h:54px; --r:9px;
}
body {
  margin:0; min-height:100vh; overflow:hidden;
  font-family:"IBM Plex Sans SC","Microsoft YaHei UI","Segoe UI",sans-serif;
  background:var(--paper); color:var(--ink);
}
.studio-shell { height:100vh; width:100vw; display:grid; grid-template-columns:var(--act-w) 1fr; background:var(--panel); }
.studio-main { min-width:0; min-height:0; display:flex; flex-direction:column; }
.studio-top { height:var(--top-h); flex-shrink:0; background:var(--panel); border-bottom:1px solid var(--line); display:flex; align-items:center; gap:16px; padding:0 16px; }
.studio-pages { flex:1; min-height:0; overflow:auto; background:linear-gradient(var(--grid) 1px,transparent 1px) 0 0/26px 26px,linear-gradient(90deg,var(--grid) 1px,transparent 1px) 0 0/26px 26px,var(--canvas); }
```

## 2. Wave 1：全局 Shell 和导航

改动范围：`_tools/uploader/static/index.html`、`_tools/uploader/static/style.css`、`_tools/uploader/static/app.js`。

具体步骤：
- 用 §1.2 的结构替换当前 `<main class="shell">`、`.mast`、`.workspace`、横向 `.stage-nav` 外壳。只移动现有页面，不改页面内部业务控件。
- 把 6 个 stage button 改成左栏图标按钮，但保留原 id、`.stage-tab`、`data-page`、`b`、说明 `span`，新增 `.glyph` 和 `.tip`。
- `.shell`、`.mast`、`.workspace` 可以暂时保留兼容样式，但生产 DOM 不再依赖它们。
- 在 `index.html` 的 `<head>` 中加入和 `docs/prototypes/workbench_layout_v3.html` 相同的 IBM Plex 字体链接：

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans+SC:wght@400;500;600;700&display=swap" rel="stylesheet">
```

- 删除或停用 `body.workbench-mode` CSS 规则；`app.js setControls()` 中删除 `document.body.classList.toggle("workbench-mode", ...)`。
- 新增页面元数据和 topbar 更新函数：

```js
const PAGE_META = {
  project: { title: "创建或选择项目", badge: "项目", crumb: "Architecture Design / Project" },
  s0: { title: "S0 建档输入", badge: "S0", crumb: "Architecture Design / S0 Intake" },
  s1: { title: "S1 区位输入", badge: "S1", crumb: "Architecture Design / S1 Location" },
  s2: { title: "S2 地形与配准输入", badge: "S2", crumb: "Architecture Design / S2 Terrain" },
  workbench: { title: "图纸工作台", badge: "图纸", crumb: "Architecture Design / Drawing Studio" },
  status: { title: "项目检查", badge: "状态", crumb: "Architecture Design / Status" },
};

function updateStudioChrome() {
  const meta = PAGE_META[state.page] || PAGE_META.project;
  $("#studioCrumb").textContent = state.project ? `${state.project} / ${meta.crumb.split(" / ").pop()}` : meta.crumb;
  $("#studioTitle").textContent = meta.title;
  $("#studioPageBadge").textContent = meta.badge;
}
```

- 在 `setControls()` 里更新 `#activeProject` 后调用 `updateStudioChrome()`。
- 保持现有 `document.querySelectorAll("[data-page].stage-tab")` 绑定，不新增第二套导航逻辑。

验证：
- `node --check _tools/uploader/static/app.js`
- 启动 `python _tools/uploader/server.py`，打开 `http://127.0.0.1:8765`。
- 未选择项目时仅项目页可用；选择项目后 6 个左栏按钮状态从 locked/ready/active 正常切换。
- 切到图纸页时，页面仍在全局左栏右侧显示，不再隐藏全局 chrome。

提交点：`feat(uploader): introduce global studio shell`

## 3. Wave 2：项目页和 S0 页

改动范围：`index.html`、`style.css`，少量 `app.js` 点击后跳转。

项目页结构：
- 页面主体使用两列：左列 `.studio-card` 放 `#projectCode`、`#projectName`、`#projectType`、`#createProject`、`#projectHint`；右列 `.studio-card` 放 `#refreshProjects` 和 `#projectList`。
- `#refreshProjects` 从旧 page-head 移入右列标题行；id 不变。
- 页面不再使用大号 `.page-head`，说明文字压缩进卡片内。

S0 结构：
- 左列为 `S0 资料桶`，保留全部 `.bucket[data-bucket]`：
  - `briefing`
  - `location_map`
  - `site_photo`
  - `chat`
  - `reference`
- 右列为 `准入`，保留 `#gateStatus`、`#runInventory`、`#runValidate`。
- S0 上运行 Inventory/Validate 后，自动跳到状态页显示 `#output`：

```js
async function runAndShowStatus(task) {
  setPage("status");
  await task();
}

$("#runInventory").addEventListener("click", () => runAndShowStatus(runInventory).catch((err) => writeOutput(err.message)));
$("#runValidate").addEventListener("click", () => runAndShowStatus(runValidate).catch((err) => writeOutput(err.message)));
```

注意：`#runInventoryStatus`、`#runValidateStatus` 保持原有直接执行逻辑。

验证：
- 创建/打开项目成功后，项目 chip 高亮仍由 `renderProjectList()` 控制。
- 上传资料桶仍调用 `upload(bucket,input)`；`.bucket.locked`、`.bucket.has-files`、`.bucket-state` 仍正常变化。
- 从 S0 点“运行 Inventory”后切到状态页，并在状态页看到结果。

提交点：`refactor(uploader): restyle project and s0 studio pages`

## 4. Wave 3：S1 区位页和地图 resize

改动范围：`index.html`、`style.css`、`app.js`。

S1 结构：
- 两列布局：左列宽度 `minmax(320px,420px)`，右列 `1fr`。
- 左列包含 `#amapStatus`、`#centerLocation`、`#checkAmap`、`#saveCenter`、区位图 `.bucket[data-bucket="location_map"]`、外部拾取器链接。
- 右列只包含 `#s1AmapPanel`，内部保留 `#s1AmapStatus`、`#s1AmapMap`、`#s1AmapHint`。
- `#s1AmapMap` 目标高度：桌面 `min-height: calc(100vh - var(--top-h) - 96px)`，下限 420px；移动端 320px。

地图时序补丁：

```js
function resizeVisibleAmap() {
  requestAnimationFrame(() => {
    if (state.page === "s1") state.amap.s1Map?.resize?.();
    if (state.page === "s2") state.amap.s2Map?.resize?.();
  });
}

function syncAmapUi() {
  updateActiveCandidatePanel();
  if (state.page === "s1") ensureS1Map().then(resizeVisibleAmap).catch((err) => writeOutput(err.message));
  if (state.page === "s2") ensureS2Map().then(resizeVisibleAmap).catch((err) => writeOutput(err.message));
}

const amapResizeObserver = "ResizeObserver" in window ? new ResizeObserver(resizeVisibleAmap) : null;
["#s1AmapMap", "#s2AmapMap"].forEach((selector) => {
  const el = $(selector);
  if (el && amapResizeObserver) amapResizeObserver.observe(el);
});
```

把 observer 初始化放在 `bind()` 末尾、第一次 `setControls()` 前后均可，但必须在 DOM 存在后执行。

验证：
- 没有中心点时，`#s1AmapMap` 仍显示 `.map-empty`。
- 填写中心点并生成上下文后，切出 S1 再切回 S1，地图不空白、不挤成细条。
- 点击地图仍写入 `#centerLocation`，不改变 GCJ-02 逻辑。

提交点：`refactor(uploader): move s1 into studio map layout`

## 5. Wave 4：S2 地形页

改动范围：`index.html`、`style.css`，复用 Wave 3 的地图 resize。

S2 结构：
- 顶部薄条保留 `.bucket[data-bucket="topography"]`，宽度 360-420px，不要横跨全屏。
- `#controlPointStaleBanner` 位于上传条下方、主工作区上方。
- 主区使用两列：左列 `minmax(520px,1.25fr)`，右列 `minmax(360px,.75fr)`。
- 左列 `.cad-preview-panel` 保留 `#cadPreviewStatus`、`#cadZoomOut`、`#cadZoomReset`、`#cadZoomIn`、`#runCadPreview`、`#cadPreviewFrame`、`#cadCandidateList`。
- 右列 `.s2-control-panel` 保留 `#s2AmapPanel`、`#s2AmapStatus`、`#s2ActiveCandidate`、`#s2AmapMap`、`#s2AmapHint`、`#controlStatus`、`#controlList`、`#alignmentPanel`、`#saveControlPoints`。
- `#s2AmapMap` 目标高度：桌面 420px；右列总高度允许滚动，不遮挡保存按钮。

验证：
- 生成 CAD 预览后，SVG 在 `#cadPreviewFrame` 内可滚动和缩放。
- 点击候选点“地图拾取”后，右列 `#s2ActiveCandidate` 更新，面板滚到地图区域。
- S1 有中心点时，S2 地图从 S1 中心启动；没有中心点时保留现有错误提示。
- stale banner 的动态按钮仍能绑定 `#generateMigrationReport`、`#archiveControlPoints`。

提交点：`refactor(uploader): move s2 into studio terrain layout`

## 6. Wave 5：状态页和结果归位

改动范围：`index.html`、`style.css`、`app.js`。

状态页结构：
- `section.page[data-page="status"]` 内第一张卡片保留 `#statusGate`、`#runInventoryStatus`、`#runValidateStatus`。
- 把当前 page-shell 末尾的 `.result-panel` 移入状态页，保留 `#resultHint` 和 `#output`。
- 删除 workbench.css 中 `.page[data-page="workbench"].active ~ .result-panel` 的隐藏规则，因为 result panel 不再是 workbench 兄弟节点。

行为：
- `writeOutput()` 不需要改变 DOM 查询；`#output` 仍全局唯一。
- 从 S0 触发检查已经在 Wave 2 跳状态页；状态页按钮保持原地执行。

验证：
- 项目/S0/S1/S2/图纸页面不显示运行结果面板。
- 状态页显示最近一次运行结果。
- `runInventoryStatus`、`runValidateStatus` 输出格式不变。

提交点：`refactor(uploader): scope result panel to status page`

## 7. Wave 6：工作台收口

改动范围：`style.css`、`workbench.css`、必要时 `index.html`。

步骤：
- `.wb3` 从 `height:100vh;width:100vw` 改为填满父页面：`height:100%; width:100%; min-height:0;`。
- `section.page[data-page="workbench"]` 和 `.studio-pages` 在 active workbench 时不能额外 padding：使用页面级类或 CSS 选择器：

```css
.studio-pages:has(.page[data-page="workbench"].active) { padding:0; overflow:hidden; }
.page[data-page="workbench"] { height:100%; min-height:0; }
.page[data-page="workbench"].active { display:block; }
.page[data-page="workbench"] .wb3 { height:100%; width:100%; }
```

如果不想依赖 `:has()`，在 `setControls()` 中给 `.studio-pages` 切类：

```js
$(".studio-pages")?.classList.toggle("workbench-active", state.page === "workbench");
```

并用 `.studio-pages.workbench-active` 写样式。

- 保留 `#wbHome` 事件：`$("#wbHome")?.addEventListener("click", () => setPage("project"));`
- 不改 `workbench.js` 的绘图、保存、task_pack、缩放、弧线、图例逻辑。

验证：
- 图纸页出现两级左栏：全局页级栏 + 工作台图纸类型栏。
- `#drawingTabs` 图纸类型切换仍能切功能分区/交通分析/待设计项。
- 800% zoom、Ctrl+滚轮、保存草图、检查器折叠、底图 popover 都维持现状。

提交点：`refactor(workbench): nest studio v3 in global shell`

## 8. id 和事件保留清单

全局导航：
- `#tabProject`、`#tabS0`、`#tabS1`、`#tabS2`、`#tabWorkbench`、`#tabStatus`：必须仍是 `[data-page].stage-tab`，因为 `setControls()` 和 `bind()` 依赖选择器。
- `#activeProject`：移入全局 topbar，供 `setControls()` 写入当前项目。

项目页：
- `#refreshProjects`、`#projectCode`、`#projectName`、`#projectType`、`#createProject`、`#projectHint`、`#projectList`。

S0：
- `#s0Hint`、`#gateStatus`、`#runInventory`、`#runValidate`。
- `.bucket[data-bucket="briefing"]`、`location_map`、`site_photo`、`chat`、`reference`。

S1：
- `#amapStatus`、`#centerLocation`、`#checkAmap`、`#saveCenter`、`#s1AmapPanel`、`#s1AmapStatus`、`#s1AmapMap`、`#s1AmapHint`。
- `.bucket[data-bucket="location_map"]` 可在 S0 和 S1 同时存在；现有 `querySelectorAll(".bucket")` 支持多个同 bucket。

S2：
- `.bucket[data-bucket="topography"]`。
- `#controlPointStaleBanner`、`#cadPreviewStatus`、`#cadZoomOut`、`#cadZoomReset`、`#cadZoomIn`、`#runCadPreview`、`#cadPreviewFrame`、`#cadCandidateList`。
- `#s2AmapPanel`、`#s2AmapStatus`、`#s2ActiveCandidate`、`#s2AmapMap`、`#s2AmapHint`、`#controlStatus`、`#controlList`、`#alignmentPanel`、`#saveControlPoints`。

工作台：
- `#drawingWorkbench`、`#wbHome`、`#drawingTabs`、`#drawingType`、`#toggleBasePanel`、`#basePanel`、`#baseImagePath`、`#baseImageFile`、`#uploadBaseImage`。
- `#wbCrumb`、`#drawingWorkspaceTitle`、`#drawingWorkspaceState`、`#workbenchLoad`、`#workbenchSave`、`#toggleInspector`、`#workbenchLayout`。
- `#workbenchCanvas`、`#workbenchStage`、`#baseImage`、`#sketchOverlay`、`#workbenchEmpty`、`#canvasZoomOut`、`#canvasZoomReset`、`#canvasZoomIn`。
- `#finishObject`、`#undoPoint`、`#redoAction`、`#deleteObject`、`#clearDraft`、`#workbenchStatus`、`#workbenchInspector`、`#drawingSpecificTools`、`#zoneLegendPreview`、`#objectList`。
- `#taskUserNotes`、`#taskPackStatus`、`#svgDraftStatus`、`#svgDraftPreview`、`#exportDrawing`、`#sendToAgent`。
- 隐藏依赖：`#styleStrip`、`#drawingWorkspaceDescription`、`#plannedWorkspace`、`#plannedTitle`、`#plannedDescription`、`#dirtyDialog`、`#dirtyDialogTitle`、`#dirtySaveSwitch`、`#dirtyDiscardSwitch`、`#dirtyCancelSwitch`。

状态：
- `#statusGate`、`#runInventoryStatus`、`#runValidateStatus`、`#resultHint`、`#output`。

## 9. 总体验证清单

每个 wave 后：
- `node --check _tools/uploader/static/app.js`
- `python _tools/validate_record.py 26-BQ-PARK`
- `git status --short`，确认没有 stage 运行产物，没有删除用户未跟踪文件。

最终浏览器自验：
- 1366x768：项目、S0、S1、S2、图纸、状态 6 页都无横向页面溢出；左栏固定，顶栏固定。
- 390x844：左栏变窄或保持 52-64px，页面内容单列，按钮文字不溢出。
- S1：输入已有中心点，地图出现；切到项目再切回 S1，地图 resize 正常。
- S2：生成 CAD 预览后，候选点列表和地图拾取都能操作；右列保存按钮可见。
- 图纸：加载底图、画点、完成分区、撤销、800% zoom、检查器折叠、底图 popover、保存草图全部可用。
- 状态：从 S0 点击 Inventory 后跳状态页并显示 `#output`；状态页按钮直接更新同一个结果面板。

## 10. 禁止事项

- 不要改 `_schema/`、`skills/`、`projects/*/05_output/record.md`、validator 或 agent 协议。
- 不要重写高德地图、CAD 预览、控制点配准或工作台绘图逻辑。
- 不要删除或重命名任何现有 id。
- 不要为了“顺手清理”删除旧 CSS，除非该规则明确只服务 `body.workbench-mode` 或已迁移到状态页的 result-panel 隐藏。
- 不要提交运行生成物；尤其保留用户现有未跟踪/未提交项目输出，由用户决定是否清理。

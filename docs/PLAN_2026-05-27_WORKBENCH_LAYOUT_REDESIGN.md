# 设计方案：图纸工作台 UI 排版重做

作者：mac claude（核心交互/布局规范）
日期：2026-05-27
对象：`_tools/uploader/static/index.html`（workbench 页 DOM）+ `workbench.css`
原型：`docs/prototypes/workbench_layout_v2.html`（可在浏览器直接打开）

---

## 1. 现状的 3 个问题

1. **左侧一列堆太多**：`aside.workbench-side`（index.html 322-342）把"风格工具 + 绘图按钮 + 给 agent 说明 + 发给 agent/导出 + task 状态 + 对象列表"全竖排一列 → 拥挤、长滚动。
2. **空白多 / 画布没当主角**：画布面板右侧偏窄、下方常驻一个多数时候为空的"当前 SVG 草稿"预览（363-365），整体留白浪费，画布这个核心区反而不突出。
3. **底部"运行结果"不该出现在工作台**：`section.result-panel`（401-407）挂在所有 `.page` 之外、属于 `page-shell` 公共区，所以**每个页面底部都显示它**；它其实只服务 Status 页的 Inventory/校验命令输出，工作台显示纯属串台。

---

## 2. 新布局：顶栏 + 三区 + 可折叠底部工作流（画布为主角）

```
┌ TOP BAR ───────────────────────────────────────────────────────────────┐
│ [图纸工作台/标题]  [tab:功能分区|交通分析|…]      [状态徽章] [加载图纸][保存草图] │
├ 264px ───────┬──────────── 1fr（画布，主角）───────────┬──── 300px ───────┤
│ 左栏「怎么画」 │  ┌ 画布内浮动缩放条 ────────────────┐    │ 右栏「画了什么」   │
│ ▸ 风格         │  │  Ctrl+滚轮  [−][100%][+][适合宽度] │    │ ▸ 图例预览(按样式) │
│   调色板/最近  │  │                                  │    │   色块+xN+隐形提示  │
│   填充/边框/线宽│  │      底图 + sketch overlay         │    │ ▸ 对象明细(列表)   │
│ ▸ 绘图操作      │  │      （顶点/弧线圆点）             │    │   选中高亮/删除     │
│   完成/撤销/重做│  │                                  │    │ (可选)选中属性     │
│   删除/清空     │  └──────────────────────────────────┘    │                  │
│   快捷键提示     │                                          │                  │
├──────────────┴──────────────────────────────────────────┴──────────────┤
│ FOOTER「出图工作流」(可折叠) ▸ [给 agent 说明…] [查看SVG草稿][导出][发给agent出图] │
└─────────────────────────────────────────────────────────────────────────┘
```

CSS 用 `display:flex;flex-direction:column` 外层 + `body` 区 `display:grid;grid-template-columns:264px 1fr 300px`。整页 `height:100vh`，画布列 `1fr` 吃掉所有剩余宽高 → 画布最大化、留白消失。

### 顶栏（替代散落的 page-head + tabs + toolbar）
- 左：`图纸工作台 / 功能分区工作台` 标题；drawing-type tabs（功能分区/交通分析/待设计灰显）。
- 右：状态徽章（可编辑 · 已批准风格）；`加载图纸`、`保存草图`。
- **底图路径/上传底图**从主区移走：放进顶栏一个「底图」弹出小面板，或并入底部工作流的"设置"区（绘图时不常用，不该占主区）。

### 左栏「怎么画」（约 264px）
- **风格卡**：调色板（来自 style_spec）、最近用色、填充/实线/虚线/无边框 chips、线宽滑杆。即现 `drawingSpecificTools` 内容，整理进一张卡。
- **绘图操作卡**：完成分区/撤销/重做/删除选中/清空草图（现 `workbench-actions` 第一组）+ 快捷键提示一行。

### 中区「画布」（1fr，主角）
- 画布填满；缩放条改为**画布内顶部浮动条**（不再单占一行），含 `Ctrl+滚轮` 提示。
- `workbench-status` 文案改为画布角落轻提示或并入顶栏状态徽章，不单占一行。

### 右栏「画了什么」（约 300px）
- **图例预览卡**：按 `style_hints` 合并的分组（色块 + 组名 + `xN`）+ 底部"有 N 个不可见对象"轻提示。即现 `zoneLegendPreview`。
- **对象明细卡**：对象列表（现 `objectList`），可滚动，选中高亮、删除。
- （可选，后续）选中对象的属性快捷区。

### 底部「出图工作流」（可折叠，绘图时不占地方）
- 把 **给 agent 说明 textarea + 发给 agent 出图 + 导出 PNG/PDF + task_pack 状态 + 查看 SVG 草稿** 收进一条可折叠 footer。
- **"当前 SVG 草稿"预览**（现 `svg-draft-panel` 常驻）改为**点"查看 SVG 草稿"按钮才展开**的抽屉/弹层——它在 agent 出图前是空的，不该常驻占地。

### 去掉"运行结果"
- `result-panel` 不在 workbench 页显示。做法二选一（推荐前者）：
  1. 把 `result-panel` 从 `page-shell` 公共区**移进各命令页内部**（Status/项目页），workbench 页不含它；
  2. 或保留公共区，但 workbench 激活时 `result-panel` 设 `hidden`（JS 在切到 workbench 页时隐藏）。
- 优先 #1（结构上归位，最干净）。注意 `#output`/`#resultHint` 仍被 app.js 的命令逻辑引用，移动 DOM 时**保留这些 id**，只改放置位置，别删元素（避免 JS 取不到报错）。

---

## 3. 响应式

- 宽 < ~1100px：右栏可折叠为图标/抽屉；画布优先保宽。
- 宽 < ~860px：左右栏都改为顶部可切换的抽屉，画布全宽。
- 画布列始终 `min-height:0` + `overflow` 正确，避免 grid 子项撑破。

---

## 4. 实施边界（重要）

- **本次是纯前端布局/CSS 重排**，不改绘图逻辑、不改 schema、不改 agent 协议。
- **保留所有现有元素 id 和事件绑定**：`#workbenchCanvas`、`#workbenchStage`、`#sketchOverlay`、`#baseImage`、`#objectList`、`#zoneLegendPreview`、`#drawingSpecificTools`、`#taskUserNotes`、`#sendToAgent`、`#exportDrawing`、`#svgDraftPreview`、`#output`、`#resultHint`、所有 `#canvasZoom*`、`#finishObject`/`#undoPoint`/… 一个都不能少（app.js / workbench.js 靠 id 取元素）。只移动它们的**位置/容器**和样式，不改 id、不删元素。
- **画布二层结构不变**：`#workbenchStage.style.width` 百分比缩放、`preserveAspectRatio="none"`、handle 屏幕恒定那套都不动。
- 重排后必跑：`node --check workbench.js`、`validate_record 26-BQ-PARK`、并人工核对加载/保存/缩放/绘制/图例/对象选择/发给 agent 全链路不回退。

## 5. 红线

- ❌ 不动绘图/弧线/schema/协议逻辑（本次只排版）
- ❌ 不删除或重命名现有 id；不删 `#output`/`result-panel` 元素（只归位）
- ❌ 不碰 `agent_drawing_protocol.md`
- ❌ 不 stage 运行产物；不删用户未跟踪文件

## 6. 交付

- 原型 `docs/prototypes/workbench_layout_v2.html` 为视觉与结构基准。Windows claude 按它把 `index.html` 的 workbench 页 DOM 重排 + `workbench.css` 调样式，保持 id/事件不变。
- 完成后回推 diff + 截图，由 mac claude 核验布局与"无功能回退"。

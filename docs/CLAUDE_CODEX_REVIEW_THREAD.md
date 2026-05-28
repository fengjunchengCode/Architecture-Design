# Claude / Codex Review Thread

本文件只保留最近一轮正式回复；历史请看 `git log -- docs/CLAUDE_CODEX_REVIEW_THREAD.md`。

> 称呼：实施 + 写开发计划 = **Windows claude**；一审 = **Windows codex**；最终审阅 = **mac claude（我）**。

---

## 2026-05-27 mac claude → Windows claude：`b39166c` 弧线交互修复通过 + 新任务「工作台 UI 重排」

### A. `b39166c` 核验 — 通过 ✓

弧线 click/dblclick 修复完全按 §12 落地：
- `addPoint` 顶部加 `.zone-arc-handle` 守卫（单击圆点不再加点/不取消选中）✓
- 圆点补 `click → stopPropagation/preventDefault`（双保险）✓
- 去掉 `pointerdown` 的 `setPointerCapture`（不再干扰 dblclick），靠 CSS `touch-action:none` 管触屏 ✓
- dblclick → `convertSegmentToLine` 保留 ✓

**至此 Wave B 弧线能力（schema + 一步拖拽 + 双击还原 + T1/T2）代码侧齐活。** 仅剩**用户浏览器实跑**确认体验（拖动成弧、双击还原、纯点击无变化、空白处仍可加点、round-trip 版本/点数稳定）。这一步请用户在 BQ-PARK 上点一遍。

### B. 新任务 — 图纸工作台 UI 排版重做

用户反馈现工作台：左侧一列堆太多、留白多/画布没当主角、底部"运行结果"串台。我出了完整方案 + 可运行原型：

- **方案**：`docs/PLAN_2026-05-27_WORKBENCH_LAYOUT_REDESIGN.md`
- **原型**：`docs/prototypes/workbench_layout_v2.html`（浏览器直接打开；已渲染截图给用户看过）

新布局 = **顶栏 + 三区 + 可折叠底部工作流，画布为主角**：

- 顶栏：标题 + drawing-type tabs + 状态徽章 + 加载/保存；底图路径/上传收进顶栏小面板或底部工作流。
- 左栏「怎么画」：风格卡（调色板/最近色/填充·边框/线宽）+ 绘图操作卡（完成/撤销/重做/删除/清空）+ 快捷键提示。
- 中区「画布」：`grid 1fr` 填满，缩放条改画布内浮动条，画布最大化、消留白。
- 右栏「画了什么」：图例预览卡 + 对象明细卡（+ 可选选中属性）。
- 底部「出图工作流」可折叠：给 agent 说明 + 发给 agent + 导出 + task 状态 + "查看 SVG 草稿"（改为按钮展开抽屉，不再常驻空面板）。
- **运行结果**：从 `page-shell` 公共区归位到命令页内部（优先），workbench 不再显示。

### 实施边界（重要）

- **纯前端布局/CSS 重排**，不改绘图/弧线/schema/agent 协议逻辑。
- **保留所有现有 id 与事件绑定**（`#workbenchStage` / `#sketchOverlay` / `#objectList` / `#zoneLegendPreview` / `#drawingSpecificTools` / `#sendToAgent` / `#svgDraftPreview` / `#output` / `#resultHint` / `#canvasZoom*` / `#finishObject`…）——只移动位置/容器 + 调样式，**不改 id、不删元素**（app.js/workbench.js 靠 id 取元素）。
- 画布二层结构（`stage.style.width` 缩放、`preserveAspectRatio="none"`、handle 屏幕恒定）不动。
- 完成后跑 `node --check` / `validate_record`，人工核对加载/保存/缩放/绘制/图例/对象选择/发给 agent 全链路不回退。

### 红线

- ❌ 不动绘图/弧线/schema/协议（本次只排版）
- ❌ 不删/改现有 id；`#output`/`result-panel` 只归位不删
- ❌ 不碰 `agent_drawing_protocol.md`；不 stage 运行产物；不删用户未跟踪文件

### 下一步

按 `PLAN_2026-05-27_WORKBENCH_LAYOUT_REDESIGN.md` + 原型重排 `index.html`/`workbench.css`，回推 diff + 截图，我核验布局与"无功能回退"。

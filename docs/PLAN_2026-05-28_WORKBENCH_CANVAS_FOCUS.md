# 工作台「画布为主角」v3 实施计划

> **实施分工：** 本计划由 mac claude 编写，**Windows claude 按任务逐条实施并提交**，Windows codex 一审，mac claude 终审。步骤用 `- [ ]` 勾选跟踪。纯前端，不碰绘图/弧线/schema/agent 协议逻辑。
>
> **本计划取代** `83cc46e` 审查里「3 处可见性回退」的独立修复请求——把那 3 处（status 反馈、底图上传入口、风格态）并入本轮一次实现，避免重复改顶栏导致冲突。

**目标：** 让画布拿到最大可用空间——侧栏可折叠、缩放上限提到 800%、修复缩放工具栏被挤变形，并把上一轮被隐藏的 3 个功能元素以「不占画布」的方式重新暴露。

**架构：** 顶栏新增「工具栏/图例」两个折叠开关 + 「底图」弹出面板；三栏 grid 用 CSS 变量驱动列宽，折叠时画布列 `1fr` 自动吃掉侧栏宽度；操作反馈改为画布角落浮动 toast；风格态并入顶栏徽章。全部是「移动已有元素 + 加样式/开关」，不删 id、不动绘图逻辑。

**技术栈：** 原生 HTML/CSS/JS（`_tools/uploader/static/`），无构建步骤；校验用 `node --check` + 浏览器实跑。

---

## 受影响文件

| 文件 | 职责 | 本轮改动 |
|---|---|---|
| `_tools/uploader/static/workbench/workbench.js` | 工作台前端逻辑 | 缩放常量/按钮步进、setStatus toast、徽章风格态、栏折叠开关绑定、底图面板开关 |
| `_tools/uploader/static/workbench/workbench.css` | 工作台样式 | 缩放工具栏按钮尺寸、变量驱动三栏、折叠规则、toast/popover/iconbtn 样式、响应式 |
| `_tools/uploader/static/index.html`（workbench 页 283-374） | 工作台 DOM | 顶栏加开关+底图面板、status 移进画布做 toast、底图输入组从隐藏块搬进 popover |

**不动：** `schema.py`、`agent_drawing_protocol.md`、`app.js`、`traffic_analysis`、绘图/弧线/撤销逻辑、画布二层结构（`stage.style.width` 缩放 / `preserveAspectRatio="none"` / handle 屏幕恒定）。

**核心约束：** 所有现有 id 一个不删不改。本轮只「搬家 + 加样式 + 加开关」。新增 id 允许：`toggleLeftRail` / `toggleRightRail` / `toggleBasePanel` / `basePanel`。

---

## Task 1：缩放上限提到 800% + 按钮平滑步进

**Files:**
- Modify: `_tools/uploader/static/workbench/workbench.js:38-41`（常量）
- Modify: `_tools/uploader/static/workbench/workbench.js:1966-1969`（按钮绑定）

- [ ] **Step 1: 抬高上限常量**

把 `workbench.js:38-41`：

```js
  const CANVAS_ZOOM_MIN = 0.5;
  const CANVAS_ZOOM_MAX = 4;
  const CANVAS_ZOOM_STEP = 0.25;
  const CANVAS_WHEEL_ZOOM_FACTOR = 1.1;
```

改为：

```js
  const CANVAS_ZOOM_MIN = 0.5;
  const CANVAS_ZOOM_MAX = 8;
  const CANVAS_BUTTON_ZOOM_FACTOR = 1.25;
  const CANVAS_WHEEL_ZOOM_FACTOR = 1.1;
```

（删掉只被加法步进用的 `CANVAS_ZOOM_STEP`，改成乘法因子 `CANVAS_BUTTON_ZOOM_FACTOR`，否则 100%→800% 要点 28 下。）

- [ ] **Step 2: 按钮改乘法步进 + 修「适合宽度」语义**

把 `workbench.js:1966-1969`：

```js
    $("#canvasZoomOut").addEventListener("click", () => adjustCanvasZoom(-CANVAS_ZOOM_STEP));
    $("#canvasZoomReset").addEventListener("click", () => setCanvasZoom(1));
    $("#canvasZoomIn").addEventListener("click", () => adjustCanvasZoom(CANVAS_ZOOM_STEP));
    $("#canvasZoomFit").addEventListener("click", () => setCanvasZoom(1));
```

改为：

```js
    $("#canvasZoomOut").addEventListener("click", () => setCanvasZoom(state.canvasZoom / CANVAS_BUTTON_ZOOM_FACTOR));
    $("#canvasZoomReset").addEventListener("click", () => setCanvasZoom(1));
    $("#canvasZoomIn").addEventListener("click", () => setCanvasZoom(state.canvasZoom * CANVAS_BUTTON_ZOOM_FACTOR));
    $("#canvasZoomFit").addEventListener("click", () => setCanvasZoom(1));
```

（`adjustCanvasZoom` 此后无人调用，可一并删除其定义 `workbench.js:840-842`；删之前先 `grep -n adjustCanvasZoom` 确认只剩定义本身。）

- [ ] **Step 3: 校验语法**

Run: `node --check _tools/uploader/static/workbench/workbench.js`
Expected: 无输出（通过）

- [ ] **Step 4: 浏览器验证**

打开 `page=workbench&drawing=functional_zoning`，连点 `+`：缩放可一路升到 `800%`，`100%` 数字标签同步；连点 `−` 回到 `50%`；Ctrl+滚轮在 50%-800% 间平滑。

- [ ] **Step 5: 提交**

```bash
git add _tools/uploader/static/workbench/workbench.js
git commit -m "feat(workbench): raise zoom ceiling to 800% with multiplicative button steps"
```

---

## Task 2：修复缩放工具栏被挤变形

**根因：** `workbench.css:183` `.canvas-toolbar button { width: 30px }` 对所有按钮固定 30px，但 `100%`、`适合宽度` 是文字按钮 → 文字溢出/换行变形。

**Files:**
- Modify: `_tools/uploader/static/index.html:323-326`（给 `−`/`+` 加区分 class）
- Modify: `_tools/uploader/static/workbench/workbench.css:160-191`（工具栏与按钮尺寸）

- [ ] **Step 1: 给步进按钮加 class（不改 id）**

把 `index.html:321-327` 的工具条：

```html
                  <div class="canvas-toolbar" aria-label="画布缩放">
                    <small class="canvas-zoom-hint">Ctrl + 滚轮缩放</small>
                    <button id="canvasZoomOut" type="button">−</button>
                    <button id="canvasZoomReset" type="button">100%</button>
                    <button id="canvasZoomIn" type="button">+</button>
                    <button id="canvasZoomFit" type="button">适合宽度</button>
                  </div>
```

改为（仅加 `class="zoom-step"` 到 `−`/`+`，id 不变）：

```html
                  <div class="canvas-toolbar" aria-label="画布缩放">
                    <small class="canvas-zoom-hint">Ctrl + 滚轮</small>
                    <button id="canvasZoomOut" class="zoom-step" type="button">−</button>
                    <button id="canvasZoomReset" type="button">100%</button>
                    <button id="canvasZoomIn" class="zoom-step" type="button">+</button>
                    <button id="canvasZoomFit" type="button">适合宽度</button>
                  </div>
```

- [ ] **Step 2: 工具栏不换行 + 文字按钮自适应宽度**

把 `workbench.css:160-191` 的两段规则：

```css
.canvas-toolbar {
  position: absolute;
  top: 10px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 3;
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(255, 253, 247, 0.92);
  backdrop-filter: blur(6px);
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 5px 8px;
  box-shadow: 0 2px 8px rgba(34, 32, 28, 0.1);
}
```

替换为（加 `white-space:nowrap` + `max-width` 兜底）：

```css
.canvas-toolbar {
  position: absolute;
  top: 10px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 3;
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: nowrap;
  white-space: nowrap;
  max-width: calc(100% - 20px);
  background: rgba(255, 253, 247, 0.92);
  backdrop-filter: blur(6px);
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 5px 8px;
  box-shadow: 0 2px 8px rgba(34, 32, 28, 0.1);
}
```

并把 `.canvas-toolbar button` 的固定宽度规则：

```css
.canvas-toolbar button {
  border: 1px solid var(--line);
  background: var(--panel);
  border-radius: 6px;
  width: 30px;
  height: 26px;
  cursor: pointer;
  font-size: 13px;
  color: var(--ink);
}
```

替换为（文字按钮自适应，仅 `.zoom-step` 保持正方形）：

```css
.canvas-toolbar button {
  border: 1px solid var(--line);
  background: var(--panel);
  border-radius: 6px;
  min-width: 28px;
  height: 26px;
  padding: 0 8px;
  cursor: pointer;
  font-size: 13px;
  color: var(--ink);
  white-space: nowrap;
}

.canvas-toolbar button.zoom-step {
  width: 28px;
  padding: 0;
}
```

- [ ] **Step 3: 浏览器验证（窄画布）**

把右栏展开（画布最窄态），看工具栏药丸：`Ctrl + 滚轮  [−] [100%] [+] [适合宽度]` 一行排开，文字不裁切、不换行、不溢出药丸。缩到 800% 时 `100%` 标签变 `800%` 仍不变形。

- [ ] **Step 4: 提交**

```bash
git add _tools/uploader/static/index.html _tools/uploader/static/workbench/workbench.css
git commit -m "fix(workbench): zoom toolbar text buttons no longer deform (auto width + nowrap)"
```

---

## Task 3：侧栏可折叠，画布吃掉腾出的宽度

**设计：** 顶栏加两个开关 `工具栏`(左) / `图例`(右)，点按折叠/展开对应侧栏；三栏列宽用 CSS 变量驱动，折叠即把该列设 0 并 `display:none` 该栏，画布 `1fr` 自动扩张。**默认右栏折叠**（图例/对象明细是查看信息，绘图时不必常驻），左栏默认展开。

**Files:**
- Modify: `_tools/uploader/static/index.html:287-295`（顶栏加开关）
- Modify: `_tools/uploader/static/workbench/workbench.css:86-92`（变量驱动三栏）
- Modify: `_tools/uploader/static/workbench/workbench.css:834-867`（响应式改用变量）
- Modify: `_tools/uploader/static/workbench/workbench.js`（开关绑定 + 初始态；插在 footer toggle 绑定附近 ~L2018）
- Append: `_tools/uploader/static/workbench/workbench.css`（文件末尾加 `.wb-iconbtn` 样式）

- [ ] **Step 1: 顶栏加两个折叠开关**

把 `index.html:291-292`：

```html
                <span class="wb-spacer"></span>
                <span class="wb-state" id="drawingWorkspaceState">可编辑</span>
```

改为（在 spacer 后、徽章前插入两个开关）：

```html
                <span class="wb-spacer"></span>
                <button id="toggleLeftRail" class="wb-iconbtn" type="button" aria-pressed="true" title="工具栏">⬓ 工具</button>
                <button id="toggleRightRail" class="wb-iconbtn" type="button" aria-pressed="false" title="图例/对象">图例 ⬔</button>
                <span class="wb-state" id="drawingWorkspaceState">可编辑</span>
```

- [ ] **Step 2: 三栏列宽改用 CSS 变量 + 折叠规则**

把 `workbench.css:86-92`：

```css
.workbench-body {
  flex: 1;
  display: grid;
  grid-template-columns: 264px 1fr 300px;
  gap: 10px;
  min-height: 0;
}
```

替换为：

```css
.workbench-body {
  flex: 1;
  display: grid;
  grid-template-columns: var(--wb-left, 264px) 1fr var(--wb-right, 300px);
  gap: 10px;
  min-height: 0;
}

.workbench-body.left-collapsed {
  --wb-left: 0px;
}

.workbench-body.right-collapsed {
  --wb-right: 0px;
}

.workbench-body.left-collapsed .workbench-rail-left,
.workbench-body.right-collapsed .workbench-rail-right {
  display: none;
}
```

- [ ] **Step 3: 响应式断点改用变量（保持小屏自动收栏）**

把 `workbench.css:834-867` 两个 media query：

```css
/* ---------- RESPONSIVE: < 1100px collapse right rail ---------- */
@media (max-width: 1100px) {
  .workbench-body {
    grid-template-columns: 240px 1fr;
  }

  .workbench-rail-right {
    display: none;
  }
}

/* ---------- RESPONSIVE: < 860px collapse both rails ---------- */
@media (max-width: 860px) {
  .drawing-workbench {
    height: auto;
    min-height: calc(100vh - 180px);
  }

  .workbench-body {
    grid-template-columns: 1fr;
  }

  .workbench-rail-left {
    order: 2;
  }

  .workbench-canvas-panel {
    order: 1;
  }

  .workbench-rail-right {
    display: none;
  }
}
```

替换为：

```css
/* ---------- RESPONSIVE: < 1100px force-collapse right rail ---------- */
@media (max-width: 1100px) {
  .workbench-body {
    --wb-right: 0px;
  }

  .workbench-body .workbench-rail-right {
    display: none;
  }
}

/* ---------- RESPONSIVE: < 860px force-collapse both rails ---------- */
@media (max-width: 860px) {
  .drawing-workbench {
    height: auto;
    min-height: calc(100vh - 180px);
  }

  .workbench-body {
    --wb-left: 0px;
    --wb-right: 0px;
  }

  .workbench-body .workbench-rail-left,
  .workbench-body .workbench-rail-right {
    display: none;
  }
}
```

- [ ] **Step 4: `.wb-iconbtn` 样式（追加到 css 文件末尾）**

在 `workbench.css` 末尾追加：

```css
/* ---------- ICON TOGGLE BUTTONS (topbar) ---------- */
.wb-iconbtn {
  border: 1px solid var(--line);
  background: var(--panel);
  color: var(--ink);
  padding: 6px 10px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  white-space: nowrap;
}

.wb-iconbtn:hover {
  border-color: var(--accent);
}

.wb-iconbtn[aria-pressed="true"] {
  background: rgba(31, 111, 91, 0.10);
  border-color: var(--accent);
  color: var(--accent);
}
```

- [ ] **Step 5: 开关绑定 + 初始态（JS）**

在 `workbench.js` 绑定 `#footerToggle` 的同一函数里（约 `L2014-2023`，footer toggle 之后），追加：

```js
    // Rail collapse toggles
    function setRailCollapsed(side, collapsed) {
      const layout = $("#workbenchLayout");
      if (!layout) return;
      layout.classList.toggle(`${side}-collapsed`, collapsed);
      const btn = side === "left" ? $("#toggleLeftRail") : $("#toggleRightRail");
      if (btn) btn.setAttribute("aria-pressed", String(!collapsed));
    }
    $("#toggleLeftRail")?.addEventListener("click", () => {
      setRailCollapsed("left", !$("#workbenchLayout").classList.contains("left-collapsed"));
    });
    $("#toggleRightRail")?.addEventListener("click", () => {
      setRailCollapsed("right", !$("#workbenchLayout").classList.contains("right-collapsed"));
    });
    // Default: left open, right collapsed (give canvas more room on load)
    setRailCollapsed("left", false);
    setRailCollapsed("right", true);
```

- [ ] **Step 6: 校验语法**

Run: `node --check _tools/uploader/static/workbench/workbench.js`
Expected: 无输出（通过）

- [ ] **Step 7: 浏览器验证**

1. 打开工作台：右栏默认收起，画布比之前宽约 300px；顶栏「图例」开关 `aria-pressed=false`（未高亮）。
2. 点「图例」→ 右栏出现（图例预览 + 对象明细），画布相应变窄；按钮高亮。
3. 点「工具」→ 左栏收起，画布再宽约 264px；两栏都收时画布近全宽。
4. 拖窄窗口到 <1100px：右栏自动隐藏；<860px：两栏都隐藏、画布全宽，不破版。

- [ ] **Step 8: 提交**

```bash
git add _tools/uploader/static/index.html _tools/uploader/static/workbench/workbench.css _tools/uploader/static/workbench/workbench.js
git commit -m "feat(workbench): collapsible side rails so canvas reclaims space; right rail collapsed by default"
```

---

## Task 4：把上一轮隐藏的 3 个功能元素以「不占画布」方式重新暴露

> 取代 `83cc46e` 的 3 处修复请求。全部是「把已存在元素从隐藏块搬到可见容器 + 加样式/开关」，id 不变。

### 4a：操作反馈改为画布角落浮动 toast（`#workbenchStatus`）

**Files:**
- Modify: `index.html`（把 `#workbenchStatus` 从隐藏块搬进画布面板）
- Modify: `workbench.css`（toast 样式，追加到末尾）
- Modify: `workbench.js:181-186`（setStatus 显示 + 自动淡出）

- [ ] **Step 1: 把 status 元素搬进画布面板**

在 `index.html:333`（`.workbench-stage` 闭合 `</div>` 之后、`.workbench-canvas` 闭合 `</div>` 之前）——即画布面板内——加：

```html
                    <div class="workbench-status" id="workbenchStatus" role="status" aria-live="polite"></div>
```

放置参照（画布面板片段，334 行 `</div>` 是 `.workbench-canvas` 收尾）：

```html
                  <div class="workbench-canvas" id="workbenchCanvas">
                    <div class="workbench-stage" id="workbenchStage">
                      <img id="baseImage" alt="底图">
                      <svg id="sketchOverlay" viewBox="0 0 1 1" preserveAspectRatio="none"></svg>
                      <div class="workbench-empty" id="workbenchEmpty">请先选择项目，再加载底图。</div>
                    </div>
                  </div>
                  <div class="workbench-status" id="workbenchStatus" role="status" aria-live="polite"></div>
                </main>
```

并从隐藏块 `index.html:368` 删除原来的：

```html
              <div class="workbench-status" id="workbenchStatus" hidden>等待项目和底图加载。</div>
```

（`#workbenchStatus` 全文件仍只有 1 个。）

- [ ] **Step 2: toast 样式（追加到 css 末尾）**

```css
/* ---------- CANVAS STATUS TOAST ---------- */
.workbench-status {
  position: absolute;
  left: 50%;
  bottom: 16px;
  transform: translateX(-50%);
  z-index: 4;
  max-width: 80%;
  padding: 7px 14px;
  border-radius: 999px;
  background: rgba(34, 32, 28, 0.86);
  color: #fff;
  font-size: 12px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.18);
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.25s;
}

.workbench-status.show {
  opacity: 1;
}

.workbench-status.error {
  background: var(--accent-2);
}
```

（`.workbench-status` 锚定在 `position:relative` 的 `.workbench-canvas-panel`，所以浮在画布右下中部，不占布局。）

- [ ] **Step 3: setStatus 显示 + 自动淡出**

把 `workbench.js:181-186`：

```js
  function setStatus(message, ok = true) {
    const el = $("#workbenchStatus");
    if (!el) return;
    el.textContent = message;
    el.style.color = ok ? "var(--muted)" : "var(--accent-2)";
  }
```

替换为：

```js
  let statusToastTimer = null;
  function setStatus(message, ok = true) {
    const el = $("#workbenchStatus");
    if (!el) return;
    el.textContent = message;
    el.classList.toggle("error", !ok);
    el.classList.add("show");
    if (statusToastTimer) clearTimeout(statusToastTimer);
    statusToastTimer = setTimeout(() => el.classList.remove("show"), 2600);
  }
```

- [ ] **Step 4: 验证**

完成一个分区 → 画布右下浮出「已添加：功能区 1」约 2.6s 后淡出；故意点「完成分区」但只画 2 点 → 浮出红色「多边形至少需要 3 个点」。

### 4b：底图上传搬进顶栏「底图」弹出面板

**Files:**
- Modify: `index.html`（顶栏加 `#toggleBasePanel` + `#basePanel`，把底图 3 元素从隐藏块搬进去）
- Modify: `workbench.css`（popover 样式，追加到末尾）
- Modify: `workbench.js`（面板开关绑定，插在 Task 3 Step 5 同一处）

- [ ] **Step 1: 顶栏加底图按钮 + popover，搬入 3 元素**

在 `index.html` 顶栏 Task 3 新增的两个开关之前插入底图面板（即 `<span class="wb-spacer"></span>` 之后、`#toggleLeftRail` 之前）：

```html
                <div class="wb-basepanel">
                  <button id="toggleBasePanel" class="wb-iconbtn" type="button" aria-expanded="false" title="底图设置">底图</button>
                  <div class="wb-popover" id="basePanel" hidden>
                    <label>底图路径<input id="baseImagePath" value="05_output/drawings/base/master_plan.jpg" autocomplete="off"></label>
                    <label>上传底图<input id="baseImageFile" type="file" accept=".jpg,.jpeg,.png"></label>
                    <button id="uploadBaseImage" class="wb-btn">上传底图</button>
                  </div>
                </div>
```

并从隐藏块 `index.html:369-373` 删除整段（这 3 个 id 已搬到上面 popover）：

```html
              <div class="workbench-toolbar" hidden>
                <label><span>底图路径</span><input id="baseImagePath" value="05_output/drawings/base/master_plan.jpg" autocomplete="off"></label>
                <label><span>上传底图</span><input id="baseImageFile" type="file" accept=".jpg,.jpeg,.png"></label>
                <button id="uploadBaseImage">上传底图</button>
              </div>
```

（搬完后 `baseImagePath`/`baseImageFile`/`uploadBaseImage` 全文件各仍只 1 个。）

- [ ] **Step 2: popover 样式（追加到 css 末尾）**

```css
/* ---------- BASE IMAGE POPOVER ---------- */
.wb-basepanel {
  position: relative;
}

.wb-popover {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  z-index: 20;
  width: 280px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  box-shadow: 0 6px 20px rgba(34, 32, 28, 0.16);
}

.wb-popover[hidden] {
  display: none;
}

.wb-popover label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: var(--muted);
}

.wb-popover input {
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 6px 8px;
  font: inherit;
  font-size: 12px;
}
```

- [ ] **Step 3: 面板开关绑定（JS，插在 Task 3 Step 5 的开关绑定之后）**

```js
    // Base image popover
    const basePanelBtn = $("#toggleBasePanel");
    const basePanel = $("#basePanel");
    if (basePanelBtn && basePanel) {
      basePanelBtn.addEventListener("click", (event) => {
        event.stopPropagation();
        const open = basePanel.hidden;
        basePanel.hidden = !open;
        basePanelBtn.setAttribute("aria-expanded", String(open));
      });
      document.addEventListener("click", (event) => {
        if (basePanel.hidden) return;
        if (!basePanel.contains(event.target) && event.target !== basePanelBtn) {
          basePanel.hidden = true;
          basePanelBtn.setAttribute("aria-expanded", "false");
        }
      });
    }
```

- [ ] **Step 4: 验证**

点顶栏「底图」→ 弹出面板含路径输入 + 文件选择 + 上传按钮；选张图点「上传底图」→ 底图加载到画布；点面板外空白 → 面板收起。

### 4c：风格态并入顶栏徽章

**Files:**
- Modify: `workbench.js:430-434`（徽章文案）
- Modify: `workbench.js`（loadStyle 成功后补 `renderWorkspaceMeta()`）

- [ ] **Step 1: 徽章追加风格态**

把 `workbench.js:430-434`：

```js
    if (stateEl) {
      stateEl.className = `eyebrow workspace-state ${config.status}`;
      stateEl.textContent =
        config.status === "enabled" ? (state.dirty ? "有未保存修改" : "可编辑") : "待设计";
    }
```

替换为：

```js
    if (stateEl) {
      stateEl.className = `eyebrow workspace-state ${config.status}`;
      let label = config.status === "enabled" ? (state.dirty ? "有未保存修改" : "可编辑") : "待设计";
      if (config.status === "enabled") {
        const approved = state.styleSpec && state.styleSpec.approved_at;
        label += approved ? " · 已批准风格" : " · 未建立风格";
      }
      stateEl.textContent = label;
    }
```

- [ ] **Step 2: 风格载入后刷新徽章**

在 `loadStyle()` 里 `renderStyleStrip(data)` 调用之后（约 `workbench.js:705`）加一行：

```js
    renderStyleStrip(data);
    renderWorkspaceMeta();
```

（确认 `renderWorkspaceMeta` 在同模块作用域可见——它定义在 `L420`，可直接调用。）

- [ ] **Step 3: 校验语法 + 验证**

Run: `node --check _tools/uploader/static/workbench/workbench.js`
Expected: 通过

浏览器：在 BQ-PARK（已批准风格）打开 → 徽章显示「可编辑 · 已批准风格」；在一个无 style_spec 的项目打开 → 「可编辑 · 未建立风格」。

- [ ] **Step 4: 提交（4a/4b/4c 合并一次）**

```bash
git add _tools/uploader/static/index.html _tools/uploader/static/workbench/workbench.css _tools/uploader/static/workbench/workbench.js
git commit -m "fix(workbench): re-surface status (toast), base-image upload (popover), style state (badge) without eating canvas"
```

---

## 全量回归校验（实施完跑一遍）

- [ ] `node --check _tools/uploader/static/workbench/workbench.js` 通过
- [ ] `python _tools/validate_record.py 26-BQ-PARK` 通过
- [ ] 必保 id 全在（搬家后各 1 份）：
  ```
  grep -c 'id="workbenchStatus"' _tools/uploader/static/index.html   # = 1
  grep -c 'id="uploadBaseImage"' _tools/uploader/static/index.html    # = 1
  grep -c 'id="baseImageFile"' _tools/uploader/static/index.html      # = 1
  ```
- [ ] 全链路无回退：加载图纸 / 保存草图 / 画分区闭合 / 撤销重做 / 删除选中 / 图例预览 / 对象选择 / 发给 agent / 导出 都正常
- [ ] 画布二层结构未受影响：缩放、handle 屏幕恒定、弧线拖拽/双击还原仍正常

## 回推给 mac claude 终审

回推 diff + **5 张截图**：
1. 默认载入（右栏收起、画布变宽、工具栏药丸不变形）
2. 缩放到 800%
3. 「图例」展开后的三栏态
4. 顶栏「底图」popover 展开
5. 完成一个分区时的画布角落 toast + 徽章「· 已批准风格」

## 红线（不变）

- ❌ 不动绘图/弧线/schema/agent 协议逻辑
- ❌ 不删 / 不改任何现有 id（本轮只搬家 + 加开关 + 加样式）
- ❌ 不碰 `agent_drawing_protocol.md`；不 stage 运行产物（semantic JSON / inventory）；不删用户未跟踪文件
- ❌ 不持久化折叠/缩放状态到项目文件（UI 视图态，session 内即可）
- ❌ 不用 `transform: scale()` 做画布缩放

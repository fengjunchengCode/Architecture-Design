# 工作台 Studio v3 全屏重构 实施计划

> **实施分工：** mac claude 写计划 → **Windows claude 逐 Task 实施 + 提交** → Windows codex 一审 → mac claude 终审。步骤用 `- [ ]` 勾选。
>
> **给实施者的关键说明（重要）：** 你（Windows claude）**没有视觉能力，看不懂渲染出来的截图**。本计划不要求你"照着图做"。
> - 所有结构与样式都以**文本形式**给全：原型文件 `docs/prototypes/workbench_layout_v3.html` 是**可读文本**，是视觉基准；本计划把要落进真实文件的代码**整段列出**，你只需**整段替换 / 整段追加 / 按行编辑**，不需要推断外观。
> - 凡是"长什么样"的问题，答案都在下面的代码块里，逐字照搬即可。

**目标：** 把图纸工作台从「1240px 居中 + 顶部横向 tab」改为「全屏 studio：左侧 64px 图标活动栏 + 瘦顶栏 + 画布主角 + 右侧可折叠检查器 + 画布底部浮动操作坞」。仅改工作台页；S0/S1/S2/项目/状态维持现状。

**架构：** 工作台页激活时给 `<body>` 加 `workbench-mode` 类 → CSS 隐藏全局 `.mast` + `.stage-nav`、让 `.shell` 全屏铺满；工作台自带左侧活动栏（图纸类型切换 + 返回阶段 + 底图）。所有现有 id 与事件绑定**一个不删不改**，只是搬进新容器。

**Tech Stack：** 原生 HTML/CSS/JS，无构建。校验 `node --check` + 浏览器实跑。

**范围假设：** 本轮只做工作台（用户选「只做工作台」方案）。S0/S1/S2 统一以后单独立项。若该假设有误请先在 review thread 提出，不要擅自扩面。

---

## 受影响文件

| 文件 | 改动 |
|---|---|
| `docs/prototypes/workbench_layout_v3.html` | 已提交，**视觉基准（可读文本）**，本轮不改 |
| `_tools/uploader/static/index.html` | 整段替换 workbench 页 DOM（Task 2） |
| `_tools/uploader/static/workbench/workbench.css` | 末尾追加 v3 样式块（Task 3）；v2 旧外层类变成死 CSS，本轮不删 |
| `_tools/uploader/static/workbench/workbench.js` | renderDrawingTabs 改竖排；加手风琴/检查器折叠/返回/面包屑；删 canvasZoomFit（Task 4） |
| `_tools/uploader/static/app.js` | body.workbench-mode 开关 + wbHome 返回绑定（Task 1） |
| `_tools/uploader/static/style.css` | workbench-mode 全屏覆盖（Task 1） |

**不动：** `schema.py`、`agent_drawing_protocol.md`、S0/S1/S2/项目/状态页、绘图/弧线/撤销逻辑、画布二层结构、所有 `.zone-*` 内部控件样式与 `renderSpecificTools`/图例/对象列表渲染逻辑。

---

## id 映射表（原型元素 → 真实 id，全部保留）

| 位置 | 真实 id / 类（保留） | 由谁填充 |
|---|---|---|
| 活动栏 图纸类型容器 | `#drawingTabs` | `renderDrawingTabs()`（Task 4 改竖排） |
| 隐藏图纸类型值 | `#drawingType` | 现有 |
| 活动栏 返回按钮 | `#wbHome`（**新增**） | app.js 绑定 setPage("project") |
| 活动栏 底图按钮/弹窗 | `#toggleBasePanel` / `#basePanel` / `#baseImagePath` / `#baseImageFile` / `#uploadBaseImage` | 现有绑定不变 |
| 顶栏 面包屑 | `#wbCrumb`（**新增**） | Task 4 在 renderWorkspaceMeta 写项目名 |
| 顶栏 标题 | `#drawingWorkspaceTitle` | 现有 |
| 顶栏 状态徽章 | `#drawingWorkspaceState`（class `workspace-state`） | 现有 |
| 顶栏 加载/保存 | `#workbenchLoad` / `#workbenchSave` | 现有 |
| 顶栏 检查器开关 | `#toggleInspector`（**新增**） | Task 4 绑定 |
| 画布视口/舞台/底图/overlay/空态 | `#workbenchCanvas` / `#workbenchStage` / `#baseImage` / `#sketchOverlay` / `#workbenchEmpty` | 现有 |
| 缩放 | `#canvasZoomOut` / `#canvasZoomReset` / `#canvasZoomIn` | 现有（`#canvasZoomFit` **删除**） |
| 操作坞 | `#finishObject` / `#undoPoint` / `#redoAction` / `#deleteObject` / `#clearDraft` | 现有 |
| 状态 toast | `#workbenchStatus` | 现有（setStatus 已改 toast） |
| 检查器 风格 | `#drawingSpecificTools` | `renderSpecificTools()` |
| 检查器 图例 | `#zoneLegendPreview` | `refreshLegendPreview()` |
| 检查器 对象明细 | `#objectList`（class `object-list`） | 现有 |
| 检查器 出图工作流 | `#taskUserNotes` / `#taskPackStatus` / `#svgDraftStatus` / `#svgDraftPreview` / `#exportDrawing` / `#sendToAgent` | 现有 |
| 折叠根容器 | `#workbenchLayout` | renderAvailability 切 hidden |
| 隐藏依赖 | `#styleStrip` / `#drawingWorkspaceDescription` / `#plannedWorkspace`(+`#plannedTitle`/`#plannedDescription`) / `#dirtyDialog`(+内部按钮) | 现有 |

---

## Task 1：全屏铺满（workbench-mode）

**Files:**
- Modify: `_tools/uploader/static/app.js:841` 附近（setControls 里加 body 类切换）
- Modify: `_tools/uploader/static/app.js:1479-1514` 附近（init 绑定区，加 wbHome）
- Append: `_tools/uploader/static/style.css` 末尾（workbench-mode 覆盖规则）

- [ ] **Step 1: setControls 切 body.workbench-mode**

在 `app.js` 的 `setControls()` 里，`document.querySelectorAll(".page").forEach(...)`（约 L841）之后加一行：

```js
  document.body.classList.toggle("workbench-mode", state.page === "workbench");
```

- [ ] **Step 2: 绑定 wbHome 返回阶段**

在 `app.js` init 绑定区（约 L1479 起的一串 `$("#...").addEventListener` 中）任选一处加：

```js
  $("#wbHome")?.addEventListener("click", () => setPage("project"));
```

- [ ] **Step 3: style.css 追加全屏覆盖**

在 `style.css` **末尾**追加：

```css
/* ===== WORKBENCH STUDIO MODE: full-bleed ===== */
body.workbench-mode{overflow:hidden}
body.workbench-mode .mast,
body.workbench-mode .stage-nav{display:none}
body.workbench-mode .shell{
  width:100vw;max-width:none;margin:0;padding:0;
}
body.workbench-mode .workspace{display:block;margin:0;gap:0}
body.workbench-mode .page-shell{margin:0;padding:0;border:0;background:none}
body.workbench-mode .page[data-page="workbench"]{margin:0;padding:0}
body.workbench-mode .result-panel{display:none}
```

- [ ] **Step 4: 校验**

Run: `node --check _tools/uploader/static/app.js`
Expected: 通过。（此步浏览器效果要等 Task 2/3 完成后才完整，先确保 JS 不报错。）

- [ ] **Step 5: 提交**

```bash
git add _tools/uploader/static/app.js _tools/uploader/static/style.css
git commit -m "feat(workbench): full-bleed workbench-mode (hide global shell chrome) + home nav"
```

---

## Task 2：整段替换 workbench 页 DOM

**Files:**
- Modify: `_tools/uploader/static/index.html`（`<section class="page" data-page="workbench">` 整段，当前约 283-395 行）

- [ ] **Step 1: 用下面整段替换 workbench 页**

把 `index.html` 中从 `<section class="page" data-page="workbench">` 到它对应的 `</section>`（v2 版整块）**整段替换**为：

```html
          <section class="page" data-page="workbench">
            <div class="wb3" id="drawingWorkbench">

              <!-- LEFT ACTIVITY RAIL -->
              <nav class="wb3-act">
                <button class="wb3-logo" id="wbHome" type="button" title="返回阶段">建</button>
                <div class="wb3-act-scroll" id="drawingTabs" role="tablist" aria-label="技术图纸类型"></div>
                <input id="drawingType" type="hidden" value="functional_zoning">
                <div class="wb3-act-sep"></div>
                <div class="wb3-basewrap">
                  <button class="wb3-act-btn" id="toggleBasePanel" type="button" aria-expanded="false" title="底图设置">▦</button>
                  <div class="wb3-pop" id="basePanel" hidden>
                    <h5>底图设置</h5>
                    <label>底图路径<input id="baseImagePath" type="text" value="05_output/drawings/base/master_plan.jpg" autocomplete="off"></label>
                    <label>上传底图<input id="baseImageFile" type="file" accept=".jpg,.jpeg,.png"></label>
                    <button id="uploadBaseImage" class="wb3-btn">上传底图</button>
                  </div>
                </div>
              </nav>

              <!-- MAIN -->
              <div class="wb3-main">
                <header class="wb3-top">
                  <div class="wb3-title">
                    <span class="crumb" id="wbCrumb">未选择项目</span>
                    <b><span id="drawingWorkspaceTitle">功能分区工作台</span> <span class="wb3-badge workspace-state enabled" id="drawingWorkspaceState">可编辑</span></b>
                  </div>
                  <span class="wb3-spacer"></span>
                  <button class="wb3-btn" id="workbenchLoad" type="button">加载图纸</button>
                  <button class="wb3-btn primary" id="workbenchSave" type="button">保存草图</button>
                  <span class="wb3-topdiv"></span>
                  <button class="wb3-btn wb3-iconbtn on" id="toggleInspector" type="button" title="检查器面板">▭</button>
                </header>

                <div class="wb3-work" id="workbenchLayout">

                  <!-- CANVAS -->
                  <div class="wb3-stage-wrap">
                    <div class="workbench-canvas" id="workbenchCanvas">
                      <div class="workbench-stage" id="workbenchStage">
                        <img id="baseImage" alt="底图">
                        <svg id="sketchOverlay" viewBox="0 0 1 1" preserveAspectRatio="none"></svg>
                        <div class="workbench-empty" id="workbenchEmpty">请先选择项目，再加载底图。</div>
                      </div>
                    </div>
                    <div class="wb3-zoom">
                      <button id="canvasZoomOut" type="button">−</button>
                      <button class="wb3-zoomval" id="canvasZoomReset" type="button">100%</button>
                      <button id="canvasZoomIn" type="button">+</button>
                      <span class="wb3-zoomhint">Ctrl+滚轮</span>
                    </div>
                    <div class="wb3-dock">
                      <button class="key" id="finishObject" type="button">完成分区</button>
                      <span class="wb3-dockdiv"></span>
                      <button id="undoPoint" type="button">撤销</button>
                      <button id="redoAction" type="button">重做</button>
                      <span class="wb3-dockdiv"></span>
                      <button id="deleteObject" type="button">删除选中</button>
                      <button id="clearDraft" type="button">清空草图</button>
                    </div>
                    <div class="workbench-status" id="workbenchStatus" role="status" aria-live="polite"></div>
                  </div>

                  <!-- RIGHT INSPECTOR -->
                  <aside class="wb3-insp" id="workbenchInspector">
                    <div class="wb3-insp-head"><span>检查器</span></div>
                    <div class="wb3-insp-body">

                      <section class="wb3-sect open" data-sect="style">
                        <button class="wb3-sect-h" type="button"><b>风格 <span class="tag">作用于新建/选中</span></b><span class="chev">▸</span></button>
                        <div class="wb3-sect-c"><div class="drawing-specific-tools" id="drawingSpecificTools"></div></div>
                      </section>

                      <section class="wb3-sect open" data-sect="legend">
                        <button class="wb3-sect-h" type="button"><b>图例预览 <span class="tag">按样式合并</span></b><span class="chev">▸</span></button>
                        <div class="wb3-sect-c"><div id="zoneLegendPreview"></div></div>
                      </section>

                      <section class="wb3-sect open" data-sect="objects">
                        <button class="wb3-sect-h" type="button"><b>对象明细</b><span class="chev">▸</span></button>
                        <div class="wb3-sect-c"><div id="objectList" class="object-list"></div></div>
                      </section>

                      <section class="wb3-sect" data-sect="export">
                        <button class="wb3-sect-h" type="button"><b>出图工作流</b><span class="chev">▸</span></button>
                        <div class="wb3-sect-c">
                          <textarea id="taskUserNotes" rows="2" placeholder="给 agent 的说明：如『橙色箭头=车行流线，绿色=活动草坪』"></textarea>
                          <div class="wb3-flowrow">
                            <span class="wb3-flowstat" id="taskPackStatus">尚未生成 task_pack。</span>
                            <span class="wb3-flowstat" id="svgDraftStatus">等待 agent 生成。</span>
                          </div>
                          <object id="svgDraftPreview" type="image/svg+xml" data="" hidden></object>
                          <div class="wb3-flowbtns">
                            <button id="exportDrawing" class="wb3-btn" disabled>导出 PNG/PDF</button>
                            <button id="sendToAgent" class="wb3-btn primary">发给 agent 出图</button>
                          </div>
                        </div>
                      </section>

                    </div>
                  </aside>
                </div>
              </div>

              <!-- hidden elements JS depends on -->
              <div class="style-strip" id="styleStrip" hidden>当前风格：未加载</div>
              <p class="eyebrow" id="drawingWorkspaceDescription" hidden>标注功能区边界、名称和必要标签。</p>
              <div class="planned-workspace" id="plannedWorkspace" hidden>
                <b id="plannedTitle">该图纸工作台待设计</b>
                <p id="plannedDescription">请在对话中定义该图纸的对象类型、输入方式和输出目标后再启用。</p>
              </div>
              <div class="dirty-dialog" id="dirtyDialog" hidden role="dialog" aria-modal="true" aria-labelledby="dirtyDialogTitle">
                <div class="dirty-dialog-panel">
                  <b id="dirtyDialogTitle">当前图纸有未保存修改</b>
                  <p>切换图纸前，请选择如何处理当前草图。未完成的点位不会进入保存文件。</p>
                  <div class="dirty-dialog-actions">
                    <button id="dirtySaveSwitch" class="primary">保存并切换</button>
                    <button id="dirtyDiscardSwitch">丢弃并切换</button>
                    <button id="dirtyCancelSwitch">取消</button>
                  </div>
                </div>
              </div>
            </div>
          </section>
```

> 注意：v2 里被隐藏的 `.workbench-toolbar`（底图旧块）整段删除——底图三件套已搬进上面 `#basePanel`。`#drawingType` 隐藏 input 已在活动栏内。`#canvasZoomFit` 不再出现（Task 4 同步删绑定）。

- [ ] **Step 2: id 存在性自检**

```
grep -c 'id="drawingTabs"'           index.html  # 1
grep -c 'id="workbenchStage"'        index.html  # 1
grep -c 'id="sketchOverlay"'         index.html  # 1
grep -c 'id="drawingSpecificTools"'  index.html  # 1
grep -c 'id="zoneLegendPreview"'     index.html  # 1
grep -c 'id="objectList"'            index.html  # 1
grep -c 'id="uploadBaseImage"'       index.html  # 1
grep -c 'id="workbenchStatus"'       index.html  # 1
grep -c 'id="dirtyDialog"'           index.html  # 1
grep -c 'id="canvasZoomFit"'         index.html  # 0  ← 已删
```
（路径用 `_tools/uploader/static/index.html`。）

- [ ] **Step 3: 提交**

```bash
git add _tools/uploader/static/index.html
git commit -m "feat(workbench): rebuild workbench DOM to studio v3 (activity rail + slim top + dock + inspector)"
```

---

## Task 3：追加 v3 样式块

**Files:**
- Append: `_tools/uploader/static/workbench/workbench.css` 末尾

说明：v3 用 `.wb3*` 前缀的新外层类，与 v2 旧外层类（`.workbench-topbar/.workbench-body/.workbench-rail/.wb-card/.workbench-footer/.canvas-toolbar` 等）不冲突——旧类在新 DOM 里没人用，成为死 CSS，本轮**不删**（以后清理）。画布内部类（`.workbench-canvas/.workbench-stage/.workbench-empty/.workbench-status/.object-list/.drawing-tab/.workspace-state/.zone-*`）继续复用；本块对其中需要改的（`.drawing-tab`、`.workbench-canvas`、`.workbench-status`）写覆盖规则，追加在文件末尾故生效。

- [ ] **Step 1: 末尾整段追加**

```css
/* =================================================================== */
/* ===== WORKBENCH STUDIO v3 (full-bleed) — see prototype html ====== */
/* =================================================================== */
.wb3{
  --act-w:64px; --insp-w:330px; --top-h:54px;
  --line3:#ddd5c5; --line-soft3:#e8e1d2; --panel3:#fbf8f1; --panel2-3:#f3eee2;
  --ink3:#2b2722; --muted3:#8a8173; --faint3:#b4ab99;
  --accent3:#1f6f5b; --accent-soft3:rgba(31,111,91,.10); --accent-line3:rgba(31,111,91,.32);
  --canvas3:#fcfaf4; --grid3:rgba(43,39,34,.055); --grid-strong3:rgba(43,39,34,.10);
  --shadow3:0 1px 2px rgba(43,39,34,.06),0 8px 26px rgba(43,39,34,.08);
  --shadow-pop3:0 10px 34px rgba(43,39,34,.16);
  height:100vh; width:100vw;
  display:grid; grid-template-columns:var(--act-w) 1fr;
  background:var(--panel3); color:var(--ink3); overflow:hidden;
}

/* ---- LEFT ACTIVITY RAIL ---- */
.wb3-act{background:var(--panel3);border-right:1px solid var(--line3);display:flex;flex-direction:column;align-items:center;padding:10px 0;gap:4px;z-index:30}
.wb3-logo{width:40px;height:40px;border-radius:11px;background:linear-gradient(150deg,var(--accent3),#15493b);color:#f4efe4;display:grid;place-items:center;font-weight:700;font-size:16px;border:0;cursor:pointer;box-shadow:0 4px 12px rgba(31,111,91,.32);margin-bottom:8px}
.wb3-act-scroll{flex:1;display:flex;flex-direction:column;gap:4px;overflow:auto;align-items:center;width:100%}
.wb3-act-scroll::-webkit-scrollbar{width:0}
.wb3-act-sep{width:26px;height:1px;background:var(--line3);margin:6px 0}
.wb3-act-btn{position:relative;width:44px;height:44px;border-radius:10px;border:1px solid transparent;background:none;cursor:pointer;color:var(--muted3);display:grid;place-items:center;font-size:18px;transition:.16s}
.wb3-act-btn:hover{background:var(--panel2-3);color:var(--ink3)}
.wb3-basewrap{position:relative}
.wb3-pop{position:absolute;left:54px;bottom:0;z-index:80;width:248px;background:var(--panel3);border:1px solid var(--line3);border-radius:12px;box-shadow:var(--shadow-pop3);padding:14px;display:flex;flex-direction:column;gap:10px}
.wb3-pop[hidden]{display:none}
.wb3-pop h5{font-size:12px;margin:0}
.wb3-pop label{display:flex;flex-direction:column;gap:4px;font-size:11px;color:var(--muted3)}
.wb3-pop input[type=text]{border:1px solid var(--line3);border-radius:7px;padding:7px 9px;font:inherit;font-size:12px;background:var(--panel2-3)}

/* ---- drawing-type buttons (rendered into #drawingTabs as .drawing-tab) ---- */
.wb3-act-scroll .drawing-tab{position:relative;width:44px;height:44px;padding:0;border-radius:10px;border:1px solid transparent;background:none;cursor:pointer;color:var(--muted3);display:grid;place-items:center;font:inherit;font-size:15px;font-weight:600;transition:.16s}
.wb3-act-scroll .drawing-tab:hover{background:var(--panel2-3);color:var(--ink3)}
.wb3-act-scroll .drawing-tab.active{background:var(--accent-soft3);color:var(--accent3);border-color:var(--accent-line3)}
.wb3-act-scroll .drawing-tab.active::before{content:"";position:absolute;left:-10px;top:9px;bottom:9px;width:3px;border-radius:3px;background:var(--accent3)}
.wb3-act-scroll .drawing-tab.planned{opacity:.4}
.wb3-act-scroll .drawing-tab small{display:none}
.wb3-act-scroll .drawing-tab .wb3-tip{position:absolute;left:52px;top:50%;transform:translateY(-50%);background:var(--ink3);color:#f6f1e7;padding:5px 9px;border-radius:7px;font-size:11.5px;font-weight:400;white-space:nowrap;opacity:0;pointer-events:none;transition:.14s;z-index:60;box-shadow:var(--shadow-pop3)}
.wb3-act-scroll .drawing-tab:hover .wb3-tip{opacity:1}

/* ---- MAIN COLUMN ---- */
.wb3-main{display:flex;flex-direction:column;min-width:0;min-height:0}
.wb3-top{height:var(--top-h);flex-shrink:0;background:var(--panel3);border-bottom:1px solid var(--line3);display:flex;align-items:center;gap:14px;padding:0 16px}
.wb3-title{display:flex;flex-direction:column;gap:1px;min-width:0}
.wb3-title .crumb{font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;color:var(--faint3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:420px}
.wb3-title b{font-size:15px;font-weight:600;display:flex;align-items:center;gap:9px}
.wb3-badge{display:inline-flex;align-items:center;gap:6px;font-size:11.5px;color:var(--accent3);background:var(--accent-soft3);padding:3px 10px;border-radius:999px;font-weight:500}
.wb3-badge::before{content:"";width:6px;height:6px;border-radius:50%;background:var(--accent3)}
.wb3-spacer{flex:1}
.wb3-btn{border:1px solid var(--line3);background:var(--panel3);color:var(--ink3);height:34px;padding:0 14px;border-radius:8px;cursor:pointer;font:inherit;font-size:12.5px;display:inline-flex;align-items:center;gap:7px;transition:.15s;white-space:nowrap}
.wb3-btn:hover{border-color:var(--accent3);color:var(--accent3)}
.wb3-btn.primary{background:var(--accent3);border-color:var(--accent3);color:#f5f0e4}
.wb3-btn.primary:hover{background:#1a5d4c;color:#fff}
.wb3-btn:disabled{opacity:.45;cursor:not-allowed}
.wb3-iconbtn{width:34px;padding:0;justify-content:center;color:var(--muted3);font-size:15px}
.wb3-iconbtn.on{background:var(--accent-soft3);border-color:var(--accent-line3);color:var(--accent3)}
.wb3-topdiv{width:1px;height:24px;background:var(--line3)}

/* ---- WORK AREA ---- */
.wb3-work{flex:1;display:grid;grid-template-columns:1fr var(--insp-w);min-height:0;transition:grid-template-columns .22s cubic-bezier(.4,0,.2,1)}
.wb3-work.insp-collapsed{grid-template-columns:1fr 0}
.wb3-work[hidden]{display:none}

/* ---- CANVAS (override reused internals) ---- */
.wb3-stage-wrap{position:relative;min-width:0;min-height:0;overflow:hidden;
  background:
    linear-gradient(var(--grid3) 1px,transparent 1px) 0 0/26px 26px,
    linear-gradient(90deg,var(--grid3) 1px,transparent 1px) 0 0/26px 26px,
    linear-gradient(var(--grid-strong3) 1px,transparent 1px) 0 0/130px 130px,
    linear-gradient(90deg,var(--grid-strong3) 1px,transparent 1px) 0 0/130px 130px,
    var(--canvas3);
}
.wb3 .workbench-canvas{position:absolute;inset:0;width:100%;height:100%;overflow:auto;border:0;border-radius:0;background:none}
.wb3 .workbench-status{position:absolute;left:16px;bottom:20px;top:auto;right:auto;transform:none;max-width:60%;z-index:8}

/* zoom pill (top-right) */
.wb3-zoom{position:absolute;top:14px;right:14px;z-index:9;display:flex;align-items:center;gap:2px;background:rgba(251,248,241,.92);backdrop-filter:blur(8px);border:1px solid var(--line3);border-radius:11px;padding:4px;box-shadow:var(--shadow3)}
.wb3-zoom button{min-width:30px;height:28px;border:0;background:none;border-radius:7px;cursor:pointer;color:var(--ink3);font:inherit;font-size:15px;display:grid;place-items:center}
.wb3-zoom button:hover{background:var(--panel2-3)}
.wb3-zoom .wb3-zoomval{font-size:12px;font-weight:500;min-width:52px}
.wb3-zoom .wb3-zoomhint{font-size:10px;color:var(--faint3);padding:0 8px 0 4px;border-left:1px solid var(--line3);margin-left:2px;height:18px;display:flex;align-items:center}

/* action dock (bottom-center) */
.wb3-dock{position:absolute;left:50%;bottom:18px;transform:translateX(-50%);z-index:9;display:flex;align-items:center;gap:3px;background:rgba(43,39,34,.92);backdrop-filter:blur(10px);border-radius:13px;padding:6px;box-shadow:var(--shadow-pop3)}
.wb3-dock button{height:34px;padding:0 13px;border:0;border-radius:9px;background:none;color:#e9e3d6;cursor:pointer;font:inherit;font-size:12.5px;transition:.14s}
.wb3-dock button:hover{background:rgba(255,255,255,.10);color:#fff}
.wb3-dock button:disabled{opacity:.4;cursor:not-allowed}
.wb3-dock button.key{background:var(--accent3);color:#fff}
.wb3-dock button.key:hover{background:#27876f}
.wb3-dock button.key:disabled{opacity:.5}
.wb3-dock .wb3-dockdiv{width:1px;height:20px;background:rgba(255,255,255,.16);margin:0 3px}

/* ---- RIGHT INSPECTOR ---- */
.wb3-insp{background:var(--panel3);border-left:1px solid var(--line3);display:flex;flex-direction:column;min-width:0;overflow:hidden}
.wb3-insp-head{height:38px;flex-shrink:0;display:flex;align-items:center;padding:0 14px;border-bottom:1px solid var(--line-soft3);font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--faint3)}
.wb3-insp-body{flex:1;overflow:auto;padding:4px 0}
.wb3-sect{border-bottom:1px solid var(--line-soft3)}
.wb3-sect-h{width:100%;display:flex;align-items:center;justify-content:space-between;padding:11px 14px;background:none;border:0;cursor:pointer;font:inherit;color:var(--ink3)}
.wb3-sect-h b{font-size:12.5px;font-weight:600;display:flex;align-items:center;gap:8px}
.wb3-sect-h .tag{font-size:10.5px;font-weight:400;color:var(--faint3)}
.wb3-sect-h .chev{transition:.18s;color:var(--muted3)}
.wb3-sect.open .chev{transform:rotate(90deg)}
.wb3-sect-c{display:none;padding:0 14px 14px}
.wb3-sect.open .wb3-sect-c{display:block}
.wb3-flowrow{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0}
.wb3-flowstat{font-size:11px;color:var(--muted3)}
.wb3-flowbtns{display:flex;gap:8px}
.wb3-flowbtns .wb3-btn{flex:1;justify-content:center}
.wb3-sect-c textarea{width:100%;border:1px solid var(--line3);border-radius:7px;padding:8px 10px;font:inherit;font-size:12px;background:var(--panel2-3);resize:vertical}

/* ---- responsive: auto-collapse inspector on narrow ---- */
@media (max-width:1040px){
  .wb3-work{grid-template-columns:1fr 0}
}
```

- [ ] **Step 2: 校验**

Run: `node --check _tools/uploader/static/workbench/workbench.js`（CSS 无 lint 工具，靠下一步浏览器看）
之后人工确认 CSS 文件无语法错（括号配对）。

- [ ] **Step 3: 提交**

```bash
git add _tools/uploader/static/workbench/workbench.css
git commit -m "style(workbench): append studio v3 stylesheet (activity rail, slim top, dock, inspector)"
```

---

## Task 4：JS 接线（竖排图纸类型 / 手风琴 / 检查器折叠 / 返回 / 面包屑 / 删 Fit）

**Files:**
- Modify: `_tools/uploader/static/workbench/workbench.js`：`renderDrawingTabs()`（约 389-416）
- Modify: `workbench.js`：`renderWorkspaceMeta()`（约 424，加面包屑）
- Modify: `workbench.js`：renderAvailability 列表删 `#canvasZoomFit`（约 814）
- Modify: `workbench.js`：缩放绑定删 `#canvasZoomFit`（约 1969）
- Modify: `workbench.js`：bind 区加手风琴 + 检查器折叠（约 footer toggle 同处，~L2018）

- [ ] **Step 1: renderDrawingTabs 改竖排 glyph**

把 `renderDrawingTabs()` 内 `tabs.innerHTML = ...` 的 `.map(...)` 模板（约 397-408）替换为：

```js
        const glyph = (config.label || key).trim().charAt(0) || "图";
        return `
          <button
            class="drawing-tab ${active ? "active" : ""} ${planned ? "planned" : "enabled"}"
            type="button"
            role="tab"
            aria-selected="${active ? "true" : "false"}"
            data-drawing-type="${escapeHtml(key)}"
          >
            ${escapeHtml(glyph)}
            <span class="wb3-tip">${escapeHtml(config.label)}${escapeHtml(suffix)}</span>
          </button>
        `;
```

（其余部分——`const active`/`const planned`/`const suffix`、`.join("")`、点击绑定——不变。）

- [ ] **Step 2: 面包屑写项目名**

在 `renderWorkspaceMeta()` 函数体开头（拿到 `config` 之后）加：

```js
    const crumb = $("#wbCrumb");
    if (crumb) crumb.textContent = projectCode() || "未选择项目";
```

- [ ] **Step 3: renderAvailability 列表删 Fit**

把 renderAvailability 里那行 `"#canvasZoomFit",` 删除（约 814 行）。

- [ ] **Step 4: 缩放绑定删 Fit**

删除缩放绑定里这一行（约 1969）：

```js
    $("#canvasZoomFit").addEventListener("click", () => setCanvasZoom(1));
```

- [ ] **Step 5: 手风琴 + 检查器折叠（bind 区追加）**

在绑定 `#footerToggle` 的同一函数里（footer toggle 已不存在于新 DOM，但绑定用了可选写法不会报错；在该处附近）追加：

```js
    // v3 inspector accordion
    document.querySelectorAll(".wb3-sect-h").forEach((h) => {
      h.addEventListener("click", () => h.parentElement.classList.toggle("open"));
    });
    // v3 inspector collapse
    const inspBtn = $("#toggleInspector");
    if (inspBtn) {
      inspBtn.addEventListener("click", () => {
        const work = $("#workbenchLayout");
        if (!work) return;
        const collapsed = work.classList.toggle("insp-collapsed");
        inspBtn.classList.toggle("on", !collapsed);
      });
    }
```

> 说明：旧的 `#footerToggle` / `#toggleLeftRail` / `#toggleRightRail` 绑定若仍在代码里，保留无害（新 DOM 没有这些元素，`$()` 返回 null，已有 `if`/`?.` 守卫）。如发现它们是无守卫的 `$("#x").addEventListener`，把对应行删掉或加 `?.`。

- [ ] **Step 6: 校验**

Run: `node --check _tools/uploader/static/workbench/workbench.js`
Expected: 通过

- [ ] **Step 7: 提交**

```bash
git add _tools/uploader/static/workbench/workbench.js
git commit -m "feat(workbench): wire studio v3 (vertical type rail, accordion, inspector collapse, crumb; drop zoomFit)"
```

---

## 全量回归校验（实施完整跑）

- [ ] `node --check _tools/uploader/static/workbench/workbench.js` 通过
- [ ] `node --check _tools/uploader/static/app.js` 通过
- [ ] `python _tools/validate_record.py 26-BQ-PARK` 通过
- [ ] id 自检（Task 2 Step 2 的 grep 全部符合）
- [ ] 浏览器全链路（进 26-BQ-PARK → 图纸 tab）：
  - [ ] 进入工作台后整页全屏铺满，无 1240px 居中留白；全局顶部 `.mast`/`.stage-nav` 隐藏
  - [ ] 左活动栏列出图纸类型（首字 glyph + hover 出全名），点击切换图纸正常；点左上「建」logo 返回到项目页（全局外壳恢复）
  - [ ] 顶栏：面包屑显示项目名；标题 + 徽章；加载/保存可用；检查器开关切换右栏显隐（画布相应变宽）
  - [ ] 画布：底图加载、缩放（按钮 + Ctrl 滚轮，到 800%）、绘制闭合、弧线拖拽/双击还原、handle 屏幕恒定均正常
  - [ ] 操作坞：完成/撤销/重做/删除/清空 全部触发对应逻辑
  - [ ] 状态 toast 在画布左下浮现并淡出
  - [ ] 检查器手风琴：风格/图例/对象明细/出图工作流 可展开收起；风格控件（调色板/填充/边框/线宽）、图例预览、对象选择、发给 agent / 导出 全部正常
  - [ ] 底图弹窗（活动栏 ▦）可开关、上传
  - [ ] 切到「状态」「S0/S1/S2」页：全局外壳恢复正常（mast/stage-nav 回来、1240px 居中），未被 workbench-mode 污染

## 回推给 mac claude 终审

回推 diff + **6 张截图**：默认全屏态 / 缩放 800% / 检查器折叠态 / 活动栏切到交通分析 / 底图弹窗 / 切回 S1 看全局外壳未被污染。

## 红线

- ❌ 不动绘图/弧线/schema/agent 协议逻辑、不动 S0/S1/S2/项目/状态页面内容
- ❌ 不删 / 不改任何现有 id（除按计划删除 `#canvasZoomFit`）
- ❌ 不碰 `agent_drawing_protocol.md`；不 stage 运行产物；不删用户未跟踪文件
- ❌ 不持久化折叠/缩放态到项目文件；不用 `transform: scale()` 缩放画布
- ❌ 不删 v2 死 CSS（本轮先留着，避免误删在用的内部类）
```

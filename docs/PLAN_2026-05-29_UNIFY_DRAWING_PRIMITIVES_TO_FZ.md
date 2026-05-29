# 统一绘图图元到功能分区（FZ）实施计划

> **执行者：codex（具备视觉）。** mac claude 出计划 + 最终审；codex 实施 + 自检（含截图对比）。
> 计划针对 `origin/main @ b43930a`。开工前先 `git pull --ff-only` 对齐到该提交，行号才对得上。
> 步骤用 `- [ ]` 复选框跟踪，按任务顺序逐个提交。

**目标（一句话）：** 让多边形/线段/圆形/三角形的「线宽·填充·边框·交互」全部走 FZ 同一套样式模型、同一个控件渲染器、同一个 SVG 渲染器——新增图元先与 FZ 多边形对齐，再按差量增删，**彻底删除现存的平行第二套**。

**架构（3 句话）：** ① 样式模型只保留 `Model.normalizeStyleHints`（已是超集且已登记 `functional_zone`），删除 `workbench.js` 里重复的 `normalizeZoneStyle`。② 控件只保留一个由「图元字段配置表」驱动的渲染器，FZ 多边形与新多边形用**同一份 4 态配置（≡）**；圆/线/三角 = 在同一配置表里加差量。③ SVG 只保留一个按 `geometry.kind` 分支的 `renderObjectSvg`，删除 `renderFunctionalZoneSvg`，FZ 闭合多边形走同一分支；命中层/顶点/弧线 handle 已是共享函数，保留。

**技术栈：** 原生 JS（UMD 模块 `workbench_model.js` + `workbench.js`）、CSS、Playwright 浏览器冒烟（`_tools/tests/drawing_workbench_browser_smoke.py`）、`node --check`、`python -m py_compile`。无 JS 单测框架——「测试」= 扩展浏览器冒烟断言 + 结构 grep 红线 + codex 截图对比。

---

## 为什么前两轮失败（codex 必读，否则会重蹈覆辙）

- 现存**两套完整链**，仅命中层/handle 共享，其余全平行：

  | 环节 | FZ 多边形（认可的） | 新增图元（要删的平行套） |
  |---|---|---|
  | 控件 | `renderFunctionalZoningTools` (1040) + `bindFunctionalZoningTools` (1286) | `renderTrimmedRegistryStyleControls` (742) + `bindRegistryStyleControls` (887) |
  | 样式模型 | `normalizeZoneStyle` (1256)、`state.zoneDraftStyle` | `Model.normalizeStyleHints`、`state.styleDrafts`/`state.lastStyles` |
  | 更新 | `updateZoneStyle` (1326) | `updateActiveStyle` (951) / `updateActiveGeometry` (967) |
  | 渲染 | `renderFunctionalZoneSvg` (2397) | `renderObjectSvg` (2270) 的各 kind 分支 |

- 「对齐 FZ」是判断题，无约束时只会做成**表皮像**（借 CSS class），底层仍两套。本轮把成功定义改成**结构二值红线**：上表「要删的平行套」那几个函数实施后必须**不存在**（grep 为 0）。这点截图骗不过、CSS 糊不过。
- 真 bug 实证：`renderObjectSvg` 第 **2276** 行 `const width = selected ? 0.012 : 0.008;`，多边形(2327/2344)、三角形(2309)、线段(2375/2381)全用这个写死值，**完全无视用户选的 `stroke_width`**——这正是「配色线粗选了不生效」。FZ(2405) 用 `style.stroke_width`。

## 关键设计决策

1. **统一模型 = `Model.normalizeStyleHints`**（超集，已含 `functional_zone` 覆盖项，且已有 `fill_enabled→fill_mode` 兼容迁移）。FZ 的 `normalizeZoneStyle` 是它的最小子集，删除；FZ 的线宽夹取（0.001–0.012）和默认色并入「图元字段配置表」。
2. **FZ 多边形 ≡ 新多边形（用户拍板：FZ 也升级到 4 态填充）。** 二者用**同一份控件配置**：
   - 填充 = `无 / 半透明 / 实心 / 斜线`（4 态）；边框 = `无 / 实线 / 虚线 / 双实线`。
   - **回归安全性论证**：现存 FZ 数据只用到 `fill_enabled→none/translucent` 与 `border_style ∈ solid/dashed/none`，从不取 `solid/hatch/double`；因此「控件多出这些选项」**不改变任何现存分区的渲染**——旧档逐像素不变，这仍是红线。新增的 4 态/双线只在用户主动选择时才生效。
   - 旧 `有填充/无填充` 两按钮**取消**，FZ 改用与新多边形一致的 4 态 `segmented-control`。
3. **配色控件统一用 FZ 那套**：色板 swatch + 最近使用色 + 自定义色（现 `renderFunctionalZoningTools` 1051–1095 的部分）。所有图元的「填充色/线色/边框色」都用它，不再用裸 `<input type=color>`。
4. **FZ 是回归红线**：抽取/合并必须让 FZ 自己也走统一函数，且**逐像素不变**（弧线 segment、zone-hit 命中层、顶点+弧线 handle、选中加深、图例分组）。

## 文件结构

- `_tools/uploader/static/workbench/workbench.js`（主战场）：删两套→并一套。新增 `PRIMITIVE_STYLE_SPEC` 注册表 + `renderStyleControls`/`bindStyleControls`/`updateStyle` 统一三函数。
- `_tools/uploader/static/workbench/workbench_model.js`：基本不动；仅确认 `normalizeStyleHints` 能承接 FZ 的 `stroke_width` 夹取（必要时加 clamp）。
- `_tools/uploader/static/workbench/workbench.css`：FZ widget class（`zone-tool-group`/`segmented-control`/`zone-palette`/`zone-swatch`）成为唯一样式来源；删 `compact-style-controls` 等平行 class。
- `_tools/tests/drawing_workbench_browser_smoke.py`：把「存在性断言」升级为「行为等价 + 结构红线」断言。

---

## Task 1：统一样式模型——FZ 改用 `Model.normalizeStyleHints`

**Files:** Modify `_tools/uploader/static/workbench/workbench.js`（`normalizeZoneStyle` 1256、`updateZoneStyle` 1326、`renderFunctionalZoneSvg` 2397、所有 `normalizeZoneStyle(...)` 调用点：1042/1137/1256/1328/1458/1460/1552/1553/1643/1936/1988/2399/2555/2779）

- [ ] **Step 1：先写回归断言（红线，必须先红）**
  在 `_tools/tests/drawing_workbench_browser_smoke.py` 的 `assert_fz_regression` 内追加：创建一个 `fill_enabled=false` 的 FZ 分区存盘→重载→断言其可见图形 `fill="none"`；创建 `fill_enabled=true` 的→断言 `fill-opacity≈0.42`。
- [ ] **Step 2：跑测试确认现状（应通过，作为基线快照）**
  Run: `python _tools/tests/drawing_workbench_browser_smoke.py`
  Expected: PASS（建立 FZ 当前行为基线；改完后必须仍 PASS）。
- [ ] **Step 3：让 FZ 走统一模型**
  - 将 `normalizeZoneStyle(style)` 改为薄适配器：
    ```js
    function normalizeZoneStyle(style = {}) {
      const s = Model.normalizeStyleHints(style || {}, "functional_zone");
      // FZ 线宽夹取保持原行为
      s.stroke_width = normalizeStrokeWidth(s.stroke_width);
      return s;
    }
    ```
  - 在 `renderFunctionalZoneSvg`(2397) 内，把 `fill_enabled` 读法替换为 `fill_mode`：
    `const fillVisible = s.fill_mode !== "none";`、`const fill = fillVisible ? s.fill_color : "none";`、`fill-opacity` 用 `s.fill_opacity ?? 0.42`。其余（segments/polygon 分支、`renderSharedPathHitLayer`、handle）保持不动。
  - 确认 `Model.normalizeStyleHints` 的旧档迁移（`fill_enabled→fill_mode`）对 FZ 生效；FZ 的 4 态填充控件在 Task 2 统一渲染器里建（本任务只动模型，不动 FZ 旧的 2 态按钮——它将在 Task 2 被整段替换）。
- [ ] **Step 4：跑测试确认 FZ 行为不变**
  Run: `python _tools/tests/drawing_workbench_browser_smoke.py`
  Expected: PASS（含 Step1 新断言、原有 `assert_fz_regression`、quadratic 重载不丢）。
- [ ] **Step 5：codex 视觉自检**
  截图：FZ 工具下画一个带弧的分区、切「有/无填充」「实/虚/无边框」「拖线宽」。确认与改前一致。
- [ ] **Step 6：提交**
  ```bash
  git add _tools/uploader/static/workbench/workbench.js _tools/tests/drawing_workbench_browser_smoke.py
  git commit -m "refactor(workbench): route functional_zone style through unified model"
  ```

## Task 2：图元字段配置表 + 统一控件渲染器

**Files:** Modify `workbench.js`（新增 `PRIMITIVE_STYLE_SPEC` + `renderStyleControls`/`bindStyleControls`；`renderSpecificTools` 626、`renderFunctionalZoningTools` 1040、`renderRegistryTools` 641、`renderTrimmedRegistryStyleControls` 742）

- [ ] **Step 1：新增字段配置表（这是「先对齐再增删」的落点，注释写清差量来源）**
  ```js
  // 唯一事实来源：每个图元暴露哪些控件。FZ = 子集；其余 = FZ 基座 + 差量（依据 DISCUSSION §2.2–§2.7）。
  const PRIMITIVE_STYLE_SPEC = {
    // FZ ≡ 新多边形：同一份配置（用户拍板升级 FZ 到 4 态）。
    functional_zone: { color: true, fill: ["none","translucent","solid","hatch"], border: ["none","solid","dashed","double"], strokeWidth: true, legendName: true },
    closed_path:     { color: true, fill: ["none","translucent","solid","hatch"], border: ["none","solid","dashed","double"], strokeWidth: true, legendName: true },
    open_path:       { color: true, fill: false, border: false, strokeStyle: ["solid","dashed"], strokeWidth: true, arrows: "flow-only", legendName: true },
    circle:          { color: true, fill: ["none","translucent","solid"], border: ["none","solid","dashed","double"], strokeWidth: true, radius: true, legendName: true },
    triangle:        { color: true, fill: ["none","translucent","solid"], border: ["none","solid","dashed"], strokeWidth: true, size: true, rotation: true, legendName: true },
    turning_radius:  { color: true, fill: false, border: false, strokeStyle: ["solid","dashed"], strokeWidth: true, arrows: "flow-only", labelBox: true, legendName: true },
    elevation_marker:{ color: true, fill: ["none","translucent","solid"], border: ["none","solid","dashed"], strokeWidth: true, size: true, rotation: true, labelBox: true, legendName: true },
    slope_arrow:     { color: true, fill: false, border: false, strokeStyle: ["solid","dashed"], strokeWidth: true, arrows: "flow-only", inlineText: true, legendName: true },
  };
  const FILL_LABELS = { none: "无", translucent: "半透明", solid: "实心", hatch: "斜线" };
  const BORDER_LABELS = { none: "无边框", solid: "实线", dashed: "虚线", double: "双实线" };
  ```
- [ ] **Step 2：写 `renderStyleControls(specKey, style)`——复用 FZ 的 widget**
  - 色板：抽出 FZ 1051–1095 的 `zonePalette`+最近色+`zoneCustomColor` 成 `renderColorControl(field, value)`（`field` ∈ `fill_color`/`stroke_color`）。
  - 填充：`spec.fill` 存在时，`segmented-control` 选项 = `spec.fill.map(v=>({value:v,label:FILL_LABELS[v]}))`；`fill_mode==="hatch"` 时 `<details>` 出角度/间距；`translucent` 出不透明度（折叠）。
  - 边框：`spec.border` → `segmented-control`(BORDER_LABELS)；`border_style==="double"` 出间距（折叠）。
  - 线型：`spec.strokeStyle` → `实线/虚线` 段。
  - 线宽：`rangeControl("styleStrokeWidth", spec.fill?"边框宽":"线宽", style.stroke_width, "0.001","0.018","0.0005")`。
  - 箭头：`spec.arrows==="flow-only"` 且 `shouldShowArrowControls(...)` 为真才出起点/终点/尺寸。
  - radius/size/rotation/labelBox/inlineText/legendName：照 spec 出对应控件（沿用 742 现有片段，迁进来）。
  - **全部用 `zone-tool-group`/`segmented-control`/`zone-palette`/`style-section-title` 这套 class，删 `compact-style-controls`。**
- [ ] **Step 3：路由收口**
  - `renderSpecificTools`(626)：FZ 分支也只渲染「绘图工具选择器（如适用）+ 分区名 + `renderStyleControls("functional_zone", zoneStyle)`」，不再调 `renderFunctionalZoningTools` 的独立样式段。
  - `renderRegistryTools`：`renderTrimmedRegistryStyleControls(...)` 调用点改为 `renderStyleControls(activeTool, draftStyleFor(...))`。
  - **删除** `renderTrimmedRegistryStyleControls`(742) 与 `renderRegistryStyleControls`(883) 函数体。
- [ ] **Step 4：统一绑定 `bindStyleControls`**
  合并 `bindFunctionalZoningTools`(1286) 与 `bindRegistryStyleControls`(887)：所有 segmented/滑块/色板/最近色/自定义色事件 → 调统一 `updateStyle(specKey, patch)`（FZ 选中态走 FZ 的 `pushUndoSnapshot`+写 `style_hints`+`state.zoneDraftStyle`；新对象走 `state.styleDrafts`/`lastStyles`——保留各自的 draft 存储，但归一化和渲染走同一条）。删两个旧 bind 函数。
- [ ] **Step 5：跑门禁**
  Run: `node --check _tools/uploader/static/workbench/workbench.js && python _tools/tests/drawing_workbench_browser_smoke.py`
  Expected: PASS。`assert_control_rules`（多边形无箭头/无独立 double_gap、配图门控）仍绿。
- [ ] **Step 6：结构红线 grep（必须为 0）**
  Run: `grep -nE "renderTrimmedRegistryStyleControls|renderRegistryStyleControls|bindRegistryStyleControls|bindFunctionalZoningTools|compact-style-controls" _tools/uploader/static/workbench/workbench.js`
  Expected: 无输出（旧平行控件链已删尽）。
- [ ] **Step 7：codex 视觉自检 + 提交**
  截图对比 FZ 多边形控件 vs 新 closed_path 控件：应**完全一致**（色板/4 态填充/4 选项边框/线宽形态全同）；再验现存旧 FZ 分区渲染未变。
  ```bash
  git add -A && git commit -m "refactor(workbench): single spec-driven style controls for FZ + all primitives"
  ```

## Task 3：统一 SVG 渲染——删 `renderFunctionalZoneSvg`，修线宽 bug

**Files:** Modify `workbench.js`（`renderObjectSvg` 2270、`renderFunctionalZoneSvg` 2397）

- [ ] **Step 1：写「线宽生效」行为断言（必须先红）**
  在浏览器冒烟里加 `assert_stroke_width_honored`：对 closed_path/open_path/triangle 各创建一个并设 `stroke_width=0.011`，读其**可见**图形（非 `.geometry-hit`）的 `stroke-width`，断言 `abs(v-0.011) < 0.0005`。
- [ ] **Step 2：跑测试确认现在是红的**
  Run: `python _tools/tests/drawing_workbench_browser_smoke.py`
  Expected: FAIL（现状写死 0.008/0.012）。
- [ ] **Step 3：合并渲染**
  - `renderObjectSvg`(2270) 顶部删掉 `if (isFunctionalZoning() && obj.type==="functional_zone") return renderFunctionalZoneSvg(obj);`——让 FZ 也走下面统一分支。
  - 删第 **2276** 行 `const width = selected ? 0.012 : 0.008;`。改为读样式：`const sw = style.hints.stroke_width || 0.003;`，闭合/开放/三角的可见图形一律 `stroke-width="${sw}"`；选中反馈改为 `stroke = selectedStrokeColor(strokeColor, selected)`（保持 FZ 的 `darkenHex(..,0.2)` 加深，不再靠加粗）。
  - 闭合 path 分支统一读 `fill_mode`（`pathFillValue` 已支持），双实线读 `border_style==="double"`+`double_border_gap`，虚线读 `stroke_style/border_style==="dashed"`。
  - **删除** `renderFunctionalZoneSvg`(2397) 整个函数。
- [ ] **Step 4：跑全门禁**
  Run: `python _tools/tests/drawing_workbench_browser_smoke.py`
  Expected: PASS（新 `assert_stroke_width_honored` + `assert_fz_regression` + quadratic 重载 全绿）。
- [ ] **Step 5：结构红线 grep（必须为 0）**
  Run: `grep -nE "renderFunctionalZoneSvg|selected \? 0\.012|0\.008" _tools/uploader/static/workbench/workbench.js`
  Expected: 无输出。
- [ ] **Step 6：codex 视觉自检——FZ 回归逐像素**
  截图叠放：改前/改后同一带弧 FZ 分区（选中态加深、顶点+弧线 handle、命中层）。必须无可见差异。
- [ ] **Step 7：提交**
  ```bash
  git add -A && git commit -m "refactor(workbench): single geometry-kind SVG renderer; honor stroke_width"
  ```

## Task 4：按差量核对各图元（圆/线/三角/标注框/坡度）

**Files:** Modify `workbench.js`（圆 2281、三角 2298、开放 path 2367 等分支，`renderArrowHeads`、`renderSegmentHandles`）

- [ ] **Step 1：逐项对照 `PRIMITIVE_STYLE_SPEC` 自查**
  确认渲染读到的字段 = 配置表暴露的字段：圆有 `radius`+双线间距；三角有 `size`/`rotation`；线段无填充、`flow-only` 才有箭头；`turning_radius`/`slope_arrow` 的 label_box/inline_text 仍渲染。圆/三角/线全部经 `renderShared*HitLayer` + `renderSharedVertexHandles`（已具备，确认未回退）。
- [ ] **Step 2：交互一致性断言**
  扩 `assert_shared_interaction_dom`：对 circle/triangle 也断言选中后存在 `.geometry-vertex-handle`；对 open_path/closed_path 断言存在 `.zone-arc-handle`（与 FZ 同源 `renderSegmentHandles`）。
- [ ] **Step 3：跑门禁**
  Run: `python _tools/tests/drawing_workbench_browser_smoke.py`
  Expected: PASS。
- [ ] **Step 4：codex 视觉自检**
  每种图元各画一个：选中、拖顶点、拖弧、改色/线宽/填充，确认与 FZ 多边形操作手感一致，差量项（半径/旋转/箭头/标注框）正常。
- [ ] **Step 5：提交**
  ```bash
  git add -A && git commit -m "fix(workbench): align circle/line/triangle interaction+controls to FZ baseline"
  ```

## Task 5：清死代码 + 门禁收口

**Files:** Modify `workbench.js`、`workbench.css`、`drawing_workbench_browser_smoke.py`

- [ ] **Step 1：删 `return;` 之后的死代码块**（`renderSpecificTools` 区、`finishObject` 区——round-2 brief 提过；用 `node --check` 后人工扫 unreachable）。
- [ ] **Step 2：CSS 收口**：删 `compact-style-controls` 等只服务旧平行控件的规则，确认统一控件只依赖 FZ widget class。
- [ ] **Step 3：全门禁一把过**
  Run: `python -m py_compile _tools/tests/drawing_workbench_browser_smoke.py && node --check _tools/uploader/static/workbench/workbench.js && node --check _tools/uploader/static/workbench/workbench_model.js && python _tools/tests/drawing_workbench_browser_smoke.py`
  Expected: 全 PASS，0 console error。
- [ ] **Step 4：结构红线总检（全部应为 0）**
  Run: `grep -cE "renderFunctionalZoneSvg|renderTrimmedRegistryStyleControls|renderRegistryStyleControls|bindRegistryStyleControls|bindFunctionalZoningTools|selected \? 0\.012" _tools/uploader/static/workbench/workbench.js`
  Expected: `0`。
- [ ] **Step 5：提交**
  ```bash
  git add -A && git commit -m "chore(workbench): remove dead code and parallel-path CSS"
  ```

---

# 第二批（第四轮）：统一交互层——保证画布操作/选中手感对齐 FZ

> 背景：第一批（Task 1–5）统一了**模型/控件/渲染**三层，但**事件/交互层**仍有 23 处 `isFunctionalZoning()` 分叉，用户实测「画布上的操作与选中方式跟功能分区完全不一样」。本批专治交互层。
> **优先级（用户拍板）：以「像 FZ」为准；与原始规格 §2.x 抵触的手感细节让位。**
> **手感对齐范围（用户拍板）**：多边形/线段 = 创建+选中+渲染+编辑**全程**对齐 FZ；圆形/三角形 = 选中/渲染/编辑/样式对齐 FZ，仅「创建那一下」按几何走（圆=点圆心+拖半径；三角=点一下+定尺寸/旋转）。

## Task 6：线段/多边形支持多点创建（修「线段两点就自动闭合」）

**Files:** Modify `workbench.js`（`addPoint` 2092、`TOOL_GEOMETRY` 28、`finishObject` 2124）

- [ ] **Step 1：写失败断言（必须先红）**
  浏览器冒烟新增 `assert_line_multipoint`：选「线段」工具，依次点 4 个不共线的点，断言此时**尚未生成对象**（`state.objects` 不增、`#sketchOverlay` 草图 polyline 有 4 个点）；再点「完成」按钮→断言生成 1 个 `geometry.kind==="path" && closed===false` 且 `coords.length===4` 的对象。
- [ ] **Step 2：跑测试确认红**
  Run: `python _tools/tests/drawing_workbench_browser_smoke.py`
  Expected: FAIL（现状第 2 点即 `createObjectFromTool` 自动收尾，加不了第 3 点）。
- [ ] **Step 3：去掉「到 minPoints 自动建对象」分支**
  `addPoint`(2117) 删除 `if (len >= minPoints && minPoints <= 2) createObjectFromTool(...)` 这段自动收尾。改为：path 类（closed_path/open_path/turning_radius/slope_arrow）一律**累积点 + 重绘草图**，只在**显式完成**（完成按钮 / Enter / 双击 / 点闭合手柄）时收尾——与 FZ 多边形同流程。`minPoints` 仅在 `finishObject` 内做**最小点数校验**（线段≥2，多边形≥3），不再触发自动建。
  point 类（circle/triangle，minPoints:1）保留「点一下即建默认尺寸对象、随后拖拽调整」——这是几何决定的创建方式。
- [ ] **Step 4：跑测试确认绿**
  Run: `python _tools/tests/drawing_workbench_browser_smoke.py`
  Expected: PASS（`assert_line_multipoint` + 既有断言）。
- [ ] **Step 5：codex 视觉自检 + 提交**
  线段连点 5 个 → 折线持续延伸 → 完成 → 5 点折线；可拖某段中点成弧。
  ```bash
  git add -A && git commit -m "fix(workbench): polyline/polygon accumulate points until explicit finish (no 2-point auto-close)"
  ```

## Task 7：统一草图预览 / 闭合手柄 / 完成 / 键盘——折叠 isFunctionalZoning 分叉

**Files:** Modify `workbench.js`（`renderDraftSvg` 2663、`addPoint` 2099/2104、`finishObject`/`finishFunctionalZone` 2124/2141、Enter 处理器 2949、`selectObject` 2859、完成按钮文案 1543）

- [ ] **Step 1：草图预览统一**
  `renderDraftSvg`(2663) 删 `isFunctionalZoning` 分叉：所有 path 草图都用 FZ 的形态——顶点用 `renderHandleSvg`；**闭合类（closed_path/functional_zone）在第一点且点数≥3 时渲染 `renderCloseHandleSvg`（点它收口）**；开放类（open_path 等）不渲染闭合手柄。线宽统一用 FZ 草图常量。
- [ ] **Step 2：完成路径统一**
  把 `finishFunctionalZone`(2141) 与 `finishObject`(2124) 的非 FZ 分支合并为一个 `finishObject()`：按 `geometry.closed`/kind 决定校验点数与是否闭合，**不再按 `isFunctionalZoning()` 分流**；`addPoint`(2099/2104) 的「开画前清选中 + 累积点」逻辑去掉 FZ 分叉；`selectObject`(2859) 选中后抓默认样式对所有类型一致。
- [ ] **Step 3：键盘/按钮统一**
  Enter 处理器(2949)：任意「正在多点绘制」状态（`currentPoints.length >= 该工具 minPoints`）按 Enter 即完成，不限 FZ；完成按钮文案(1543) 由当前工具标签驱动即可（可保留动态文案，但分流逻辑删除）。
- [ ] **Step 4：跑门禁**
  Run: `node --check _tools/uploader/static/workbench/workbench.js && python _tools/tests/drawing_workbench_browser_smoke.py`
  Expected: PASS（含 `assert_fz_regression`——FZ 创建/收口/选中行为逐像素不变）。
- [ ] **Step 5：结构红线 grep**
  Run: `grep -nE "isFunctionalZoning" _tools/uploader/static/workbench/workbench.js | grep -nE "addPoint|finish|renderDraftSvg|key|Enter|selectObject" ; grep -c "isFunctionalZoning" _tools/uploader/static/workbench/workbench.js`
  Expected: 第一条**无输出**（创建/完成/草图/键盘/选中处理器里 0 个 `isFunctionalZoning`）；总数从 23 降到个位数（只剩 `drawingType`/类型路由等合法用途）。
- [ ] **Step 6：codex 视觉自检 + 提交**
  并排：FZ 多边形 vs 新多边形——逐点画、第一点闭合手柄、回车收口、虚线草图，操作**一模一样**。
  ```bash
  git add -A && git commit -m "refactor(workbench): unify draft/close/finish/select interaction across primitives"
  ```

## Task 8：行为等价门禁——把 FZ 的交互脚本原样跑在每个图元上（本批红线）

**Files:** Modify `_tools/tests/drawing_workbench_browser_smoke.py`

- [ ] **Step 1：抽出 FZ 交互序列为可复用函数**
  把现有 `assert_fz_regression` 里「点 N 点→点闭合手柄收口→选中→pointerdown 拖某段中点→断言该段 `kind==="quadratic"`→断言选中加深/zone-hit/handle 齐全」抽成 `drive_polygon_interaction(page, tool_id)`。
- [ ] **Step 2：对每个图元跑同一脚本**
  - `closed_path`（任一非 FZ 图纸）：`drive_polygon_interaction` **一字不改**通过（含闭合手柄、拖边成弧）。
  - `open_path`：多点折线版（无闭合手柄）——连点≥3、拖边成弧、选中加深、handle 齐全。
  - `circle`/`triangle`：创建后**选中→拖拽编辑→改色/线宽**与 FZ 同源函数驱动（创建按几何，不跑闭合手柄那步）。
- [ ] **Step 3：跑全门禁确认绿**
  Run: `python _tools/tests/drawing_workbench_browser_smoke.py`
  Expected: PASS，0 console error。**这是本批红线：FZ 能过的交互,新图元必须同脚本过。**
- [ ] **Step 4：提交**
  ```bash
  git add -A && git commit -m "test(workbench): drive FZ interaction script verbatim on every primitive"
  ```

---

## 验收红线汇总（mac claude 最终审会逐条看实际输出）

1. **结构（二值，骗不过）**：`renderFunctionalZoneSvg` / `renderTrimmedRegistryStyleControls` / `renderRegistryStyleControls` / 两个旧 bind 函数 / 写死 `0.008`·`0.012` 线宽——grep 全 0。
2. **行为**：closed_path/open_path/triangle 设线宽 X → 可见图形 `stroke-width≈X`；填充 4 态在多边形渲染正确（半透明 opacity、斜线 pattern）；箭头仅 flow 类出现。
3. **FZ 回归（红线）**：FZ 带弧分区存→重载弧不丢；`fill_enabled` 旧档迁移为 `none/translucent` 后渲染与改前**逐像素一致**（FZ 控件现含 4 态填充/双线边框，但现存数据不取这些值，故旧分区不变）；选中后 `zone-hit` 命中层 + 顶点 + 弧线 handle 齐全；图例分组不变。
4. **交互层（第四轮红线）**：① 线段支持多点——连点≥3 不自动收尾，显式完成才生成（`assert_line_multipoint`）；② `addPoint`/`finishObject`/`renderDraftSvg`/键盘/`selectObject` 处理器里 `isFunctionalZoning` grep 为 0，总数降至个位数；③ **FZ 的交互脚本 `drive_polygon_interaction` 原样跑在 closed_path/open_path 上必须通过**（逐点画、闭合手柄收口、拖边成弧、选中加深、handle 齐全）；圆/三角选中+拖拽+样式同源脚本通过。
5. 其余既有门禁（py_compile / node --check / API smoke / validate_record）全过。

## 交付约定

- 第一批 5 任务 + 第二批（第四轮）Task 6–8，各一次提交，提交信息如上。第二批是在第一批已落地基础上继续。
- **不要改 `docs/CLAUDE_CODEX_REVIEW_THREAD.md`**——审阅线程留给 mac claude。
- 回推后通知 mac claude 做最终审 + 看结构 grep 与行为断言的实际输出。

# Claude / Codex Review Thread

本文件只保留最近一轮正式回复；历史请看 `git log -- docs/CLAUDE_CODEX_REVIEW_THREAD.md`。

> 称呼：实施 + 写开发计划 = **Windows claude**；一审 = **Windows codex**；最终审阅 = **mac claude（我）**。

---

## 2026-05-29 mac claude → Windows codex：实施回推最终审 — **不通过**，前端整层（Phase 5 / F3–F9）未实现，附返工方向 + 升级验收门禁

审阅对象：`2fc1576..3dc105e`（6 个提交）实施结果。用户手测反馈"各图纸功能全没实现，每张图纸只是一模一样的框架"——**属实，且根因明确**。本轮返工**交给 Windows codex 执行**。

### 一句话结论

后端（registry / schema 1.2 / API / task_pack）、独立模型模块 `workbench_model.js`、以及全部 Python/Node/API 测试都**正确且通过**。但真正决定"每张图纸有不同功能"的前端交互层 `workbench.js` **没有按计划 §7（Wave F3–F9）重构**。除 `functional_zoning` 外的 9 张图纸全部走同一个通用占位表单，且产出的几何数据非法。

### 证据（已逐条核到 file:line）

1. **通用占位表单 = "一模一样的框架"**：`workbench.js:492-532` `renderSpecificTools()` 对所有非 FZ 图纸只渲染 对象类型/几何类型/标签/来源 四个字段。计划 §7 要的工具按钮（F4）、样式检查器（F7：填充/描边/箭头/hatch/圆半径/三角尺寸/标注框）、配图面板（F8）**全缺**；turning_radius / elevation_marker / slope_arrow / supporting_images 工具在 UI 里根本不存在。
2. **画出的几何非法、存不进去**：`workbench.js:1315-1352` `finishObject()` 把 `geometryKind.value` 直接当 kind，产出 `{kind:"closed_path"|"open_path"}`。schema 只接受 `path/circle/triangle/point`（`schema.py:25`），`/api/drawing/save→normalize_drawing`（`server.py:681`）必然报错 → 非 FZ 对象保存必失败。
3. **圆/三角一画就崩**：`renderObjectSvg`（`workbench.js:1449-1472`）读 `geo.center/radius/size`，但 `finishObject`（1339）给圆/三角建的是 `{kind:"circle",coords:[[x,y]]}`，无 center/radius → 读 undefined 抛异常 → overlay 渲染整体挂掉。`addPoint`（1287-1313）也没有圆/三角"单击即建"、转弯半径/坡度箭头"两点成箭头"。
4. **`minimum` 校验失效**：`workbench.js:1327` 用 `{point,polyline,arrow,polygon}` 查表，但 kind 已换成 `closed_path` 等新值，永远命不中 → 任何形状 1 点即可"完成"。
5. **无按类型默认样式**：`objectStyle()`（`workbench.js:976-985`）只硬编码 5 个旧类型，planting_zone/landscape_node/sponge_zone 等全 fallthrough 成黑色——这就是"无功能差异"的视觉表现。
6. **计划核心产物 `workbench_model.js` 是死代码**：`workbench.js` 从未引用 `DrawingWorkbenchModel`，且 `index.html:424` **只加载了 workbench.js、没加载 workbench_model.js**。模块只为喂 Node 测试而生。

### 为什么测试全绿却没功能（也含我上轮的责任）

硬门禁（Python 单测 / Node 模型测试 / API smoke）测的是后端 + 那个**独立**模型模块——都对。唯一驱动真实 UI 的浏览器 smoke 是 best-effort：没装 Playwright 就 `exit 0`，即便跑也只数了 tab 数（`drawing_workbench_browser_smoke.py:76-79`），**没有"选图纸→选工具→画对象→保存→重载"的断言**。于是整层前端缺失从门禁缝里漏过。

**坦白**：上一轮二审是我（mac claude）力主把浏览器 smoke 降级 best-effort（防 /goal 把预算烧在手搓 CDP 上）。那个判断挡住了一个烂尾点，却放开了另一个——前端占位也能过门禁。本轮修正不是退回"手搓 CDP"，而是**在已知前端是风险点的前提下，补一个正经的、必过的 UI 驱动门禁**。

### 不要 revert，fix-forward

坏账只在 `workbench.js` 一处（提交 `d2cbb88`）。registry/schema/API/task_pack/模型模块/测试都对，revert 会把它们一起扔掉重做。**保留这 6 个提交，在 main 上往前修。**

### 返工方向（codex 执行，按 file:line 落地）

**A. 工具→几何 的映射层（堵死 #2/#4 的根源）**
- UI 工具 id（`closed_path/open_path/circle/triangle/turning_radius/elevation_marker/slope_arrow`）**绝不能原样存进 geometry.kind**。在建对象时映射成 schema 合法形状：
  - `closed_path → {kind:"path", closed:true, coords}`（≥3 点）
  - `open_path → {kind:"path", closed:false, coords}`（≥2 点）
  - `circle → {kind:"circle", center:[x,y], radius}`（默认 0.035）
  - `triangle / elevation_marker → {kind:"triangle", center:[x,y], size, rotation_deg}`（默认 size 0.055, rot 0）
  - `turning_radius → {kind:"path", closed:false, coords:[a,b]}` + `style_hints.label_box.enabled=true, text="R=9M"`
  - `slope_arrow → {kind:"path", closed:false, coords:[a,b]}` + `style_hints.inline_text.enabled=true, text="0.3%"`
- `finishObject()` 按工具分支，分别校验最少点数并构造上面对应结构。

**B. 交互（计划 §F5）**
- 圆/三角/标高点：**单击即建**（用默认或克隆样式），不要走多点折线。
- 转弯半径/坡度箭头：**两点成形**后立即建对象。
- 闭合/开放 path：多点 + 完成按钮/双击/Enter；完成按钮文案随工具变（多边形/线段/箭头）。

**C. 真正用上 `workbench_model.js`（堵死 #6）**
- 在 `index.html` 加载 `workbench_model.js`（在 `workbench.js` 之前）。
- `workbench.js` 改为调用其 `normalizeStyleHints / migrateLegacyObject / trianglePoints / sampleSegments / segmentsToPathD / defaultStyleForObjectType / buildLegendGroups / cloneStyle`，删掉重复的本地实现。默认样式一律走 `defaultStyleForObjectType`（接 registry `default_style`），删除 `objectStyle()` 的 5 类型硬编码。

**D. 检查器 + 配图面板（§F7/F8）**
- 按选中对象/工具显示相关控件：填充模式(none/translucent/solid/hatch)/填充色/不透明度/hatch 角度间距宽度/描边色与宽度/实虚线/边框(none/solid/dashed/double)+间距/起止箭头+尺寸/圆半径/三角尺寸+旋转/标注框(文本/尺寸/字号/不透明度/偏移)/内联文字(文本/字号/位置/偏移)。不相关控件不要对每个工具都显示。
- 含 `supporting_images` 工具的图纸显示配图面板：上传/列表(缩略图+caption+notes+排序+删除)，走 §6 B3 的 supporting API。配图**不进画布、不进 semantic JSON**。

**E. 渲染兜底**：`renderObjectSvg` 对 circle/triangle 必须在缺 center/radius/size 时安全跳过或用默认，禁止因单个坏对象让整个 overlay 抛异常。

**F. 回归**：`functional_zoning` 现有体验、弧线 handle、旧 JSON 加载**必须不破**。

### 升级后的验收门禁（这是关键 —— 没有它返工还会再跑偏）

**把浏览器/DOM smoke 从 best-effort 升级为硬门禁**，且必须真正驱动 UI：

1. **环境**：在 Windows 执行机上安装 Playwright（`pip install playwright` + `playwright install chromium`）作为本任务的一部分；**"没装"不再是 skip 的理由**。
2. **给前端加确定性测试钩子**：在 `workbench.js` 暴露 `window.DrawingWorkbenchTest = { createObject(toolId, points), getObjects(), getActiveDrawingType() }`，让 smoke 能脱离视觉、确定性地建对象。
3. **smoke 必过断言**（遍历每个 enabled 图纸类型）：
   - 点该图纸 tab → 断言 `#drawingSpecificTools` 渲染出**该图纸专属工具**（而非通用 4 字段表单），且工具集合 = registry `tools`。
   - 对该图纸每种几何，用钩子建 1 个对象 → 断言对象数 +1，且 `geometry.kind ∈ {path,circle,triangle}`（**断言不出现 `closed_path/open_path`**）。
   - 保存 → 重载 → 断言对象仍在、kind 正确、turning_radius 带 label_box、slope_arrow 带 inline_text。
   - 整个流程 **console 无 error**。
4. **廉价兜底断言**（加进 Python/Node 测试，防回归）：`index.html` 含 `workbench_model.js`；`workbench.js` 引用 `DrawingWorkbenchModel`。

### 完成定义（全满足才算完成）

- [ ] A–F 全部落地，9 张非 FZ 图纸各自有专属工具/样式/几何，互不相同。
- [ ] `functional_zoning` 回归不破（旧 JSON 加载、弧线、填充控件）。
- [ ] 升级后的浏览器/DOM smoke **作为硬门禁通过**（上述 1–3）。
- [ ] §12 原有硬门禁（py_compile / 三个 node --check / unittest / Node 模型测试 / API smoke / validate_record）仍全过。
- [ ] `workbench_model.js` 被加载且被引用（兜底断言 4 通过）。
- [ ] `git status` 不含 `projects/26-BQ-PARK/05_output/` 输出脏文件。

实施请分提交（A+B / C / D+E / 门禁 各一次），回推后 mac claude 做最终审 + 看升级门禁实际输出。

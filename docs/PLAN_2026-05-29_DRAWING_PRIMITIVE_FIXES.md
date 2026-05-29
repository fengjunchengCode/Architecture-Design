# 绘图图元第五轮修复 brief（mac claude 审 round-4 → 6 条返工）

> **执行者：codex（有视觉）。单线程顺序执行,每条一个提交。不要开并行子 agent**——6 条几乎全改 `workbench.js` 同几个函数且互相耦合,并行只会冲突。
> 针对 `origin/main @ 3483132`。开工前 `git pull --ff-only`。
> 红线沿用前四轮:**功能分区(FZ)行为逐像素不变**;结构不得新增平行路径;改完跑全门禁 + 截图自检。
> **不要改 `docs/CLAUDE_CODEX_REVIEW_THREAD.md`**(审阅线程留给 mac claude)。

**背景**：round-4 统一交互层后,用户实测发现 6 个渲染/交互问题。本轮逐条修。文件几乎都在 `_tools/uploader/static/workbench/workbench.js`,门禁在 `_tools/tests/drawing_workbench_browser_smoke.py`。

---

## F1：拖线段中点成弧后冒出一堆白色顶点(回归)

**根因**：`renderObjectSvg` 给顶点 handle 喂的是 `objectPathCoords(obj)` = `Model.sampleSegments(...)` 的**采样点**(闭合分支 2545、开放分支 2572)。一段直线变 quadratic 后被采样成 16 点(`sampleSegments` STEPS=16）→ 弧上冒出十几个白点。

**Files:** `workbench.js`（2545、2572；新增取顶点的 helper）

- [ ] **Step 1（先红）**：冒烟新增 `assert_arc_no_phantom_handles`：建一条 3 点线段→选中→拖第一段中点成弧→断言 `.geometry-vertex-handle` 数量 == 折线**顶点数**(本例 3),不随弧采样暴涨。
- [ ] **Step 2**：跑测试确认 FAIL。
- [ ] **Step 3（修）**：顶点 handle 必须画在**真实顶点**,不是采样曲线。新增 `function objectVertexPoints(obj)`：有 `segments` → 取每段 `from` + 最后一段 `to`(闭合则不重复首点);否则取 `geometry.coords`。把 2545/2572 的 `renderSharedVertexHandles(closedCoords/coords, ...)` 改为传 `objectVertexPoints(obj)`。`renderSharedPathHitLayer` 和路径 `d`/polyline **仍用采样坐标**(命中/绘制不变)。
- [ ] **Step 4**：跑测试 PASS;FZ 回归断言仍绿(FZ 多边形顶点 handle 数 == 顶点数)。
- [ ] **Step 5**：codex 截图——线段/多边形拖边成弧,弧上不再有白点,只在真实顶点有 handle。
- [ ] **Step 6**：`git commit -m "fix(workbench): place vertex handles on real vertices, not sampled curve points"`

## F2：线段虚线是"圆点"质感,与多边形不一致

**根因**：开放路径用了 `stroke-linecap="round"`(2561/2566),叠加 `stroke-dasharray` → 每节虚线被圆头帽撑成圆点;多边形不用 round cap,是方块虚线。

**Files:** `workbench.js`（2561、2566）

- [ ] **Step 1（修）**：开放路径渲染时,**虚线用 butt cap**:`stroke_style==="dashed"` 时不要 `stroke-linecap="round"`(实线可保留 round 让端点圆润);或统一去掉 round cap 与多边形看齐。`stroke-linejoin="round"` 保留。
- [ ] **Step 2**：`node --check` + 冒烟 PASS。
- [ ] **Step 3**：codex 截图——线段虚线与多边形虚线**同款方块虚线**。
- [ ] **Step 4**：`git commit -m "fix(workbench): dashed open paths use butt cap to match polygon dash texture"`

## F3：三角"旋转即缩放"——拆开旋转/缩放(回归)

**根因**：`vertexDrag` 三角分支(2873-2874)用**同一个角点 handle** 同时算 `size = radius*1.5` 与 `rotation_deg = atan2(...)`,拖一下两者一起变。

**Files:** `workbench.js`（三角 handle 渲染 2497-2502；`vertexDrag` 2857-2875）

- [ ] **Step 1（先红）**：冒烟 `assert_triangle_rotate_no_scale`：建三角→记 `size`→拖**旋转手柄**转一定角度→断言 `rotation_deg` 变、`size` **不变**(容差 1e-4)。
- [ ] **Step 2**：跑测试 FAIL。
- [ ] **Step 3（修）**：三角选中时渲染**两个**功能区分的手柄(用 `roles` 区分):一个顶点角色 `triangle-rotate`(拖动只改 `rotation_deg`,半径固定),一个 `triangle-size`(沿径向拖只改 `size`,角度固定)。`vertexDrag` 按 `role` 分流:`triangle-rotate` 只写 `rotation_deg=atan2(...)`;`triangle-size` 只写 `size`。圆形保持 `circle-center`/`circle-radius` 两手柄(已正确)。
- [ ] **Step 4**：跑测试 PASS。
- [ ] **Step 5**：codex 截图——三角旋转时尺寸不变,缩放时角度不变。
- [ ] **Step 6**：`git commit -m "fix(workbench): split triangle rotate/resize into separate handles"`

## F4：圆非正圆/三角非等边/形变——纵横比补偿

**根因**：`index.html:310` `<svg viewBox="0 0 1 1" preserveAspectRatio="none">` 把单位正方形拉伸填满非正方形画布,参数化的 `<circle>`/`trianglePoints` 被压扁。**用户拍板:做纵横比补偿(不改底图铺满)。** 现成范例:handle 已用 `getHandleRadiusX()=px/W`、`getHandleRadiusY()=px/H` 渲成屏幕正圆。

**Files:** `workbench.js`（圆 2464-2467、三角 2482-2494;新增 `aspectK()`）

- [ ] **Step 1**：新增 `function aspectK(){ const s=$("#workbenchStage"); const r=s&&s.getBoundingClientRect(); return r&&r.height? r.width/r.height : 1; }`
- [ ] **Step 2（圆）**：把圆的 `<circle cx cy r>` 改为 `<ellipse cx cy rx="${r}" ry="${r*aspectK()}">`(内圈双线同理)。命中层 `renderSharedCircleHitLayer` 同步改 ellipse,保证点选范围跟随。
- [ ] **Step 3（三角）**：渲染前对 `Model.trianglePoints(...)` 的每个点做 y 补偿:`y' = cy + (y - cy) * aspectK()`(内圈双线、命中层、顶点/旋转手柄位置都用补偿后的点)。
- [ ] **Step 4（重渲染）**：画布尺寸变化时形状要重算——确认 resize/zoom 时会 `renderCanvasLayers`(若无,挂一个 `ResizeObserver(#workbenchStage)` → 重渲染)。
- [ ] **Step 5**：冒烟新增 `assert_circle_round`：建圆→读 `<ellipse>` 的 `rx`、`ry`,断言 `ry/rx ≈ 渲染时 W/H`(即屏幕上近似正圆,容差 5%)。`node --check` + 全门禁 PASS。
- [ ] **Step 6**：codex 截图——圆呈正圆、三角呈等边(目测 + 量屏幕像素)。
- [ ] **Step 7**：`git commit -m "fix(workbench): aspect-ratio compensation so circles render round and triangles equilateral"`

## F5：坡度文本从右往左/斜画时方向与位置错乱

**根因**：`renderSemanticTextOverlays`(2295-2296)直接 `rotate(Model.lineAngleDeg(coords))`。R→L 时 angle≈180° 文字倒转;斜画角度未归正、offset 在未旋转坐标硬加 → 位置乱。

**Files:** `workbench.js`（2289-2296）

- [ ] **Step 1（修）**：① 角度**归正到始终正立**:`let a = Model.lineAngleDeg(coords); if (a > 90 || a < -90) a += 180;`(再 `%360`)。② offset 改沿线**法向**偏移:法向 `n = [-dyN, dxN]`(单位化的线方向旋 90°),`x = base + n[0]*off`、`y = base + n[1]*off`,默认 off 取原 `-0.018` 量级,使文字浮在线**上方**而非乱跳。③ `text-anchor="middle"`,`x/y` 为锚点,使文字居中于该点。④ 纵横比:法向偏移的 y 分量乘 `aspectK()` 以免斜线上偏移被拉伸(复用 F4 的 `aspectK`)。
- [ ] **Step 2**：冒烟 `assert_slope_text_upright`:分别从左→右、右→左、对角画坡度箭头,断言文本 `transform` 归一后的角度 ∈ [-90,90]。
- [ ] **Step 3**：跑测试 PASS。
- [ ] **Step 4**：codex 截图——三种方向画坡度箭头,文字都正立、贴线、位置稳定。
- [ ] **Step 5**：`git commit -m "fix(workbench): keep slope-arrow inline text upright and normal-offset across directions"`

## F6：线段去掉自动标签 + 新增可拖拽"文字工具"

**根因**：开放路径走 `plainLabel = renderSvgLabel(obj.label, labelPoint,...)`(2579),`labelPoint` 取中间采样点,不可调。用户要:线段别自动加文本;改为独立、可移动的文字对象。

**Files:** `workbench.js`（plainLabel 2578-2579;`TOOL_GEOMETRY` 28;`PRIMITIVE_STYLE_SPEC`;工具注册/标签 10-35;`renderObjectSvg` 新增 text 分支;`vertexDrag` 复用点拖拽）;按需 `index.html` 工具按钮

- [ ] **Step 1（去自动标签）**：`renderObjectSvg` 中开放路径(及一般几何)**默认不渲染 plain label**——只有 `label_box`/`inline_text` 这类显式语义文本才渲染。`functional_zone` 行为不变。
- [ ] **Step 2（新文字工具)**：新增工具/对象类型 `text_label`:
  - `TOOL_GEOMETRY.text_label = { kind: "text", minPoints: 1 }`;`TOOL_LABELS.text_label = "文字"`;在需要的图纸 registry tools 里加入(与 supporting_images 同级别的通用工具)。
  - 几何:`{ kind:"text", coords:[[x,y]] }`,点击画布即落点创建。
  - `PRIMITIVE_STYLE_SPEC.text_label = { color:true, textContent:true, fontSize:true }`;控件:文本输入 + 字号 range + 颜色(复用统一控件)。
  - 渲染:`renderObjectSvg` 加 `geo.kind==="text"` 分支 → `<text x y text-anchor="middle" fill=color font-size=fs data-object-id=id>...`;选中渲染**一个可拖拽顶点 handle**(role `text-anchor`)。
  - 拖拽:`vertexDrag` 加 `role==="text-anchor"` → 更新 `geometry.coords[0]`,**位置随意可调**。
- [ ] **Step 3**：冒烟 `assert_text_tool`:① 画一条线段→断言无 plain `<text>` 自动标签;② 选"文字"工具→画布点一下→断言生成 `kind==="text"` 对象且渲染出 `<text>`;③ 选中拖动 handle→断言 `coords[0]` 改变。
- [ ] **Step 4**：`node --check` + 全门禁 PASS。
- [ ] **Step 5**：codex 截图——线段无自动文字;文字工具可放置、可拖到任意位置、可改字号/颜色。
- [ ] **Step 6**：`git commit -m "feat(workbench): drop auto line label; add draggable text tool"`

## F7：图例预览全显示"暂无功能分区"——通用化

**根因**：`renderFunctionalZoneLegendPreview`(1402-1405)只统计 `type==="functional_zone"`,空时硬编码"暂无功能分区";但 `#zoneLegendPreview` 对所有图纸都渲染它(741)。

**Files:** `workbench.js`（`buildFunctionalZoneLegendGroups` 1375、`renderFunctionalZoneLegendPreview` 1402、调用点 741/`refreshLegendPreview`）

- [ ] **Step 1（修）**：图例分组通用化——FZ 图纸按 `functional_zone` 分组(现状);**非 FZ 图纸**按当前图纸**所有可见对象**的 `(type + 关键样式)` 分组,图例名取 `legend_label`/`label`。空文案改为中性「暂无图例对象」,不写死功能分区。可保留两套分组函数但由 `isFunctionalZoning()` 选择(这是合法的类型路由,不算平行渲染)。
- [ ] **Step 2**：冒烟 `assert_legend_non_fz`:在某非 FZ 图纸建 2 个不同类型对象→断言图例预览出现对应条目,不显示"暂无功能分区"。
- [ ] **Step 3**：全门禁 PASS。
- [ ] **Step 4**：codex 截图——新图纸图例预览正确列出对象。
- [ ] **Step 5**：`git commit -m "fix(workbench): generalize legend preview for non-FZ drawings"`

---

## 验收红线（mac claude 最终审逐条看实际输出 + 截图）

1. **F1**：弧线上无幻影白点,handle 数 == 真实顶点数(`assert_arc_no_phantom_handles`)。
2. **F2**：线段虚线 = 多边形虚线质感(butt cap)。
3. **F3**：三角旋转不改尺寸、缩放不改角度(`assert_triangle_rotate_no_scale`)。
4. **F4**：圆呈正圆、三角等边(`assert_circle_round`,屏幕量测)。
5. **F5**：坡度文本三方向(L→R/R→L/对角)均正立贴线(`assert_slope_text_upright`)。
6. **F6**：线段无自动标签;文字工具可放置 + 拖动改位置(`assert_text_tool`)。
7. **F7**：非 FZ 图纸图例预览正确(`assert_legend_non_fz`)。
8. **FZ 回归(红线)**：所有改动后,FZ 多边形创建/收口/选中/弧线/图例**逐像素不变**;既有门禁(py_compile/node --check/API smoke/validate_record)全过。

## 交付

- F1→F7 各一次提交,信息如上,**顺序执行**。
- 回推后通知 mac claude 终审。

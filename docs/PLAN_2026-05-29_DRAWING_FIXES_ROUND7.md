# 绘图图元第七轮修复 brief（mac claude 审 round-6 → 8 条）

> **执行者：codex（有视觉）。单线程顺序执行,每条一个提交。不要开并行子 agent。**
> 针对 `origin/main @ 68e27d4`。开工前 `git pull --ff-only`。
> 红线:**FZ 行为逐像素不变**;不得新增平行路径;改完跑全门禁 + 截图自检。**不要改 `docs/CLAUDE_CODEX_REVIEW_THREAD.md`**。
> **两处产品决策(用户已定,第二版)**:① 样式预设 = **内置一批写死的预设(参照 PDF 图例风格)** + **用户另存的预设按项目存(后端,`projects/<code>/05_output/drawings/presets.json`)**,不用 localStorage;② **删除"对象类型"**——每个工具直接生成一个通用几何类型,去掉检查器里的对象类型下拉(图例已与类型脱钩)。

---

## H1：标签文本失效——非 FZ 也要绑定 + 改样式不清空（先修,其他依赖它）

**根因**：① 非 FZ `objectLabel` 输入框(804)无 `value=`;② 标签事件被 `if (isFunctional)`(1237)限定 → 非 FZ 对象标签**从不绑定**,只创建时读一次,改样式一重渲染就空。

**Files:** `workbench.js`(804、1236-1252、updateStyle/renderSpecificTools)

- [ ] **Step 1(先红)**：冒烟 `assert_label_persists`:建一个非 FZ 对象设 label="主入口"→选中→改填充色→断言对象 `label` 仍为"主入口"且输入框回填该值。
- [ ] **Step 2**：跑测试 FAIL。
- [ ] **Step 3(修)**：① 非 FZ 标签框补 `value="${escapeHtml(selected ? selected.label||"" : draftLabel||"")}"`;② 标签 input/change 绑定去掉 `isFunctional` 限定,对所有类型生效:选中对象时写 `selected.label`、未选中时写 draftLabel;③ 确认 `updateStyle` 只改 `style_hints`,**绝不动 `label`**,且重渲染从对象读回 label。
- [ ] **Step 4**：跑测试 PASS;codex 截图——改各项样式标签都不丢。
- [ ] **Step 5**：`git commit -m "fix(workbench): bind object label for all types; never clear on style change"`

## H2：图例跟随标签文本、按样式合并（与对象类型脱钩）

**根因**：`legendGroupKey`(workbench_model.js)以 `obj.type` 为首要键,图例名回退类型名(`renderGenericLegendPreview` 1574)。

**Files:** `workbench_model.js`(`legendGroupKey`、`buildLegendGroups`)、`workbench.js`(1574 取名)

- [ ] **Step 1**：`legendGroupKey` **去掉 `obj.type`**,只用 `geometry.kind + 关键样式参数`(沿用现有 per-kind 参数列表:fill_mode/fill_color/opacity/border/stroke_color/stroke_width/dash_scale/箭头 等)。同样式 → 同组(跨类型也合并)。
- [ ] **Step 2**：组的展示名 = **该组第一个创建对象的 `label`**(无 label 再回退几何名,不要回退类型名)。`buildLegendGroups` 保留每组首个对象引用以取 label。
- [ ] **Step 3**：冒烟 `assert_legend_by_label`:建两个不同"类型"但样式相同、label="车行"的对象→断言图例**合并为 1 条**且名为"车行";改其中一个线宽→断言**拆成 2 条**。全门禁 PASS。
- [ ] **Step 4**：`git commit -m "fix(workbench): legend groups by style+label, decoupled from object type"`

## H3：标注框——白色半透明、无边框、直角、更透明

**根因**：label_box 渲染(2516)`rx="0.004"` 圆角 + `stroke` 边框 + opacity 默认 0.82 偏不透明。

**Files:** `workbench.js`(2516;控件默认 1211)

- [ ] rect 改:`rx="0"`(直角)、**去掉 `stroke`**(无边框)、`fill="#FFFFFF"`、`fill-opacity` 默认降到 **0.55**(控件 `labelBoxOpacity` 默认与 min 同步调,允许更透明)。文字仍用对象描边色。
- [ ] 冒烟 `assert_labelbox_style`:label_box rect 无 `stroke`/`rx`=0/opacity≈0.55。全门禁 PASS。codex 截图。
- [ ] `git commit -m "fix(workbench): label box white translucent, no border, square corners"`

## H4：标高三角默认倒三角 + 文本在正上方 + 图例含三角与文本框

**Files:** `workbench.js`(elevation 默认几何 430/2215;文本叠加;`renderGenericLegendSwatch`)、`workbench_model.js`(elevation 默认)

- [ ] elevation_marker 默认 `rotation_deg = 180`(倒三角);entrance_marker 维持正三角。
- [ ] 标高 label_box/文本默认 offset 让文字浮在**倒三角正上方**。
- [ ] 图例 swatch:elevation 组画**倒三角 + 旁边一个小白底框**(体现"三角+标高文本"组合)。
- [ ] 冒烟 `assert_elevation_inverted`:elevation 默认 `rotation_deg==180`;图例 swatch 含三角+rect。全门禁 PASS。codex 截图。
- [ ] `git commit -m "feat(workbench): elevation marker defaults to inverted triangle with label above; legend shows triangle+box"`

## H5：三角旋转手柄改标准圆形小箭头

**根因**：triangle-rotate 手柄现为普通椭圆点(2846)。

**Files:** `workbench.js`(三角选中渲染 ~2846;新增 `renderRotateHandle`)

- [ ] 新增 `renderRotateHandle(x, y, objectId)`:画一个**小圆 + 环绕弧形箭头**图标(标准旋转图标,参考 PS/PPT),`data-vertex-role="triangle-rotate"`,纵横比用 `aspectK` 保持圆形。位置在顶点沿 size 方向外延一截。
- [ ] 拖拽逻辑(3238 `triangle-rotate`)不变,只换外观。
- [ ] codex 截图——旋转手柄是圆形小箭头、不丑、好点。全门禁 PASS。
- [ ] `git commit -m "feat(workbench): circular-arrow rotate handle for triangle"`

## H6：箭头随线宽缩放

**根因**：`arrow_size` 固定默认 0.028,与 `stroke_width` 无关(2448)。

**Files:** `workbench.js`(`renderArrowHead` 2448;箭头控件)

- [ ] 箭头尺寸改为**随线宽**:`const size = (Number(style.arrow_size) || (style.stroke_width||0.004) * 6)`;即默认按 `stroke_width * 6`(可 clamp 到 [0.012, 0.06]),用户未显式设 arrow_size 时跟随线宽;细线小箭头、粗线大箭头。箭头控件标签注明"随线宽,可覆盖"。
- [ ] 冒烟 `assert_arrow_scales`:线宽 0.002 与 0.012 两个箭头对象,断言后者箭头三角形显著更大。全门禁 PASS。codex 截图——细/粗线箭头比例协调。
- [ ] `git commit -m "fix(workbench): arrowhead size scales with stroke width by default"`

## H7：对象支持拖动移动 + 复制粘贴（新功能）

**Files:** `workbench.js`(`bindOverlaySelection`/命中层 pointer 事件;键盘处理器;state)

- [ ] **拖动移动**：在对象命中层(`.geometry-hit`)上 `pointerdown` → 进入 `state.moveDrag`(objectId, 起点);`pointermove` 超过阈值后,把该对象**所有坐标平移**(path:coords/segments 全平移;circle/triangle:center;text/label:coords;含弧线 control 点)Δ(屏幕→viewBox,x/y 各自换算);`pointerup` 落定 + `markDirty`。与顶点/弧线手柄拖拽互斥(手柄优先)。
- [ ] **复制粘贴**：`Ctrl/Cmd+C` 选中对象存 `state.clipboard`(深拷贝);`Ctrl/Cmd+V` → 克隆、新 `nextObjectId()`、所有坐标偏移一小段(如 +0.02,0.02)、选中新对象、`pushUndoSnapshot`。`editable` 焦点时不拦截。
- [ ] 冒烟 `assert_move_and_paste`:① 选中对象 → 模拟在命中层拖动 → 断言坐标整体平移;② 触发复制粘贴 API → 断言对象数 +1 且新对象坐标有偏移。全门禁 PASS。codex 截图——拖动平移、粘贴出副本。
- [ ] `git commit -m "feat(workbench): drag-to-move and copy/paste for objects"`

## H8：整套样式预设——内置批次（写死,参照 PDF 图例）+ 用户另存（按项目,后端）

**Files:** `workbench.js`(样式控件加"预设"块 + 内置常量 + 调后端);`_tools/drawing_workbench/`(预设存取 + API);`_tools/uploader/*`(路由)

- [ ] **Step 1 内置预设(写死)**：`workbench.js` 加 `BUILTIN_STYLE_PRESETS`,一批参照 `docs/reference_pdfs/report_examples/` 图例风格的整套样式(每条 = `{ id, name, kind, hints }`)。至少覆盖:车行-橙红实线(end_arrow)、人行-钴蓝实线(end_arrow)、地下-蓝虚线、消防-正红线、转弯半径-深青+白底框、景观节点-暖橙描边半透圆、主轴-红虚线、次轴-紫虚线、出入口-朱红实心三角、标高-紫倒三角、坡度-深青箭头、种植区-饱和绿半透+深绿边、径流-深蓝、生态沟-青虚线。`hints` 用完整样式字段。
- [ ] **Step 2 后端按项目存**：新增预设存储 `presets.json`(项目目录 `05_output/drawings/presets.json`),复用 `task_pack.safe_project/project_dir` 防越界;字段 `[{ id, name, kind, hints, created_at }]`。加 API:`GET /api/drawing/presets?project=` 列出;`POST` 保存(校验 hints 走 `Model.normalizeStyleHints` 同源/或 style_schema);`DELETE` 删。
- [ ] **Step 3 UI**：样式控件顶部"预设"一节:① 内置 + 该项目用户预设合并列出,每项一个**预览 swatch**(复用 `renderGenericLegendSwatch`)+ 名称 + 应用 +(用户预设可删);② "保存当前为预设"输入名 → `POST` 存当前 draft 整套 hints;③ 应用 → `updateStyle` 用该 preset hints 覆盖当前工具/选中对象。
- [ ] **Step 4**：冒烟 `assert_style_presets`:① 内置预设渲染出列表+swatch;② 保存一个用户预设 → 重新 `GET` 仍在(写进项目文件);③ 应用某预设 → 当前 draft hints == 预设 hints。`py_compile` + `node --check` + 全门禁 PASS。codex 截图——内置批次预览、保存、套用。
- [ ] **Step 5**：`git commit -m "feat(workbench): built-in style presets + per-project saved presets"`

## H9：删除"对象类型"——工具直出通用几何类型

**根因/范围**：用户「对象类型没有意义了，直接删除」。当前检查器有"对象类型"`<select>`(789),每个工具下挂多个语义子类型(vehicle_flow/pedestrian_flow…);schema 按 `OBJECT_TYPE_REGISTRY` 校验 `type`。改为:**工具 = 几何,直接生成一个通用类型,无子类型选择**。

**Files:** `workbench.js`(对象类型下拉 789 及其绑定 811-816、`toolObjectTypes`/`selectedToolObjectType`、创建 `type` 赋值)；`_tools/drawing_workbench/registry.py`(object_types、通用类型)；`schema.py`(校验/兼容)；`registry.py` 各图纸 `object_types`

- [ ] **Step 1(后端通用类型 + 兼容)**：`OBJECT_TYPE_REGISTRY` 增加通用几何类型 `polygon / line / circle / triangle`(+保留 turning_radius/elevation_marker/slope_arrow/text_label 这些**行为型**工具类型);**旧语义类型(vehicle_flow 等)保留在 registry/别名里**,确保**旧存档仍能加载**(`normalize_object_type` 命中即放行)。各图纸 registry 的 `object_types` 收敛为该图纸用到的通用/行为类型(不再罗列语义子类型)。
- [ ] **Step 2(前端删下拉)**：删除"对象类型"label+`<select id="objectType">`(789)及其 change 绑定;`createObjectFromTool` 的 `type` 由**工具直接映射**:closed_path→`polygon`、open_path→`line`、circle→`circle`、triangle→`triangle`、turning_radius/elevation_marker/slope_arrow/text_label→同名。`PRIMITIVE_STYLE_SPEC`/预设/默认样式改为**按几何类型**键,不再按语义子类型。
- [ ] **Step 3(测试/兼容)**：冒烟 `assert_no_object_type_select`:检查器内 `#objectType` count==0;各工具建对象 `type` ∈ 通用集;旧存档(含 vehicle_flow 等)加载不报错(`assert_no_bad_kinds` 仍过)。后端 `test_drawing_workbench_schema.py` 增「通用类型校验通过 + 旧类型兼容」用例。`py_compile` + `node --check` + 全门禁 PASS。
- [ ] **Step 4**：codex 截图——检查器无"对象类型",选几何工具直接画+样式+标签。
- [ ] **Step 5**：`git commit -m "refactor(workbench): drop semantic object-type selector; tools emit generic geometry types"`

---

## 验收红线（mac claude 终审 + 截图）

1. H1 标签改样式不丢、非 FZ 可编辑;2. H2 图例按样式+标签合并、不跟类型;3. H3 标注框白·半透·无框·直角;4. H4 标高默认倒三角+文字上方+图例含框;5. H5 旋转手柄=圆形小箭头;6. H6 箭头随线宽;7. H7 可拖动移动+复制粘贴;8. H8 内置预设批次(参照 PDF)+ 用户预设按项目存、可预览/套用;9. H9 检查器无对象类型、工具直出通用几何、旧存档兼容。
10. **FZ 回归(红线)** + 既有门禁全过。

## 交付
- H1→H9 各一次提交,顺序执行(H1 先;H9 因改后端 schema/registry,建议放最后,改完重点验旧存档加载)。回推后通知 mac claude 终审。

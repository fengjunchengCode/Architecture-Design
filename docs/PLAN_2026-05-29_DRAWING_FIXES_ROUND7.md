# 绘图图元第七轮修复 brief（mac claude 审 round-6 → 8 条）

> **执行者：codex（有视觉）。单线程顺序执行,每条一个提交。不要开并行子 agent。**
> 针对 `origin/main @ 68e27d4`。开工前 `git pull --ff-only`。
> 红线:**FZ 行为逐像素不变**;不得新增平行路径;改完跑全门禁 + 截图自检。**不要改 `docs/CLAUDE_CODEX_REVIEW_THREAD.md`**。
> **两处产品决策(用户已定)**:① 样式预设存 **localStorage**(跨会话保留,无需后端);② **保留**"对象类型"内部模型,但**图例与类型脱钩**(按样式+标签合并)。

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

## H8：整套样式预设——保存 / 预览 / 应用（新功能,localStorage）

**Files:** `workbench.js`(样式控件区加"预设"块;localStorage 读写)

- [ ] 数据:`localStorage["wb_style_presets"]` = `[{ id, name, hints }]`,`hints` 为一整套样式(fill_mode/fill_color/fill_opacity/hatch/border_style/stroke_color/stroke_width/stroke_style/dash_scale/double_border_gap/箭头… 当前 `draftStyleFor` 的完整快照)。
- [ ] UI(样式控件顶部一节"预设"):① **保存当前为预设**(输入名→存当前 draft 整套 hints);② 预设列表,每项一个**小预览 swatch**(复用 `renderGenericLegendSwatch` 思路画该套样式)+ 名称 + 应用按钮 + 删除;③ 点"应用"→ `updateStyle` 用该 preset 的 hints 覆盖当前工具/选中对象样式。
- [ ] 跨会话:刷新后预设仍在(localStorage)。
- [ ] 冒烟 `assert_style_presets`:保存一个预设 → 列表出现且 swatch 渲染;改当前样式后点应用 → 当前 draft hints == 预设 hints。全门禁 PASS。codex 截图——保存、预览缩略、一键套用。
- [ ] `git commit -m "feat(workbench): save/preview/apply full style presets (localStorage)"`

---

## 验收红线（mac claude 终审 + 截图）

1. H1 标签改样式不丢、非 FZ 可编辑;2. H2 图例按样式+标签合并、不跟类型;3. H3 标注框白·半透·无框·直角;4. H4 标高默认倒三角+文字上方+图例含框;5. H5 旋转手柄=圆形小箭头;6. H6 箭头随线宽;7. H7 可拖动移动+复制粘贴;8. H8 预设可存/预览/套用且跨会话。
9. **FZ 回归(红线)** + 既有门禁全过。

## 交付
- H1→H8 各一次提交,顺序执行(H1 先,其余依赖标签修复)。回推后通知 mac claude 终审。
- 待确认项:若用户要"去掉对象类型下拉"或"预设改后端存储",再追加任务。

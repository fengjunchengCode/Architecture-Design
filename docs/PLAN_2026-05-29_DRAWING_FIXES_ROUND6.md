# 绘图图元第六轮修复 brief（mac claude 审 round-5 → 收尾问题）

> **执行者：codex（有视觉）。单线程顺序执行,每条一个提交。不要开并行子 agent**(全改 `workbench.js` 同几个函数,耦合)。
> 针对 `origin/main @ f705754`。开工前 `git pull --ff-only`。
> 红线:**功能分区(FZ)行为逐像素不变**;不得新增平行路径;改完跑全门禁 + 截图自检。
> **不要改 `docs/CLAUDE_CODEX_REVIEW_THREAD.md`**。
> 风格依据:`docs/reference_pdfs/report_examples/`(报告标注用暖色高饱和——橙/琥珀圈注、红色红线、金色标题——压在绿/灰底总平面上醒目;现默认淡绿与底图糊作一团)。

---

## G1：所有虚线的分段密度可调

**根因**：虚线 `stroke-dasharray` 全硬编码 `"0.014 0.01"`。

**Files:** `workbench.js`(各 `stroke-dasharray` 处;`PRIMITIVE_STYLE_SPEC`;统一控件)

- [ ] 样式加字段 `dash_scale`(默认 1)。所有虚线 dasharray 改为 `${0.014*scale} ${0.01*scale}`(线/多边形/圆边框统一)。
- [ ] 控件:线型=虚线时,出现"虚线密度" range(0.4–2.5, step 0.1),写 `dash_scale`。图例 swatch 同步。
- [ ] 冒烟 `assert_dash_scale`:改 `dash_scale` → 可见图形 `stroke-dasharray` 随之变。`node --check` + 全门禁 PASS。
- [ ] `git commit -m "feat(workbench): adjustable dash density (dash_scale)"`

## G2：线段图例画成了弧线 → 改直线

**根因**：开放路径图例 swatch 硬编码贝塞尔曲线 `d="M3 11 C8 4, 15 4, 21 9"`(workbench.js:1560)。

**Files:** `workbench.js`(1559-1566)

- [ ] 开放路径 swatch 改**直线**:`<line x1="3" y1="8" x2="21" y2="8" .../>`(虚线/线宽/颜色照样式;若该类型有终点箭头,末端补一个小三角)。
- [ ] 冒烟 `assert_line_legend_straight`:线段图例 svg 内有 `<line>` 或直 `<path>`,无曲线 `C`。全门禁 PASS。
- [ ] `git commit -m "fix(workbench): straight line swatch in legend (was bezier arc)"`

## G3：箭头从端点出发 + 修畸变(线/坡度共用)

**根因**：`renderArrowHead` 的 `angle` 在 viewBox 单位算(未纵横比补偿)→ 斜画畸变(只有水平/垂直对);箭尖 `p1=tip` 压在端点 + 线画到端点 → 重叠,线粗就露。

**Files:** `workbench.js`(`renderArrowHeads`/`renderArrowHead`;开放路径渲染 2554-2569)

- [ ] **Step 1(先红)**：冒烟 `assert_arrow_geometry`:画一条斜向(非水平/垂直)带终点箭头的线→断言箭头三角形**朝向沿屏幕方向**(用 `aspectK` 校正后角度与屏幕线角度一致, 容差 5°);并断言线的末端坐标**短于**原始端点(留出箭头长度)。
- [ ] **Step 2**：跑测试 FAIL。
- [ ] **Step 3(修)**：
  - 箭头几何用屏幕度量算:把方向向量按 `aspectK()` 校正(`dyScreen = dy*?`)再算角度,`back`/`side` 分量也按 aspectK 反映射回 viewBox,使屏幕上箭头不畸变、对称。
  - 线**截短到箭头根部**:渲染开放路径前,若末端(或起点)有箭头,把该端点沿线回退 `arrow_size`(屏幕度量),让线止于箭头底边、箭头从真端点长出,不重叠。
- [ ] **Step 4**：跑测试 PASS;codex 截图——水平/垂直/斜向三种箭头都对称、从端点出发、线粗也不露馅。
- [ ] **Step 5**：`git commit -m "fix(workbench): aspect-correct arrowheads emanating from trimmed endpoint"`

## G4：坡度文字永远在线段上方

**根因**：法向偏移符号跟画线方向走,换方向就翻到下面。

**Files:** `workbench.js`(`renderSemanticTextOverlays` inline_text 分支)

- [ ] 计算法向后,**强制取屏幕"向上"那一侧**:若法向 y 分量 > 0(屏幕向下),取反。文字始终浮在线**上方**,与画线方向无关。角度归正(round-5 已做)保留。
- [ ] 冒烟 `assert_slope_text_above`:L→R / R→L / 对角三种,文字锚点 y < 线中点 y(屏幕更靠上)。全门禁 PASS。
- [ ] `git commit -m "fix(workbench): slope text always above the line regardless of direction"`

## G5：三角形 PS/PPT 式旋转/缩放手柄

**根因**：现旋转/缩放手柄不好用(round-5 拆成两点但非标准交互)。

**Files:** `workbench.js`(三角选中渲染 2497-2502;`vertexDrag` role 分支)

- [ ] 选中三角形时:**三个角点 = 缩放点**(role `triangle-size`,拖动改 `size`、角度不变);并在**顶点上方浮出一个标准旋转按钮**(role `triangle-rotate`,小圆+连接线图标,位置 = 顶点沿 size 方向再外延一截,参考 PS/PPT),拖动只改 `rotation_deg`。
- [ ] `vertexDrag`:`triangle-size` 只写 size;`triangle-rotate` 只写 rotation_deg(round-5 已分流,调整手柄外观/位置)。
- [ ] 冒烟保持 `assert_triangle_rotate_no_scale`;codex 截图——旋转按钮浮在三角上方、像 PS/PPT,三个角缩放、按钮旋转。
- [ ] `git commit -m "feat(workbench): PS/PPT-style triangle rotate handle + corner resize"`

## G6：标注框统一白色半透明、可拖动且与图元成组(转弯半径/标高)

**根因**：label_box 现用对象色填充;且不可拖动;标高框未默认在三角正上方。

**Files:** `workbench.js`(`renderSemanticTextOverlays` label_box 分支 2271-2283;`vertexDrag`;elevation 默认 offset)

- [ ] label_box 矩形改 **白底 `fill="#FFFFFF"` + `fill-opacity≈0.82`**;**文字与箭头/描边同色**(`stroke_color`)。
- [ ] 标注框**可拖动**:渲染一个 box 拖拽 handle(role `labelbox`),拖动改 `label_box.offset`(相对锚点),从而与转弯半径箭头/标高三角**成组**(同对象,一起选中/删除/移动锚点)。
- [ ] 标高点(elevation_marker)`label_box` 默认 offset 让框**居中浮在三角正上方**。
- [ ] 冒烟 `assert_labelbox_white_draggable`:label_box rect `fill` 为白、文字为 stroke_color;拖 handle → offset 变。全门禁 PASS。codex 截图。
- [ ] `git commit -m "fix(workbench): white translucent label box, draggable and grouped with marker"`

## G7：去掉"来源"下拉(无意义)

**根因**：`workbench.js:795-797` 的"来源"`<select>`,创建时永远默认 `user_sketch`(2248)。

**Files:** `workbench.js`(795-798、2205、2248)

- [ ] 删除"来源"label+`<select id="objectSource">`;创建对象 `source` 恒为 `"user_sketch"`;删 `objectSource` 读取。`SOURCE_OPTIONS` 若无其他引用一并删。
- [ ] `node --check` + 全门禁 PASS(若有断言依赖该下拉,更新)。
- [ ] `git commit -m "chore(workbench): remove meaningless source dropdown"`

## G8：文字工具做明显 + 确认可用

**根因**：文字工具已实现+测试,但用户在 UI 里找不到(疑似工具格拥挤/测在功能分区图)。

**Files:** `workbench.js`(工具格渲染 766-782)；`workbench.css`

- [ ] 工具格 `tool-grid` 确保所有工具按钮都完整可见(不换行截断/不溢出隐藏);"文字"按钮加可辨识图标(T)。
- [ ] 自查:每张含 `text_label` 的图纸(除功能分区)进入后工具格都显示"文字"按钮。
- [ ] 冒烟保持 `assert_text_tool` 全绿;codex 截图——某非 FZ 图纸里"文字"按钮可见、可放置、可拖动改位置。
- [ ] `git commit -m "fix(workbench): make text tool discoverable in tool grid"`

## G9：项目加载时注入 PPT 风格高对比预设(收尾,最重)

**根因**：默认色淡绿,与绿/灰底图糊作一团,每次进工作台都要手调。需:加载时按类型给一批**高饱和、互补于绿底、彼此区分**的预设(暖色为主呼应 PPT 金/橙/红 + 必要冷色),进台即用。

**Files:** `workbench_model.js`(`_STYLE_OVERRIDES`)；按需 `workbench.js`(加载时确保新对象/草稿用这批默认)

- [ ] 把 `_STYLE_OVERRIDES` 各类型默认色改为下表(起点,codex 可微调更协调,最终以截图在绿底上**清晰醒目**为准)：
  - 车行流线 vehicle_flow：`#E8551E`(橙红, end_arrow)
  - 人行流线 pedestrian_flow：`#1F6FE0`(钴蓝, end_arrow)
  - 地下通道 underground_flow：`#1F6FE0` 虚线
  - 消防车道 fire_route_line：`#E11D1D`(正红)
  - 转弯半径 turning_radius：`#0E9594`(深青) 箭头+白底框
  - 景观节点 landscape_node / 圆形：边框 `#F08A24`(暖橙) 半透明白填充
  - 景观主轴 landscape_axis_primary：`#E11D1D` 虚线；次轴 secondary：`#7B2FF0`(紫) 虚线
  - 出入口三角 entrance_marker：`#E03020`(朱红, 实心)
  - 标高三角 elevation_marker：`#7B2FF0`(紫, 实心)
  - 坡度箭头 slope_arrow：`#0E7C86`(深青)
  - 种植区 planting/key_planting：填充半透明 `#7CB342`、边框 `#2E7D32`(比现状更饱和的绿,与底图拉开)
  - 海绵/径流 runoff_line：`#1565C0`(深蓝)；生态沟 ecological_ditch_line：`#00897B`(青) 虚线
  - 设施/无障碍/人防 区:半透明填充用各自高饱和色 + 深色边框,避免淡绿
  - 文字 text_label：`#1A1A1A`(深灰,保证可读)
  - **互补/区分原则**:同一图纸内各类型色相尽量拉开;暖色(橙红紫)与绿底互补、醒目;冷色(蓝青)留给水/人行/地下。
- [ ] 进入工作台/新建对象时,草稿样式取上述类型默认(确认 `draftStyleFor`/`lastStyles` 初值走 `Model.normalizeStyleHints(type)`,无对象时即为该预设)。
- [ ] 冒烟 `assert_preset_not_pale`:新建各类型对象,断言其默认 `stroke_color`/`fill_color` ≠ 旧淡绿 `#DCE8C8`/`#7AA35A`(种植类除外)。全门禁 PASS。
- [ ] codex 截图——在 `启泰_master_plan_render.jpg` 之类绿底上各放一个图元,目视清晰醒目、彼此区分、风格与 PPT 暖色调协调。
- [ ] `git commit -m "feat(workbench): inject PPT-style high-contrast complementary presets at load"`

---

## 验收红线(mac claude 终审 + 截图)

1. G1 虚线密度可调;2. G2 线段图例为直线;3. G3 箭头从端点出发、三方向不畸变;4. G4 坡度文字恒在线上方;5. G5 三角 PS/PPT 旋转按钮+三角缩放;6. G6 标注框白底半透明、可拖、成组;7. G7 无来源下拉;8. G8 文字工具可见可用;9. G9 进台即有高对比 PPT 风格预设、绿底上清晰。
10. **FZ 回归(红线)** + 既有门禁全过。

## 交付
- G1→G9 各一次提交,顺序执行。回推后通知 mac claude 终审。
- 注:#6 三角形几何本就是等边(`trianglePoints`)且 round-5 已 aspectK 补偿,若仍觉"扁",多为画布 resize 后未重算——G3/G5 改动时一并确认 `ResizeObserver` 触发重渲染。

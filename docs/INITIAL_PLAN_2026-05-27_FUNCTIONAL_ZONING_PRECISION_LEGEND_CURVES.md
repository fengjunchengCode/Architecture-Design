# 完整计划：Functional Zoning 精细绘制、图例分组与弧线能力

日期：2026-05-27
项目：`26-BQ-PARK`
状态：按 mac Claude `1bcaa52` 审阅意见修订，供再次复审；本轮只写计划，不实施代码。

---

## 1. 目标与边界

用户当前的 4 个体验问题：

1. 闭合多边形后不会默认选中新对象，必须手动点选才能改样式。
2. 对象命中区覆盖整个多边形面积，精细落点时经常误选旁边对象。
3. 对象列表不是最终图例；真实功能区应按填充、边框、线宽等视觉属性归类预览。
4. 需要支持直线 + 弧线混合边界，能精确勾勒弧形功能区。

本计划拆成两波：

- **Wave A：不改 schema 的 UI 快修**。默认选中、精细命中、图例预览、协议图例规则。该波可由 Windows Claude 直接实施。
- **Wave B：弧线 schema + UI + 协议升级**。升 `schema_version` 到 `1.1`，新增可选 `geometry.segments`。该波必须按本计划的 schema 规范实施，实施完成后回推给 mac Claude 最终核验。

明确不做：

- 不新增 `legend_group` 字段。
- Wave A 不改 `schema.py`，不引入弧线。
- 不改 `traffic_analysis`。
- 不碰 `docs/agent_drawing_protocol.md` 的 `## 3.5 SVG 箭头标准`。
- 不提交 `projects/26-BQ-PARK/05_output/inventory.json` 或 `projects/26-BQ-PARK/05_output/drawings/semantic/`。

---

## 2. Wave A：精细绘制与图例预览

### A1. 闭合后默认选中新分区

当前状态：

- `_tools/uploader/static/workbench/workbench.js`
- `finishFunctionalZone()` 创建对象后执行 `state.selectedId = ""`。

修改：

- 将 `finishFunctionalZone()` 中新对象创建后的选择逻辑改为 `state.selectedId = id`。
- 保留 `state.zoneDraftStyle = style`。
- 保留 `state.zoneDraftLabel = ""`，避免下一个对象继承名称。
- 保留 `addPoint()` 当前逻辑：当用户开始画下一个多边形时，如果存在 selected，则先复制 selected 的 `style_hints` 到 `zoneDraftStyle`，再清空 selected。

验收：

- 点击首点或 Enter 闭合后，新分区在对象明细中高亮。
- 样式控件立即绑定新对象，闭合后直接改颜色/线宽会作用到新对象。
- 用户继续点画布开始下一个分区时，选择态清除，但样式继承。

### A2. 命中区从“整面可选”改为“绘制态不拦截、空闲态精确选”

当前状态：

- `renderFunctionalZoneSvg()` 生成 `.zone-hit`，`fill="transparent"`、`stroke-width="0.02"`、`pointer-events="all"`。
- 这会导致整个多边形面积吃掉点击。

修改规则：

- 可见 polygon/path 增加 `pointer-events="none"`，不直接处理点击。
- 当 `state.currentPoints.length > 0` 时，不渲染旧对象 `.zone-hit`，或渲染为 `pointer-events="none"`。
- 绘制态禁用旧对象 hit 时，不能影响草稿 close handle；`data-close-zone` 仍需可点击。
- 空闲态分两类：
  - 有边框对象：`.zone-hit` 使用 stroke-only 命中。
    - `fill="none"`
    - `stroke="transparent"`
    - `pointer-events="stroke"`
    - `stroke-width=getZoneHitStrokeWidth(style)`
  - `border_style === "none" && fill_enabled === true`：保留填充面可选。
    - `fill="transparent"`
    - `stroke="none"`
    - `pointer-events="fill"`
- `!fill_enabled && border_style === "none"` 的全隐形对象不提供画布命中，只能从对象明细选中。

`getZoneHitStrokeWidth(style)` 规则：

- 使用 normalized style。
- 基础值取可见 `stroke_width`。
- 增加约 `2px` 屏幕容差。
- 因 SVG `viewBox="0 0 1 1"` 且 `preserveAspectRatio="none"`，单个 `stroke-width` 无法同时做到 x/y 屏幕恒定；实现时按 stage 短边换算或取两轴折中，并在代码注释说明这是有意的宽松命中容差。
- 不再使用固定 `0.02`。

验收：

- 绘制新分区时，点击已有分区内部不会选中旧对象，而是继续添加草稿点。
- 空闲态点击有边框对象的边线附近可选中对象。
- 空闲态点击无边框但有填充对象的填充面可选中对象。
- 全隐形对象只能从对象明细选中。
- `Delete`、`Ctrl/Cmd+Z`、对象明细选择不回退。

### A3. 新增“图例预览”，按可见样式分组

当前状态：

- `objectList` 是对象明细，每个 polygon 一行。
- 最终图纸图例不应每个 polygon 一条。

新增派生函数：

- `buildFunctionalZoneLegendGroups(objects)`
- 只处理 `functional_zone`。
- 使用 `normalizeZoneStyle(obj.style_hints)` 后再生成 group key。

分组 key 必须按可见性归一：

```js
{
  fill: style.fill_enabled ? style.fill_color : null,
  border: style.border_style,
  stroke_width: style.border_style === "none" ? null : style.stroke_width
}
```

规则：

- 两个“关闭填充但 fill_color 不同”的对象应合并，因为图面上都不显色。
- 两个“无边框但 stroke_width 不同”的对象应合并，因为图面上都不显线宽。
- `!fill_enabled && border_style === "none"` 的全隐形对象不进入正常图例；图例预览底部显示轻提示：`有 N 个不可见对象未进入图例`。
- 同一组内多个 polygon 合并为一条图例，显示 `x N`。

组名规则（不新增 schema）：

- 取该组第一个非空 `object.label`。
- 如果同一组存在多个不同 label，显示：`首个 label 等 N 类`。
- 同时在该组下方显示轻提示：`同一样式下存在多个名称，最终图例将按样式合并`。
- 如果全组没有 label，显示 `功能分区`。

UI 位置：

- 在功能分区工具面板中新增 `renderFunctionalZoneLegendPreview()`。
- 放在样式控件之后、工作台操作按钮之前。
- 原 `objectList` 保留，但在列表上方增加标题“对象明细”，避免用户误认为它是最终图例。

需要修改：

- `_tools/uploader/static/workbench/workbench.js`
  - 新增 `buildFunctionalZoneLegendGroups()`。
  - 新增 `renderFunctionalZoneLegendPreview()`。
  - 在 `renderFunctionalZoningTools()` 中渲染图例预览。
  - 所有改变 objects/style/label 的路径都要刷新图例预览。
- `_tools/uploader/static/workbench/workbench.css`
  - 新增图例预览、色块、线型、提示文本样式。
- `_tools/uploader/static/index.html`
  - 仅在需要给 `objectList` 增加标题容器时微调。
- `docs/agent_drawing_protocol.md`
  - 在 `## 5. 图例自动生成` 内新增“功能分区图例按 `style_hints` 合并”。

协议文字要求：

- `functional_zoning` 图例按 normalized `style_hints` 分组，不按 object id。
- 图例样式取对象级 `style_hints`，优先于 `style_spec` 默认。
- 同一 style group 的多个 polygon 只生成一条图例。
- label 按 UI 中同样的组名规则派生。
- 不新增 schema 字段。

验收：

- 画 3 个相同样式 polygon，图例预览只出现 1 条，显示 `x 3`。
- 修改其中一个 polygon 的颜色后，图例预览变成 2 条。
- 关闭填充后，不同 fill_color 的对象合并。
- 无边框后，不同 stroke_width 的对象合并。
- 全隐形对象不进入正常图例，并显示轻提示。
- `docs/agent_drawing_protocol.md` §5 明确 Stage 7 也按同样逻辑生成图例。

---

## 3. Wave B：弧线几何能力

### B1. 版本与兼容

schema 版本：

- 新写出的 semantic drawing 使用 `schema_version: "1.1"`。
- 旧 `schema_version: "1.0"` 文件继续合法。
- 旧 1.0 文件没有 `segments` 时，仍按 `coords` 当普通 polygon 读取。
- 注意：旧版 `schema.py` 会丢弃未知 `segments`；1.1 落地后，禁止再用旧 `schema.py` 回写含弧线的文件，否则弧线会退化。

不升 `2.0` 的原因：

- `segments` 是可选加法字段。
- 缺省行为仍是旧 polygon。
- 旧数据可读，不是破坏性变更。

### B2. 数据模型：`segments` 为权威，`coords` 为派生采样

`GEOMETRY_KINDS` 不新增 kind，仍为：

```python
{"point", "polyline", "polygon", "arrow"}
```

弧线仍是：

```json
{
  "geometry": {
    "kind": "polygon",
    "coords": [[...]],
    "segments": [...]
  }
}
```

`segments` 规则：

- 仅允许出现在 `functional_zone + polygon`。
- 是可选 sibling，不替代 `coords` 字段。
- `segments` 存在时为权威边界。
- `coords` 必须从 `segments` 确定性重采样生成，禁止独立手改。
- 保存时每次都从 `segments` 重新生成 `coords`。
- `coords` 只用于 hit test、填充兜底、label 形心、旧工具兜底。

segment v1 仅支持：

```json
{ "kind": "line", "from": [x, y], "to": [x, y] }
{ "kind": "quadratic", "from": [x, y], "control": [x, y], "to": [x, y] }
```

cubic 预留：

- validator 现在只接受 `line` / `quadratic`。
- 遇到 `cubic` 报明确错误：`geometry.segments cubic is reserved but not supported yet`。
- 未来 cubic 使用 `control1` / `control2`，不复用 quadratic 的 `control` 字段。

### B3. 采样规则

确定性重采样：

- line 段保留终点连接关系，不重复写相邻段的共享点。
- quadratic 段固定采样 `16` 等分。
- 对每个 quadratic，按 `t = 1/16 ... 16/16` 采样，首点由上一段或 first.from 提供，避免重复点。
- 所有采样点 round 到 6 位小数。
- 保存前 `coords = sampleSegments(segments)`。

建议伪代码：

```js
function sampleQuadratic(from, control, to, steps = 16) {
  const points = [];
  for (let i = 1; i <= steps; i += 1) {
    const t = i / steps;
    const mt = 1 - t;
    points.push([
      mt * mt * from[0] + 2 * mt * t * control[0] + t * t * to[0],
      mt * mt * from[1] + 2 * mt * t * control[1] + t * t * to[1],
    ]);
  }
  return points;
}
```

### B4. schema 校验

`_tools/drawing_workbench/schema.py` 修改：

- `SCHEMA_VERSION` 升为 `"1.1"`，但 normalize 接受 `"1.0"` 与 `"1.1"`。
- 输出 normalize 后统一写 `"1.1"`。
- `_normalize_geometry()` 接受可选 `segments`。
- 新增 `_normalize_segments(value, object_index)`。
- `_normalize_segments()` 必须校验：
  - value 是非空数组。
  - 每段 kind 是 `line` 或 `quadratic`。
  - 每个 `from` / `to` / `control` 走现有 `_normalize_coord()`。
  - `segment[i].to == segment[i+1].from`，按 6 位小数比较。
  - `last.to == first.from`，按 6 位小数比较。
  - 不连续直接 `DrawingValidationError`。
  - 非 `functional_zone + polygon` 出现 segments 直接拒绝。
- `segments` 存在时，忽略输入里的旧 `coords` 形状，重新采样生成 normalized `coords`。
- `segments` 不存在时，旧 `coords` 路径不变。

验收：

- 旧 1.0 polygon JSON 可加载并保存为 1.1。
- 含合法 `segments` 的文件 normalize 后保留 `segments` 并重采样 `coords`。
- 越界 control、非法 kind、不连续链、未闭合环都会报 `DrawingValidationError`。
- `traffic_analysis` 或非 polygon 对象写 segments 会报错。

### B5. UI 交互

交互原则：

- 不做自由手绘。
- 不做自动平滑。
- 不做 cubic。
- 做边级弧线编辑：用户先画普通 polygon，再把某些边改成 quadratic。

选中对象时：

- 顶点显示现有 vertex handles。
- 每条边中点显示 edge handle。
- 直线边 edge handle 使用空心小菱形。
- quadratic 边显示 control handle 与轻量辅助线。

操作：

- 点击直线边 edge handle：将该边转换为 quadratic。
  - `control` 初始为边中点。
  - 进入该边编辑态。
- 拖动 quadratic 的 control handle：实时改变弧度。
- 双击 control handle 或点击“恢复直线”：该边回到 line。
- 所有转换、拖动结束、恢复直线都进入 undo stack。
- 保存时从 segments 重采样 coords。

渲染：

- 有 `geometry.segments` 时，`renderFunctionalZoneSvg()` 用 `<path d="">`。
- 无 `segments` 时继续用 `<polygon points="">`。
- path 命令：
  - first segment：`M from.x from.y`
  - line：`L to.x to.y`
  - quadratic：`Q control.x control.y to.x to.y`
  - 末尾 `Z`
- 可见形状、hit shape、选中 handles 都基于同一 segments/path。

### B6. 协议修改

修改 `docs/agent_drawing_protocol.md`：

1. 在 `## 5. 图例自动生成` 增加“功能分区图例按 `style_hints` 合并”。
2. 增加弧线渲染规则：
   - Stage 7 见 `geometry.segments` 时，用 `<path>` + `Q` 绘制功能分区边界。
   - 无 `segments` 时，按 `coords` 输出 polygon。
3. 修改现有自动平滑规则：
   - 如果存在 `geometry.segments`，必须严格按 segment kind 逐边渲染，禁用自动 Catmull-Rom / Bezier 平滑。
   - 只有无 `segments` 的旧 polygon 才允许自动平滑。
4. 不触碰 `## 3.5 SVG 箭头标准`。

验收：

- 含 segments 的 task pack 中，Stage 7 协议不会把显式直线边自动平滑。
- quadratic segment 会转成 SVG `Q` 命令。
- 无 segments 的旧 polygon 仍走旧规则。

---

## 4. 实施顺序与验证

### Wave A 实施顺序

1. `finishFunctionalZone()` 闭合后默认选中新对象。
2. `renderFunctionalZoneSvg()` 调整 hit shape：
   - 绘制态禁用旧 hit。
   - 有边框走 stroke-only hit。
   - 无边框有填充走 fill hit。
   - 全隐形只列表选。
3. 新增图例预览与对象明细标题。
4. 更新 `docs/agent_drawing_protocol.md` §5 图例规则。
5. 运行验证。

Wave A 命令验证：

```powershell
node --check _tools\uploader\static\workbench\workbench.js
git diff --check -- _tools\uploader\static\index.html _tools\uploader\static\workbench\workbench.css _tools\uploader\static\workbench\workbench.js docs\agent_drawing_protocol.md
python _tools\validate_record.py 26-BQ-PARK
```

Wave A 浏览器验收：

- 闭合后新对象自动选中。
- 闭合后直接改样式作用于新对象。
- 开始下一个分区时继承样式并清选择。
- 绘制态点击已有分区内部不会误选。
- 空闲态点击边线附近可选中有边框对象。
- 空闲态点击无边框填充面可选中对象。
- 图例预览按 visible style group 合并。
- 全隐形对象不进入正常图例。

### Wave B 实施顺序

1. 改 `schema.py`，先完成 1.0/1.1 兼容、segments 校验、coords 重采样。
2. 为 schema 增加最小命令级测试或用临时 JSON smoke test 覆盖合法/非法 segments。
3. 改前端数据结构和 path 渲染。
4. 加 edge handle / control handle / 恢复直线交互。
5. 更新 `docs/agent_drawing_protocol.md` segments 渲染与自动平滑排除规则。
6. 浏览器验证保存、刷新、重载后弧线仍存在。

Wave B 命令验证：

```powershell
node --check _tools\uploader\static\workbench\workbench.js
python -m py_compile _tools\drawing_workbench\schema.py
python _tools\validate_record.py 26-BQ-PARK
git diff --check -- _tools\drawing_workbench\schema.py _tools\uploader\static\workbench\workbench.js _tools\uploader\static\workbench\workbench.css docs\agent_drawing_protocol.md
```

Wave B 浏览器验收：

- 旧 polygon 能正常加载。
- 新建 polygon 后可把单条边切换为弧线。
- 拖动 control handle 改变弧度。
- 恢复直线可用。
- 保存、刷新、重新加载后弧线仍存在。
- undo / redo 覆盖转换弧线、拖动 control、恢复直线。

---

## 5. 提交与回审边界

提交时只 stage 本轮需要的代码和文档。

不要提交：

- `projects/26-BQ-PARK/05_output/inventory.json`
- `projects/26-BQ-PARK/05_output/drawings/semantic/`
- 运行缓存、截图草稿、临时 JSON。

回审报告必须包含：

- 实施的是 Wave A 还是 Wave B。
- 改动文件列表。
- 对应验收项是否通过。
- 是否产生但未提交项目输出。
- 若实施 Wave B，必须报告：
  - `coords` 重采样规则。
  - 链连续性校验结果。
  - 1.0 旧文件兼容结果。
  - `agent_drawing_protocol.md` 中自动平滑排除规则是否已写入。

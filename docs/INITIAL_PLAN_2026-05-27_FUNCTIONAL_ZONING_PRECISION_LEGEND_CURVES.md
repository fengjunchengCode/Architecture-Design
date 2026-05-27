# 初版方案：Functional Zoning 精细绘制、图例分组与弧线能力

日期：2026-05-27
项目：`26-BQ-PARK`
对象：`_tools/uploader/static/workbench/` 功能分区工作台
目标：解决用户在连续绘制后的 4 个体验问题，并交给 Mac 端 Claude 复审。

---

## 1. 当前问题与成功标准

### 用户反馈

1. 闭合多边形后不会默认选中新对象，必须手动点选才能继续改样式。
2. 对象点击命中区过大，当前 `zone-hit` 覆盖整个多边形面积，精细绘图时容易误选旁边对象。
3. 对象列表按每个 polygon 展示，但真实图纸的图例应按填充、边框、线宽等视觉属性归类，而不是每个多边形一条图例。
4. 目前只能画折线多边形，无法精确画“直线 + 弧线”混合边界。

### 成功标准

- 用户闭合一个分区后，右侧/左侧样式面板立即绑定该新分区，可直接调颜色、线型、线宽、名称。
- 绘制新点时不会被已有分区的填充面误拦截；空闲选择时命中范围接近可见边线。
- UI 中新增“图例预览”，按 `style_hints` 自动合并相同视觉属性的功能区，并和最终 PDF/SVG 图例逻辑一致。
- 弧线能力支持部分边为直线、部分边为弧线；保存后可复原；Stage 7 agent 能用曲线语义生成 `<path>`，旧数据仍可读取。

---

## 2. Wave A：快速体验修复（不改 schema）

### A1. 闭合后默认选中新分区

现状：`finishFunctionalZone()` 创建对象后执行 `state.selectedId = ""`。

修改：

- 在 `finishFunctionalZone()` 中改为 `state.selectedId = id`。
- 保留 `state.zoneDraftStyle = style`，这样下一次开始新多边形时仍能继承当前样式。
- `renderSpecificTools()` 会因 selected 存在而显示该对象的样式和 label，用户可立即修改。
- `addPoint()` 现有逻辑已经会在开始新多边形时复制 selected 样式到 draft 并清空 selected，可继续复用。

验收：

- 点击首点闭合后，对象列表中新对象高亮。
- 颜色、边框、线宽控件立即显示新对象属性。
- 闭合后直接修改颜色，刚闭合对象立即变化。
- 随后点画布开始下一个分区时，不会继续保持选中状态，但会继承样式。

### A2. 选择命中区改为“跟随边线”，绘制时禁用旧对象拦截

现状：`renderFunctionalZoneSvg()` 生成：

```svg
<polygon class="zone-hit" fill="transparent" stroke="transparent" stroke-width="0.02" pointer-events="all">
```

这会让整个多边形面积都可点击，导致用户想在旁边或内部精细落点时误选旧对象。

修改：

- 可见 polygon 增加 `pointer-events="none"`，避免填充面吃掉画布点击。
- `zone-hit` 改为 stroke-only：
  - `fill="none"`
  - `stroke="transparent"`
  - `pointer-events="stroke"`
  - `stroke-width` 用 `getZoneHitStrokeWidth(style)` 计算。
- `getZoneHitStrokeWidth(style)`：
  - 基础值使用当前可见 `style.stroke_width`。
  - 增加很小的屏幕容差，建议 `2px` 转 SVG 坐标。
  - 最终命中宽度不再使用固定 `0.02`。
- 当 `state.currentPoints.length > 0` 时，不渲染或禁用已有对象的 `zone-hit`，保证绘制过程中每次点击都优先添加草稿点。
- `border_style === "none"` 的对象默认只能从对象列表选中；如果用户后续强烈需要，也可以再加“填充面可选”开关，但本轮不加。

验收：

- 已有分区内部点击不会误选对象。
- 绘制新分区时，点落在已有分区内部或边缘附近仍能添加草稿点。
- 空闲状态下点击边线附近可选中对象。
- `Delete`、`Ctrl+Z`、对象列表选择逻辑不回退。

### A3. 新增“图例预览”，按视觉属性归类

现状：`objectList` 是对象明细，每个 polygon 一行；最终图纸如果按对象生成图例，会出现过多重复条目。

修改：

- 新增派生函数 `buildFunctionalZoneLegendGroups(objects)`：
  - 只处理 `functional_zone`。
  - group key 使用 normalized style：
    - `fill_enabled`
    - `fill_color`
    - `border_style`
    - `stroke_width`
  - 同 key 的多个 polygon 合并为一个图例组。
- 新增 `renderFunctionalZoneLegendPreview()`，显示在功能分区工具面板中，位置建议在样式控件之后、对象明细之前。
- 每个图例组显示：
  - 色块/填充状态
  - 边框线型（实线/虚线/无边框）
  - 线宽数值
  - 组名
  - 对象数量，例如 `x 3`
- 组名规则（不新增 schema）：
  - 取该组第一个非空 `object.label`。
  - 若同组存在多个不同 label，显示 `首个 label 等 N 类`，并在 UI 中提示“同一样式下存在多个名称，最终图例将按样式合并”。
  - 若全空，显示 `功能分区`。
- 保留原对象明细列表，但标题改为“对象明细”，避免用户把它误认为最终图例。

协议同步：

- 修改 `docs/agent_drawing_protocol.md` 的图例规则：
  - 对 `functional_zoning`，图例优先按 `style_hints` 分组，而不是按 object id 或每个 polygon。
  - 图例样式必须使用对象级 `style_hints`。
  - 同一 style group 的多个 polygon 只生成一条图例。
  - label 按上述组名规则派生。

验收：

- 画 3 个相同样式 polygon，图例预览只出现 1 条，显示 `x 3`。
- 修改其中一个 polygon 的颜色后，图例预览变成 2 条。
- 相同样式不同 label 时出现轻量提示，不阻塞保存。
- 生成 task pack 后，agent 协议能明确读到“功能分区图例按 style_hints 合并”。

---

## 3. Wave B：弧线几何能力（需要 schema + 协议）

弧线不建议和 Wave A 混在同一个小修里直接写。它会影响保存格式、校验、UI 渲染、Stage 7 SVG 翻译，必须单独作为几何能力升级。

### B1. 交互方案：边级弧线编辑，而不是自由手绘

推荐交互：

- 默认仍是当前直线多边形绘制。
- 选中一个分区后：
  - 顶点显示原有 vertex handles。
  - 每条边中点显示 edge handle。
- 点击某条边的 edge handle：将该边从 `line` 切换为 `quadratic` 弧线。
- 拖动 edge handle：移动二次贝塞尔控制点，实时预览弧度。
- 双击 edge handle 或点击“恢复直线”：该边回到直线。
- 不做自由手绘、不做自动平滑、不做三次贝塞尔；先只做二次贝塞尔，降低复杂度。

理由：

- 用户可以保留“直线 + 弧线混合”的精细控制。
- 不要求用户理解复杂曲线工具。
- 二次贝塞尔足够表达建筑总图里大部分圆角、弧形边界、曲线园路边界。

### B2. 数据结构：保留 `coords` 兼容，新增可选 `segments`

当前 schema 只保存：

```json
{
  "geometry": {
    "kind": "polygon",
    "coords": [[0.1, 0.2], [0.3, 0.2], [0.3, 0.4]]
  }
}
```

建议扩展为：

```json
{
  "geometry": {
    "kind": "polygon",
    "coords": [[0.1, 0.2], [0.3, 0.2], [0.32, 0.28], [0.3, 0.4]],
    "segments": [
      { "kind": "line", "from": [0.1, 0.2], "to": [0.3, 0.2] },
      { "kind": "quadratic", "from": [0.3, 0.2], "control": [0.38, 0.3], "to": [0.3, 0.4] },
      { "kind": "line", "from": [0.3, 0.4], "to": [0.1, 0.2] }
    ]
  }
}
```

规则：

- `coords` 继续存在，保存为 sampled polygon，用于旧代码、hit test、填充兜底。
- `segments` 可选；不存在时按旧 polygon 读取。
- `segments` 只允许在 `functional_zone + polygon` 上使用。
- 每个 segment 坐标仍是 normalized `[0..1, 0..1]`。
- 二次贝塞尔保存 `control`，Stage 7 输出 SVG 时使用 `Q` 命令。

### B3. 需要修改的文件

- `_tools/drawing_workbench/schema.py`
  - `GEOMETRY_KINDS` 不新增 kind，仍用 `polygon`。
  - `_normalize_geometry()` 接受可选 `segments`。
  - 新增 `_normalize_segments()`，只允许 `line` / `quadratic`。
  - 保留旧 JSON 兼容。
- `_tools/uploader/static/workbench/workbench.js`
  - `buildDrawing()` 保存 `geometry.segments`。
  - `loadDrawing()` 读取并规范化旧数据。
  - `renderFunctionalZoneSvg()` 从 segments 生成 `<path d="">`，无 segments 时 fallback polygon。
  - 新增 selected object 的 edge handles 与 curve control handle。
  - 新增边切换/拖拽逻辑，所有操作进入 undo stack。
- `_tools/uploader/static/workbench/workbench.css`
  - edge handle / curve handle 样式。
- `docs/agent_drawing_protocol.md`
  - Stage 7 若发现 `geometry.segments`，用 `<path>` 和 `Q` 命令绘制功能分区边界。
  - 若无 `segments`，继续按 `coords` 输出 polygon。

### B4. 弧线验收

- 旧的 polygon JSON 能正常加载、保存、导出。
- 新建 polygon 后可将单条边切换为弧线。
- 保存、刷新、重新加载后弧线仍存在。
- 修改弧线控制点可撤销/重做。
- `schema.py` 能拒绝越界控制点或非法 segment kind。
- Stage 7 task pack 中保留 `segments`，agent 协议明确如何转成 SVG path。

---

## 4. 推荐实施顺序

### 第一轮：Wave A

1. 改 `finishFunctionalZone()`：闭合后默认选中新对象。
2. 改 `renderFunctionalZoneSvg()`：stroke-only hit + 绘制时禁用旧对象 hit。
3. 新增图例预览：按 style key 分组展示。
4. 更新 `docs/agent_drawing_protocol.md`：功能分区图例按 `style_hints` 合并。
5. 浏览器验证当前 26-BQ-PARK，不提交 `inventory.json` 或 semantic 输出。

### 第二轮：Wave B

1. 先让 Mac 端 Claude 审核 `segments` schema。
2. 审核通过后再改 schema + UI 曲线编辑。
3. 最后补 Stage 7 协议与验证。

---

## 5. 给 Mac 端 Claude 的审阅问题

1. Wave A 是否可以直接实施，还是图例预览需要先加显式 `legend_group` 字段？
2. `zone-hit` 改成 stroke-only 是否会让“无边框但有填充”的对象过难选择？是否接受“只能从对象列表选”的初版策略？
3. 功能分区图例按 `style_hints` 分组是否符合最终 PDF/PPT 表达逻辑？
4. Wave B 的 `geometry.segments` 是否应该作为 schema 1.0 的可选字段，还是需要升级 `schema_version`？
5. 弧线初版只支持 quadratic 是否足够，是否需要从第一版就支持 cubic？

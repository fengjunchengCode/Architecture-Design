# Agent Drawing Protocol（task_pack → SVG）

**目的**：当 agent 收到一个 task_pack 目录，按本文档的步骤产出符合印刷要求的 SVG 草稿。

**适用 agent**：claudecode / 任意带视觉的 Claude 会话。

**触发**：用户在对话窗口说"请画 {project} 的 {drawing_type}"并给出 task_pack 路径；或工作台 task_pack_status 提示后用户切到对话窗口。

---

## 1. 输入读取顺序

收到 task_pack 路径后，**按顺序**读以下文件（顺序决定 agent 心智模型构建顺序，不要乱）：

| # | 文件 | 用途 |
|---|---|---|
| 1 | `task.json` | 知道 drawing_type / output_target / user_notes / 哪些文件可用 |
| 2 | `style_spec.json` | 视觉规范；若 `{"exists": false}` → **停下来要求用户先做 style 协商** |
| 3 | `context/s1_registration.json` | 项目场地基本信息、地理坐标、注册状态 |
| 4 | `context/s2_alignment.json` | CAD 对齐结论、控制点、置信度 |
| 5 | `sketch.json` | 用户草图几何 + 对象类型 + 标签（**几何真相**） |
| 6 | `base_image.{ext}` | 用视觉打开，看清地理底图实际样子 |
| 7 | `references/*.png` | 同类参考页缩略图，借鉴构图/图例/视觉惯例 |

### 缺料处理

- style_spec 不存在 → 在对话窗口跟用户启动 `docs/style_spec_negotiation.md` 流程，**不**继续画
- sketch.json 没有 objects → 提示用户回工作台先画几个对象
- base_image 缺失 → 报错并停
- references 为空（poppler 失败或未配置） → 继续画，但在结束时提示"未拿到参考页，风格判断仅基于 style_spec"
- s1/s2 context 为空 → 继续画，但标签/方位信息可能受限，结尾提示

---

## 2. SVG 输出规范

### 2.1 文件位置

写入 `task.json` 里的 `output_target`，等价于 `projects/{code}/05_output/drawings/svg/{drawing_type}.svg`。

**不要**写到 task_pack 目录里。task_pack 是输入，SVG 是项目级产物。

### 2.2 画布尺寸

**锁定 A3 横版 300 DPI**：

```xml
<svg xmlns="http://www.w3.org/2000/svg"
     viewBox="0 0 4960 3508"
     width="4960" height="3508">
```

| 维度 | 值 | 推导 |
|---|---|---|
| 宽 px | 4960 | 420mm × 300dpi / 25.4 |
| 高 px | 3508 | 297mm × 300dpi / 25.4 |
| 1mm | 11.81 SVG 单位 | 11.81 ≈ 300/25.4 |
| 1pt | 4.167 SVG 单位 | 4.167 ≈ 300/72 |

所有 stroke-width、font-size、padding 用上面换算。**不要在 SVG 里写 mm/pt 单位**，全用纯数字（默认 px 等价于 SVG 单位）。

### 2.3 底图嵌入

底图在 task_pack 里是 `base_image.{ext}`，原始位置在 `projects/{code}/05_output/drawings/base/{name}`。

**用相对路径引用，不要 base64 嵌入**：

```xml
<image href="../base/{filename}"
       x="0" y="0" width="4960" height="3508"
       preserveAspectRatio="xMidYMid slice"/>
```

`../base/{filename}` 是从 `05_output/drawings/svg/` 走到 `05_output/drawings/base/` 的相对路径。cairosvg 在 svg2png 时通过 `url=str(svg_path)` 能正确 resolve。

### 2.4 图层结构（自上而下）

```xml
<svg ...>
  <defs>
    <!-- marker（箭头）、linearGradient（如需）、symbol 等 -->
  </defs>
  
  <g id="base-layer">
    <image href="../base/..." .../>
  </g>
  
  <g id="annotation-layer">
    <!-- 用户草图翻译过来的对象，按 z-order：functional_zone 在下，flow 在中，entrance 在上 -->
    <g id="functional-zones">...</g>
    <g id="flows">...</g>
    <g id="entrances">...</g>
  </g>
  
  <g id="label-layer">
    <!-- 文字标签 + 引线 -->
  </g>
  
  <g id="legend-layer">
    <!-- 图例区 -->
  </g>
  
  <g id="frame-layer">
    <!-- 标尺、指北针、标题块 -->
  </g>
</svg>
```

`<g>` 加 `id` 方便后续 agent / 工具按层修改。

---

## 3. SVG 元素白名单

### 允许使用

| 元素 | 用途 |
|---|---|
| `<svg>` `<g>` | 根/分组 |
| `<image>` | 底图 |
| `<path>` `<polyline>` `<polygon>` `<line>` | 几何 |
| `<circle>` `<ellipse>` `<rect>` | 点、椭圆、矩形 |
| `<text>` `<tspan>` | 文字 |
| `<defs>` `<marker>` | 复用定义、箭头 |
| `<linearGradient>` `<radialGradient>` | 图例色块渐变（可选） |
| `<title>` `<desc>` | 可访问性，可选 |

### 禁止

| 元素 | 原因 |
|---|---|
| `<script>` | 安全 |
| `<foreignObject>` | cairosvg 支持差 |
| `<filter>` | 滤镜在 cairosvg 上不稳定 |
| `<use href="external"/>` | 跨文件 use 解析脆 |
| 内联 base64 字体 | 文件臃肿；用 font-family 回退 |

---

## 3.5 SVG 箭头标准

所有 `<marker>` 必须用 **`userSpaceOnUse` + `viewBox`** 归一化模板，保证箭头视觉重量跟线宽解耦：

```xml
<marker id="arrow-{object_type}"
        viewBox="0 0 10 10"
        markerWidth="{W}" markerHeight="{W}"
        refX="10" refY="5"
        orient="auto"
        markerUnits="userSpaceOnUse">
  <path d="M0,0 L10,5 L0,10 z" fill="{color}"/>
</marker>
```

### markerWidth 按画布尺寸

| 画布 | 短边 | markerWidth |
|---|---|---|
| A3 真图 (4960×3508) | 3508 | **56** |
| A4 真图 (3508×2480) | 2480 | **40** |
| 800×600 样卡 | 600 | **14** |

公式：`markerWidth = round(canvas_short_dim / 60)`。

### 禁止

- ❌ 不用 `markerUnits="strokeWidth"`（会让细线箭头变小，图例 / 主图视觉不一致）
- ❌ 不省略 `viewBox`（会让 path 坐标和 markerWidth 隐性耦合，难维护）
- ❌ 不用 path 坐标值≠ 10 × 10 范围（其他模板的 viewBox 坐标系不要换）
- ❌ 不为不同 object_type 用不同 markerWidth（同一画布所有箭头同尺寸）

### 双端箭头

`vehicle_flow` 在启泰风格里两端都有箭头。SVG 写法：定义两个 marker（`arrow-X-start` 和 `arrow-X-end`，path 镜像），或用单 marker + `marker-start` + `marker-end` + `orient="auto-start-reverse"`：

```xml
<marker id="arrow-vehicle"
        viewBox="0 0 10 10"
        markerWidth="56" markerHeight="56"
        refX="10" refY="5"
        orient="auto-start-reverse"
        markerUnits="userSpaceOnUse">
  <path d="M0,0 L10,5 L0,10 z" fill="..."/>
</marker>

<path d="..." marker-start="url(#arrow-vehicle)" marker-end="url(#arrow-vehicle)"/>
```

`orient="auto-start-reverse"` 让同一 marker 既能贴在 path 起点（自动反转方向）也能贴在终点。

---

## 4. 几何翻译：sketch.json → SVG 坐标

sketch.json 里的 coords 是 [0,1] 归一化：

```python
svg_x = sketch_x * 4960
svg_y = sketch_y * 3508
```

### 几何清理

agent 翻译时**允许**对草图做下列清理（用户画得粗时帮忙补齐）：

- **平滑曲线**：折线 → Catmull-Rom 或 Bezier，节点数 ≥ 4 时启用
- **闭合多边形**：polygon 最后点没回到首点时自动闭合
- **吸附短段**：相邻段长 < 0.5% 画布对角线时合并
- **延长流线到边界**：flow 起止点离画布边缘 < 2% 时，延伸到画布边缘（避免"线突然停在中间"）

**不允许**：
- 改变对象数量（不要凭空加流线或分区）
- 改变对象类型（草图标的 vehicle_flow 不能渲染成 pedestrian_flow）
- 移动多边形重心超过 5% 画布对角线

### 对象类型 → 视觉样式

按 style_spec 映射，**不要**自己写死颜色：

| sketch object_type | 主要视觉 | 来源字段 |
|---|---|---|
| `functional_zone` | 多边形填充 + 描边 | `palette.annotation_colors.functional_zone` 或回退到 `palette.primary` 半透明 |
| `vehicle_flow` | 实线/虚线 + 箭头 | `palette.accent`、`arrows.default_style`、`strokes.primary_width_mm` |
| `pedestrian_flow` | 实线 + 箭头 | `palette.primary`、`strokes.secondary_width_mm` |
| `main_entrance` | 三角形或菱形点位 | `palette.accent` |
| `label` | 文字 + 标签底盒 | `labels.shape`、`labels.background_alpha` |

---

## 5. 图例自动生成

从 sketch.json 的对象 + label 自动派生。

### 规则

- 每种 object_type + 唯一 label 组合占一行
- 同 type 同 label 的多个对象合并到一行（不要重复）
- label 为空的对象 → 用 object_type 中文名（"功能分区" / "车行流线" / ...）

### 位置

按 `style_spec.legend.position` 放（默认 `bottom_right`）：

| position | 锚点（SVG 单位） |
|---|---|
| `bottom_right` | 右下角，距边距 200，宽 1400 |
| `bottom_left` | 左下角，对称 |
| `right` | 右侧中部，宽 1200 |

### 样式

按 `style_spec.legend.layout`：

- `table`：每行一个色块（width 80 height 30）+ 文字
- `scatter`：贴在对象旁（agent 自行避让，本协议不强制位置）
- `sidebar`：单列纵向贴右边

---

## 6. 标尺 + 指北针

仅当 `style_spec.scale_north.scale_style != "none"` 时画。

### 标尺

- 默认 5 段刻度，总长 800 SVG 单位
- 实际米数：从 s2_alignment.json 抽取（如 `cad_alignment_report.scale_meters_per_unit`），找不到则取默认"100m"并在 label 注明
- 位置按 `scale_position`

### 指北针

- compass：圆 + N 字 + 三角指针，半径 120
- arrow：单箭头向上 + N 字
- text：仅 N 字
- 位置按 `north_position`

---

## 7. 标题块

每张图右上 / 顶部统一加：

```
{drawing_type 中文名} | {project_code} {project_name}
{date}
```

- drawing_type → 中文映射：`functional_zoning → "功能分区图"`、`traffic_analysis → "交通组织方案分析图"`
- project_name 从 s1_registration.json 里的项目名抽
- date 用今天

字号按 `style_spec.typography.title_size_pt × 4.167`。

---

## 8. 字体处理

cairosvg 渲染时找不到字体会回退到默认（通常是 sans-serif，中文可能显示成方框）。处理方法：

### SVG 写法

```xml
<text font-family="Source Han Sans CN, PingFang SC, Microsoft YaHei, sans-serif"
      font-size="38" fill="#1F2937">
  功能分区
</text>
```

- 提供 3-4 个回退字体
- 思源黑体（开源跨平台）放首位
- 末尾兜底 `sans-serif`

### 渲染端

cairosvg 走系统 fontconfig。Windows 上需保证系统装了思源或微软雅黑；macOS 上苹方/思源都行。**不要在 SVG 里嵌字体文件**。

---

## 9. 自检（保存前必跑）

agent 在写 SVG 前心里过一遍 checklist：

| # | 检查项 | 否则 |
|---|---|---|
| 1 | sketch.json 里所有 object 都在 SVG 里出现了？ | 漏画必须补 |
| 2 | viewBox 是 `0 0 4960 3508`？ | 改回 |
| 3 | 颜色 / 线宽 / 字号全部来自 style_spec？ | 全部回查 |
| 4 | 底图引用路径相对（`../base/...`）？ | 改回 |
| 5 | 图例存在且条目齐？ | 补 |
| 6 | 标尺 + 指北针存在（如果 style_spec 要求）？ | 补 |
| 7 | 标题块存在？ | 补 |
| 8 | 文件大小 < 5MB？ | 检查是否误嵌 base64 |
| 9 | 禁止元素清单全部未用？ | 改写 |

---

## 10. 输出回执（agent → 用户）

写完 SVG 后回贴：

```
已写入：projects/{code}/05_output/drawings/svg/{drawing_type}.svg

包含：
- 功能分区 N 个
- 流线 N 条
- 标签 N 条
- 图例 / 标尺 / 指北针：[√] / [×]

参考来源：{references 列表}
风格来源：style_spec.json （approved_at: ...）

下一步：到工作台预览，或直接 POST /api/drawing/export 出 PNG/PDF。
```

---

## 11. 反馈迭代

用户看了 SVG 不满意时，agent 接受三种粒度的反馈：

| 粒度 | 例子 | 处理 |
|---|---|---|
| 局部改 | "把南侧分区颜色改深" | 直接 edit SVG 里那个 `<polygon>` |
| 重画一个对象 | "南侧流线重画一下" | 找到该 object_id 对应的 SVG `<g>` 整体替换 |
| 整张重出 | "整体重来" | 删 SVG，从 §1 重读 task_pack |

迭代时**不需要**重新生成 task_pack。原 task_pack 还在，agent 在它基础上改 SVG 即可。

---

## 12. 边界 / 不做的事

- ❌ 不调用图像生成模型（DALL·E / Imagegen 等）—— 输出必须是确定性矢量
- ❌ 不引入 React / Vue / D3 / headless browser
- ❌ 不修改 sketch.json 几何（除 §4 允许的清理）
- ❌ 不修改 style_spec.json（修改走 `style_spec_negotiation.md`）
- ❌ 不动 record.md / inventory.json
- ❌ 不把 task_pack 当输出目录写东西

---

## 13. 关联文档

- `docs/style_spec_negotiation.md` —— style_spec 怎么来
- `docs/planning/TECHNICAL_DRAWING_TYPES_ROADMAP_2026-05-25.md` —— 图种全集
- `_tools/drawing_workbench/schema.py` —— sketch.json 字段定义
- `_tools/drawing_workbench/task_pack.py` —— task_pack 构造逻辑
- `_tools/drawing_workbench/svg_to_png.py` —— SVG → PNG/PDF 导出参数

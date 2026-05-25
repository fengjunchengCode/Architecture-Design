# 技术图纸类型分波次实施计划

日期：2026-05-25
适用范围：`_tools/drawing_workbench/` 语义图纸工作台
对照参考：
- `docs/reference_pdfs/report_examples/20260410西藏启泰直销市场建设项目-3.pdf`
- `docs/reference_pdfs/report_examples/202600520西藏长江大厦建设项目-4.pdf`

## 原则

1. 不追求一次性覆盖所有图种。**一种一种做、一种一种验**。
2. 每种图独立实验：先 VLM 抠该图种的视觉模板（配色/线型/箭头/字号/图例规范）→ 实现渲染逻辑 → BQ-PARK 或同期项目实测一张 → 对照参考 PDF 评 visual gap → 调模板 → 验收。
3. 不靠图像生成模型（nano-banana / GPT-image 等）生成技术图。技术图必须**确定性渲染**：同样 semantic JSON 出同样像素，能 diff，能审计。
4. VLM 的角色：**一次性**抠模板风格 + **可选**输出 QA。**不**在 per-render 路径上。
5. 工作台核心架构（栅格底图 + 用户草图 + 语义 JSON + 模板渲染）不变。每波只在该图种上叠加渲染/对象类型/模板能力。

## 通用基础设施（Wave 0，先于所有图种）

下面这些是所有图种共用的渲染层升级。Wave 1 顺手做掉。

| 项 | 说明 |
|---|---|
| **F3 底图文件选择/上传** | UI 上传按钮 + 已有底图下拉 + 后端 endpoint `/api/drawing/base/upload` 保存到 `05_output/drawings/base/` |
| **R1 曲线平滑** | 用户折线 → Catmull-Rom 或 Bezier，可关闭（点击 "保留原始" 还原折线） |
| **R2 虚线/点划线** | 渲染器支持 `stroke-dasharray`，模板按 object_type 决定虚实模式 |
| **R3 箭头库** | 至少 4 种箭头：开口三角、实心三角、双线箭头、菱形端点；marker 库 |
| **R4 标签** | 圆角矩形 + 文字 + 可选引线（leader line）+ 自动避让 |
| **R5 图例区** | 表格式图例自动从对象列表生成，含色块/线样/图标/中文名 |
| **R6 标尺/指北针** | 标尺基于底图实际比例（用户标注一次实际米数对应像素）；指北针 SVG 模板 |
| **R7 高 DPI 输出** | PNG 最低 2400px 宽，PDF 矢量导出（cairosvg） |
| **R8 模板加载机制** | `_tools/drawing_workbench/templates/{drawing_type}.json` 定义该图种的所有视觉规范，render.py/export.py 读取该 JSON 渲染 |

## 图纸类型完整枚举（按参考 PDF）

按渲染复杂度分三档：

### Category A — 分析图（工作台直接覆盖）

底图 = 渲染总平 / 卫星图 / CAD 导出渲染图。用户画几何 + 标签 → 模板套印。

| # | 图种 | 启泰 PDF 页 | 长江 PDF 页 | 对象类型 | 渲染特征 | 复杂度 |
|---|---|---|---|---|---|---|
| A1 | **功能分区图** | P52 | 类似页 | 多边形(按功能着色) + 文字标签 | 半透明填色 + 描边 + 表格图例 | 低 |
| A2 | **交通组织方案分析图** | P54 | 类似页 | 车行流线/人行流线/消防流线/主入口/次入口/货运入口 | 虚实线 + 箭头库 + 入口图标 + 标签 + 表格图例 | 中 |
| A3 | **消防流线图** | P55 | 类似页 | 消防车道环路 + 消防登高面 + 消防入口 + 转弯半径标注 | 红虚线 + 消防图标库（消火栓、登高面阴影）+ 半径数值 | 中 |
| A4 | **景观绿地规划设计分析图** | P53 | 类似页 | 景观主轴/次轴 + 节点 + 绿地多边形 + 视线分析 | 主次轴线（粗细差异）+ 节点圆 + 视线虚线 + 文化叙事文字 | 中 |
| A5 | **场地设计竖向分析图** | P56 | 类似页 | 标高点 + 坡向箭头 + 排水方向 + 等高线（可选）| 三角标高 + 单方向箭头 + 蓝色水流箭头 + 标注 | 中 |
| A6 | **日照分析图** | P50 | 类似页 | 阴影区域(冬至/春秋分) + 建筑投影 + 受影响范围 | 阴影色块（不同时刻不同透明度）+ 太阳角度图标 | 高（可能需太阳几何计算）|
| A7 | **绿化设计图** | P51 | 类似页 | 乔木/灌木/草坪多边形 + 树种图标 + 重点节点植物配置 | 树种图标库 + 绿色色阶 + 节点标注 | 中高 |
| A8 | **配套分析图** | P57 | 类似页 | 周边公共服务点 + 服务半径圆（300m/500m/1000m）+ 项目位置 | POI 图标 + 同心圆 + 距离标注 | 中 |
| A9 | **海绵城市分析图** | P58 | 类似页 | 透水铺装/绿地多边形 + 雨水径流箭头 + 蓄水节点 | 蓝色水流箭头 + 透水图例色 + 节点图标 | 中高 |
| A10 | **无障碍设计图** | P59 | 类似页 | 无障碍主流线 + 无障碍出入口 + 无障碍卫生间/电梯 | 蓝色无障碍图标库 + 流线 | 中 |
| A11 | **人防设计图** | P60 | 类似页 | 地下室人防分区 + 人防出入口 + 平战转换标注 | 黄色分区 + 人防符号 + 文字标注 | 中 |

### Category B — 区位 / 风貌图（工作台部分覆盖，需要外部数据）

| # | 图种 | 启泰 PDF 页 | 数据源 | 工作台角色 |
|---|---|---|---|---|
| B1 | **区位分析图** | P37 | 城市级地图 / 高德静态地图 | 工作台只做项目点 + 地标标注 + 半径圆叠加；底图建议接高德静态地图 API |
| B2 | **风貌区位图** | P40 | 卫星图 + 风貌区划线 | 类似 B1，加风貌分区多边形叠加 |
| B3 | **基地现状与条件图** | P38 | 现场照片拼贴 + 标注 | 工作台简化版：照片缩略图组合 + 标注文字框 |
| B4 | **基地基本信息** | P39 | 表格 + 关键坐标 + 红线导出 | 不属于工作台范围；S2 现有 CAD 预览 + record.md 表格已经够 |

### Category C — 单体 / 材料 / 风貌对比（工作台不覆盖）

| # | 图种 | 启泰 PDF 页 | 不覆盖原因 |
|---|---|---|---|
| C1 | 单体设计 | P61 | 需要 3D 建模或建筑平面，不属于"在总平叠分析图"工作流 |
| C2 | 文化元素提取 | P62 | 图片+文字排版工作，走 S9/S10 汇报排版即可 |
| C3 | 立面材料 | P63 | 需要立面图 + 材质贴图，专门工具 |
| C4 | 风貌设计对比 | P41-P42 | 多张参考图 + 文字对比，走 S9 排版 |
| C5 | 鸟瞰 / 透视渲染 | P45-P49 | 需要 SU 模型 + 渲染器，专门工具 |
| C6 | 真实技术图纸 | P64-P105 | 各层平面/立面/剖面/屋顶/地下室/图签 —— 这些是 CAD 直出，不在工作台范围 |
| C7 | 设计说明 | P106-P159 | 纯文字章节，走 S9 |
| C8 | 对比方案 | P160-P170 | 多方案对比排版，走 S9 |

## 实施波次顺序

每波内部：抠模板 → 实现 → 实测 → 收口 → 进下一波。

### Wave 1（启动波）—— A1 功能分区图 + A2 交通组织图 + Wave 0 基础设施

**时间估**：3-4 天

实施清单：
- 完成 Wave 0（R1-R8 + F3）所有基础设施
- VLM 抠 A1 模板（启泰 P52 + 长江同类页）→ `templates/functional_zoning.json`
- VLM 抠 A2 模板（启泰 P54 + 长江同类页）→ `templates/traffic_analysis.json`
- 实现 A1 + A2 渲染逻辑（render.py / export.py 重写到模板驱动）
- BQ-PARK 实测：上传一张底图 → 画一张 A1 + 一张 A2 → 输出 PNG/PDF
- 对照启泰 P52 / P54 评 visual gap，调模板
- 在本文件回写"已收口"+ 截图描述

**验收标准**：visual gap ≤ "看起来像同一事务所、不同项目的图"。允许配色不完全相同，但风格规范、可读性、信息层级要匹配。

### Wave 2（核心补全）—— A3 消防流线 + A5 竖向分析

**时间估**：2-3 天

理由：A3 复用 A2 大部分能力（箭头 + 流线 + 入口图标），A5 引入新原语（标高点 + 坡向箭头 + 排水箭头）。

实施清单：
- VLM 抠 A3 + A5 模板
- 在 Wave 1 渲染框架上加 A3 / A5 渲染逻辑
- 加新原语：fire_route_arrow, fire_entrance, fire_hydrant, elevation_point, slope_arrow, drainage_arrow
- BQ-PARK 实测，调模板
- 收口

### Wave 3（景观 + 绿化）—— A4 景观分析 + A7 绿化设计

**时间估**：3-4 天

理由：两者都涉及节点 + 轴线 + 图标库。一波内统一引入图标库基础设施。

实施清单：
- 引入树种/景观节点图标库（SVG icons）
- VLM 抠 A4 + A7 模板
- 渲染逻辑
- BQ-PARK 实测
- 收口

### Wave 4（专项补全）—— A8 配套 + A10 无障碍 + A11 人防

**时间估**：3-4 天

理由：都是图标 + 流线 + 半径圆 类型，可在 Wave 3 基础设施上批量加。

实施清单：
- VLM 抠三种模板
- 渲染逻辑（多用 Wave 3 的图标库）
- 实测 + 收口

### Wave 5（高复杂度）—— A6 日照 + A9 海绵城市

**时间估**：4-5 天

理由：A6 可能需要太阳几何计算（按经纬度 + 日期算阴影），A9 需要透水分级色阶 + 水流网络。这两个是 Category A 里最复杂的。

实施清单：
- A6：决定是否引入太阳几何计算（pysolar 等），或退一步只支持用户手画阴影区域 → 模板套印
- A9：透水/不透水多级色阶 + 水流箭头网络
- VLM 抠模板 + 渲染
- 实测 + 收口

### Wave 6（区位类，可选）—— B1 区位分析 + B2 风貌区位

**时间估**：2-3 天

理由：B1/B2 需要城市级地图底图，建议接高德静态地图 API（项目已有 AMap key）。

实施清单：
- 接高德静态地图：按项目中心点 + zoom 拉取底图
- B1：项目点 + 服务半径圆 + 地标 POI 叠加
- B2：风貌分区多边形叠加
- 实测 + 收口

### Wave 7（B3 基地现状）—— 现场照片标注

**时间估**：1-2 天

理由：简化版工作台，照片网格 + 标注文字框。可能不需要 normalized coords，直接像素坐标即可。

## VLM 抠模板的具体协议

每波启动时，对该图种的参考 PDF 页执行：

```text
输入：参考 PDF 的该图种页（图像 + 抽取的文字层）
任务：让 VLM 输出该图种的 templates/{drawing_type}.json，含：
  - palette: { object_type: { stroke, fill, opacity, label_bg } }
  - line_style: { object_type: { width, dash_pattern, line_cap } }
  - arrow_style: { object_type: { head_type, head_size, head_color } }
  - icon_lib: { object_type: SVG icon string or icon path }
  - label_style: { font_size, font_weight, bubble_radius, bubble_padding, leader_line }
  - legend_layout: { position, columns, row_height, font }
  - chrome: { scale_bar, north_arrow, title_block, drawing_type_label }
```

VLM 调用方式：
- 用 Claude with vision 直接 chat：贴 PDF 页截图 + 上面的 schema 要求
- 或者通过 `_tools/vision_route.py` 走仓库视觉 provider
- 输出 JSON 由人复核一次（VLM 可能配色读偏）后入仓
- **不在 per-render 路径上调用 VLM**，只在新增图种 / 调整风格时调用

## 工作台核心 schema 扩展（按需追加）

每波可能需要新增 object_type。当前 schema 已有：
- `functional_zone, vehicle_flow, pedestrian_flow, main_entrance, label`

按波次扩展（每波在该波 PR 内同步扩展 schema.py 的 `OBJECT_TYPES` enum）：

- Wave 2：`fire_route, fire_entrance, fire_hydrant, elevation_point, slope_arrow, drainage_arrow`
- Wave 3：`landscape_axis_primary, landscape_axis_secondary, landscape_node, view_corridor, tree_zone, planting_node`
- Wave 4：`poi_marker, service_radius, accessible_route, accessible_facility, civil_defense_zone, civil_defense_marker`
- Wave 5：`shadow_zone, solar_path, permeable_zone, water_flow, storage_node`
- Wave 6：`city_landmark, fengmao_zone`
- Wave 7：`photo_annotation`

每波内 schema.py 同步 PR，但**已上线波的 object_type 不准改语义**（向后兼容）。

## 不做事项

- 不引入图像生成模型做 per-render（不可重复、漂移、违反技术图确定性）
- 不进 Category C（单体/材料/真实技术图纸）
- 不引入 React/Vue/D3 等框架（保持原生 Canvas + SVG）
- 不引入 headless browser（PNG 用 cairosvg / Pillow）
- 不动 record.md / schema / inventory.json（除非新加 drawing_type 影响 S9/S10 marker，那时单独提案）
- 不在 Wave 1-2 内做 智能吸附 / vector CAD 提取（被参考 PDF 的实际做法证伪，不需要）

## 各波完成的回顾点

每波收口时，在本文件 append 一段：

```markdown
### Wave X 收口（YYYY-MM-DD）

- commit: <hash>
- 实施图种：A?, A?
- 实测项目：26-BQ-PARK / ...
- 输出文件：projects/.../rendered/{drawing_type}.png
- visual gap 自评（对照参考 PDF）：可接受 / 需补 / 待重做
- 下一波建议起始时间：YYYY-MM-DD
```

reviewer 据此跟踪整体进度。

## 收尾里程碑

Wave 1-4 完成后，工作台覆盖 7 种最常用的分析图（功能/交通/消防/竖向/景观/绿化 + 配套/无障碍/人防三选二），足够支撑 S9 汇报文档生成阶段的图源需求。Wave 5-7 视项目实际需要再推。

S9 SKILL.md 增强（Stage A 重排版）需要等 Wave 1 验收通过后再启动——那时 S9 草稿生成器有真实成品图可以引用，不会再产出"光文字没图"的草稿。

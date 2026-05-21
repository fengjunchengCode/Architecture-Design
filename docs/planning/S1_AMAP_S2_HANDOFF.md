# S1 高德地图接入与 S2 合成底图交接文档

状态：审核草案  
日期：2026-05-21  
适用项目：`26-BQ-PARK`，也可作为后续同类项目的 S1/S2 协作模板  
注意：本文档是交接计划，不是当前生效的 skill 规范。审核通过后，应把必要约束同步到 `skills/S1_site_analysis/SKILL.md`、`skills/S2_dwg_parse/SKILL.md` 和相关工具。

## 1. 背景与目标

当前工作流中，S2 已能通过 ODA File Converter + `ezdxf` 从 DWG 转 DXF 并提取候选红线、面积、周长、外包框、图层和文字样本。以 `26-BQ-PARK` 为例，S2 初步识别到疑似红线：

- DXF handle：`1306`
- 类型：闭合 `LWPOLYLINE`
- 图层：`0`
- 顶点数：29
- 候选面积：约 `15052.575` 图纸单位平方
- 外包框：约 `194.212 x 130.056`
- 状态：候选红线，未人工确认

问题是：S2 当前偏 CAD 几何事实，无法独立回答“主入口应靠哪边、主要道路从哪里来、河流/桥梁/文化节点如何影响总平面”。S1 应补充高德地图和视觉 sidecar 中的外部关系，形成可供 S2 合成底图使用的“地图语义层”。

本交接文档目标：

1. 定义 S1 如何接入高德官方 Skill/API。
2. 定义 S1 应写入 `record.md` 的结构。
3. 定义 S1 给 S2 的机器可读接口。
4. 说明没有 CAD-地图控制点时如何做语义叠合。
5. 建议 S2 输入如何调整，以便读取 S1 外部关系并生成合成底图。

## 2. 高德官方 Skill 的角色分工

高德官方 Skill 文档提供两个基础 Skill：

- `amap-lbs-skill`：LBS 综合服务。适合 POI 搜索、周边搜索、路径规划、旅游规划、地图链接生成。
- `amap-jsapi-skill`：前端地图开发。适合地图初始化、覆盖物绘制、图层管理、矢量图形、绘制工具和交互式控制点拾取。

S1 阶段建议默认使用 `amap-lbs-skill`，因为 S1 需要的是结构化 LBS 数据，而不是开发一个交互地图页面。

后续若要人工点选控制点、在地图上交互叠加 CAD 红线、生成可审查网页，再引入 `amap-jsapi-skill`。

官方配置要求：

- `amap-lbs-skill`：需要 `AMAP_WEBSERVICE_KEY`。
- `amap-jsapi-skill`：需要 `AMAP_JSAPI_KEY` 和 JSAPI 安全密钥。

参考链接：

- 高德基础能力 Skill：https://lbs.amap.com/api/skill/ready-to-use/summary
- 地理/逆地理编码：https://lbs.amap.com/api/webservice/guide/api/georegeo
- 搜索 POI：https://lbs.amap.com/api/webservice/guide/api-advanced/search
- 路径规划：https://lbs.amap.com/api/webservice/guide/api/direction
- 静态地图：https://lbs.amap.com/api/webservice/guide/api/staticmaps
- 坐标转换：https://lbs.amap.com/api/webservice/guide/api/convert

## 3. 坐标边界：必须避免的误用

高德返回的经纬度属于高德地图坐标体系，通常记为 GCJ-02 / AMap 坐标。

当前 DWG 坐标是 CAD/测绘工程坐标，且 DXF header 中 `$INSUNITS = 0`，没有明确坐标系声明。

因此：

- 不能把高德坐标直接套到 DWG 坐标上。
- 不能用单个高德坐标点推导 CAD 到地图的旋转、比例和平移。
- 高德“坐标转换”接口只适用于 GPS、百度、mapbar、高德等经纬度体系之间转换，不能把未知 CAD 工程坐标自动转成高德坐标。

默认合成模式应是：

```yaml
registration:
  mode: semantic_only
  map_crs: GCJ-02 / AMap
  cad_crs: unknown
  precise_transform_possible: false
  reason: "缺少高德地图与 DWG 坐标的共同控制点"
```

如果未来能提供控制点，才可升级：

- 2 个共同点：可做近似平移、旋转、比例匹配。
- 3 个及以上共同点：可做仿射变换。
- 推荐控制点：桥头、道路交叉口、建筑角点、红线角点、明显硬化边界角点。

## 4. S1 执行输入

S1 agent 接手前应读取：

```text
AGENTS.md
SKILL.md
skills/S1_site_analysis/SKILL.md
skills/_shared/*.md 中与 record、marker、confidence、output 相关的协议
projects/{code}/05_output/record.md
projects/{code}/05_output/inventory.json
projects/{code}/05_output/vision/index.json
projects/{code}/05_output/vision/*.vision.json
projects/{code}/05_output/dwg_probe.json
```

对于 `26-BQ-PARK`，还应关注：

- 区位图 sidecar：识别到 `G317`、`索巴二线`、`盐曲`、河流、桥梁、县城行政节点。
- 现场照片 sidecar：识别到道路、桥梁、河流、经幡、佛塔/藏式建筑、电线杆/高压线、施工场地、硬化停车或道路空间。
- S2 候选红线：`handle 1306`，但尚未人工确认。

## 5. S1 使用高德的推荐流程

### 5.1 地理编码

目的：获取项目中心的大致地图坐标、行政区划编码和匹配级别。

建议查询组合：

```text
西藏自治区那曲市巴青县拉西镇 巴青县城西口袋公园
巴青县城西口袋公园
巴青县人民政府 拉西镇
G317 巴青县 拉西镇
```

S1 应记录：

- 查询文本
- 返回坐标 `coords_gcj02`
- `adcode`
- `citycode`
- `level`
- 置信度
- 选择该结果的原因

### 5.2 逆地理编码

目的：从场地中心坐标获取附近道路、POI、AOI 和道路交叉口。

建议：

- 使用 `extensions=all`
- 半径优先 `1000m`
- 若结果稀疏，增加到 `2000m`
- 不要把逆地理编码返回地址当成 CAD 红线边界

S1 应提取：

- 道路名称
- 道路交叉口
- 主要 POI
- AOI 或行政/地名线索
- 与视觉 sidecar 的一致/冲突点

### 5.3 周边搜索

目的：建立场地外部功能与交通关系。

建议搜索半径：

- `500m`：直接可达环境
- `1000m`：步行与慢行联系
- `2000m`：县城级公共节点和旅游到达关系

建议搜索关键词或类型：

```text
G317
桥
河流
巴青县人民政府
拉西镇政府
停车场
公园
景区
寺庙
佛塔
学校
医院
公交
```

输出时不要求全量 POI，只保留对设计有影响的节点：

- 交通节点
- 行政/公共服务节点
- 宗教/文化节点
- 旅游/停留节点
- 居住或村落节点
- 水系和桥梁节点

### 5.4 路径规划

目的：判断主要来向和可达性，不是生成总平面精确入口。

可选路线：

- 县城行政节点到场地中心
- G317 可识别节点到场地中心
- 桥梁/道路节点到场地中心
- 停车或硬化场地节点到场地中心

输出：

- 路线类型：驾车/步行
- 距离
- 时间
- 主要来向
- 对主入口/次入口候选的影响

## 6. S1 写入 `record.md` 的推荐结构

S1 只允许改写：

```markdown
<!-- BEGIN:s1_site_analysis -->
...
<!-- END:s1_site_analysis -->
```

建议正文标题固定为：

```markdown
## S1 区位与外部关系分析

### S1 输入与数据源
### 高德定位与行政区划
### 周边道路与到达关系
### 水系、桥梁与文化节点
### 现场约束与机会
### 主次入口候选
### S1 -> S2 合成底图接口
### 低置信与待复核
### 对 S2/S3/S9 的影响
```

其中 `S1 -> S2 合成底图接口` 必须出现，并包含一个短 YAML 块，供后续 agent 稳定抽取。

## 7. `record.md` 中的 S1 -> S2 接口格式

建议写入如下 YAML 代码块：

```yaml
s1_map_context:
  location_fix:
    query: "西藏自治区那曲市巴青县拉西镇 巴青县城西口袋公园"
    coords_gcj02: [null, null]
    adcode: null
    citycode: null
    geocode_level: null
    source: amap_geocode
    confidence: low
    evidence:
      - "高德地理编码结果"
      - "区位图视觉 sidecar"

  registration:
    mode: semantic_only
    map_crs: GCJ-02 / AMap
    cad_crs: unknown
    precise_transform_possible: false
    transform_status: not_available
    reason: "缺少高德地图与 DWG 坐标共同控制点"

  external_edges:
    - edge_label: road_side
      relation: "G317 / 现状道路主要到达方向"
      preferred_design_use: "主入口、车行到达、服务入口候选"
      confidence: medium
      evidence:
        - "高德道路/POI 检索"
        - "区位图/现场照片 sidecar"
    - edge_label: river_side
      relation: "河流、桥梁、经幡/佛塔文化景观方向"
      preferred_design_use: "慢行入口、观景节点、文化打卡路径候选"
      confidence: medium
      evidence:
        - "高德 POI/地名检索"
        - "现场照片 sidecar"

  access_candidates:
    - type: main
      relation_basis: road_side
      design_reason: "对外可达性、停车/服务组织和施工进入更稳定"
      confidence: medium
    - type: secondary_or_scenic
      relation_basis: river_side
      design_reason: "结合滨水、桥梁、经幡/佛塔等文化景观"
      confidence: low

  s2_join_hints:
    overlay_mode: semantic_only
    usable_for_precise_transform: false
    usable_for_semantic_overlay: true
    map_center_gcj02: [null, null]
    cad_redline_candidate_handle: "1306"
    control_points_needed:
      - "CAD 红线角点对应的高德地图可识别点"
      - "桥头、道路交叉口、建筑角点等至少 2-3 个共同点"
```

执行 agent 应把 `null` 替换为实际高德返回值；若高德没有可信结果，应保留 `null` 并说明原因，不得编造。

## 8. 派生 JSON 文件建议

`record.md` 是核心真相，但不适合存放全部高德原始返回。

建议派生文件：

```text
projects/{code}/05_output/amap/s1_amap_raw.json
projects/{code}/05_output/amap/s1_map_context.json
```

规则：

- `s1_amap_raw.json`：保存高德原始响应、查询参数、时间戳、错误信息。
- `s1_map_context.json`：保存从 S1 marker 可重建的机器上下文。
- 派生 JSON 不替代 `record.md`。
- 若 JSON 与 `record.md` 冲突，以 `record.md` 为准。

S1 marker 中应引用：

```markdown
原始高德查询结果见：`05_output/amap/s1_amap_raw.json`
机器可读地图上下文投影见：`05_output/amap/s1_map_context.json`
```

## 9. 建议调整 S2 输入

当前 S2 输入主要是：

```text
record.md
inventory.json
02_site/地形图/
dwg_probe.json
```

建议 S2 增加读取：

```text
record.md 的 s1_site_analysis marker
可选：05_output/amap/s1_map_context.json
可选：05_output/cad/redline_candidate_*.geojson
```

S2 合成底图的输入分工：

| 来源 | 内容 | 用途 |
|---|---|---|
| S2 / `dwg_probe.json` | CAD 红线候选、顶点、面积、周长、bbox、高差候选 | 绘制场地本体 |
| S1 / `record.md` | 道路、水系、桥梁、POI、入口候选、主次来向 | 绘制外部关系箭头和标签 |
| 高德派生 JSON | 原始证据和可追溯查询结果 | 复核和再运行 |
| 人工控制点 | CAD 与地图共同点 | 升级精确套合 |

默认合成底图应标注：

```text
候选红线，未人工确认
地图关系为语义叠合，非精确套图
高德坐标与 CAD 坐标未配准
```

## 10. S2 工具建议

为让 S1/S2 更顺，建议后续改造 `_tools/dwg_probe.py` 或新增 CAD 可视化工具：

1. 对候选闭合多段线导出完整顶点数组 `vertices_xy`。
2. 支持指定 handle 导出：
   - SVG
   - PNG
   - local GeoJSON
3. 给红线候选增加机器字段：
   - `candidate_role: redline_candidate`
   - `confidence`
   - `reason`
4. 增加高程解析摘要：
   - 带 Z 实体数量
   - 疑似高程文字样本
   - 有效高程 min/max/delta
   - 高差置信度

注意：高程点和等高线语义不明时，只输出候选和待复核，不要强行写最大高差。

## 11. 验收标准

S1 实现可通过审核的最低标准：

1. `record.md` 的 `s1_site_analysis` marker 已写入，不再是 `_pending`。
2. S1 记录高德查询来源、坐标来源、行政区划、匹配级别和置信度。
3. S1 明确输出 `registration.mode`，默认应为 `semantic_only`。
4. S1 输出道路、水系、桥梁、文化节点和入口候选。
5. S1 有固定小节 `S1 -> S2 合成底图接口`。
6. S1 不伪造 CAD-地图精确坐标转换。
7. S2 能读取 S1 接口，生成候选红线 + 外部关系箭头/标签的合成底图。
8. 所有不确定项进入低置信或待复核说明。

## 12. 给审核 agent 的重点问题

请审核以下点：

1. S1 YAML 接口是否足够稳定，后续 agent 是否容易解析。
2. `record.md` 中放短 YAML、派生 JSON 中放原始响应的分工是否合适。
3. `semantic_only` 是否应作为无控制点时的强制默认。
4. S2 是否应强制读取 S1 marker 后再生成合成底图。
5. 是否需要新增 `_tools/amap_context.py`，把高德查询变成确定性脚本，而不是完全交给 agent 手动调用 Skill。
6. 是否需要把 `s1_map_context` 纳入 schema，还是先保持为 marker 内机器可读块。

## 13. 推荐实施顺序

1. 审核本交接文档。
2. 更新 `skills/S1_site_analysis/SKILL.md`：加入高德 Skill 流程和固定输出结构。
3. 更新 `skills/S2_dwg_parse/SKILL.md`：加入读取 S1 接口和合成底图要求。
4. 可选新增 `_tools/amap_context.py`：统一调用高德 Web Service 并生成原始 JSON。
5. 可选增强 `_tools/dwg_probe.py`：导出完整顶点、高程摘要和红线候选角色。
6. 对 `26-BQ-PARK` 执行 S1。
7. 生成 S1/S2 合成底图第一版：候选红线 + 道路/河流/入口方向箭头。


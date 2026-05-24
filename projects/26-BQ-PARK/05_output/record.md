---
schema_version: '1.0'
project:
  code: 26-BQ-PARK
  name: 巴青县城西口袋公园建设项目
  client: 巴青县人民政府
  type: park
  scale: 口袋公园
  stage: 方案设计
  updated_at: '2026-05-23T18:04:57+08:00'
site:
  address: 西藏自治区那曲市巴青县拉西镇
  coords: null
  area_sqm: null
  far_max: null
  height_limit_m: null
  setback: null
  has_elevation_diff: true
  boundary_shape: null
style_preferences:
  keywords:
  - 巴青县本地特色
  - 旅游打卡点
  references: null
  client_raw_quotes: "业主无特殊要求，所有建设内容由设计自行考虑，投资无上限，只强调突出巴青县本地特色，打造成为巴青县旅游打卡点。"
brief:
  summary: "在巴青县拉西镇地形图内用地红线范围新建口袋公园。业主要求突出巴青县本地特色，打造成为旅游打卡点。投资无上限，设计自行考虑所有建设内容。提交成果包括方案、估算、效果图。"
pending_questions:
- id: q001
  field: site.area_sqm
  question: "用地红线范围的具体坐标和面积是多少？"
  raised_by: S0
  status: 待问
  answer: null
  answered_at: null
- id: q002
  field: project.scale
  question: "设计规模和面积指标有无具体要求？"
  raised_by: S0
  status: 待问
  answer: null
  answered_at: null
- id: q003
  field: brief.budget
  question: "投资预算的具体数字是多少？"
  raised_by: S0
  status: 待问
  answer: null
  answered_at: null
- id: q004
  field: brief.deadline
  question: "设计周期和提交时间是什么时候？"
  raised_by: S0
  status: 待问
  answer: null
  answered_at: null
- id: q005
  field: brief.functional_zones
  question: "是否有特殊的功能需求（如儿童游乐、健身设施、休憩空间等）？"
  raised_by: S0
  status: 待问
  answer: null
  answered_at: null
- id: q006
  field: site.coords
  question: "场地高程数据和地形测绘图是否可以提供？"
  raised_by: S0
  status: 待问
  answer: null
  answered_at: null
low_confidence_fields:
- field: site.address
  value: "西藏自治区那曲市巴青县拉西镇"
  reason: "从区位图推断，需人工确认具体地址"
- field: site.coords
  value: null
  reason: "区位图中有红色标记框，但精确坐标需人工确认"
completeness:
  filled_required_pct: 65
  ready_for:
  - S4
  blocked:
  - skill: S3
    reason: "需先完成 S1 基于高德上下文与 S2 控制点的区位/道路/入口细化，不应直接进入面积策划。"
  - skill: S9
    reason: "S3 尚未执行，且 S1/S2 合成结论仍需确认。"
files_indexed:
- path: "01_briefing/2026-04-22巴青县城西口袋公园建设项目.docx"
  sha1: "24f91e9be3a7102a7dd5db96d4a2951b41743f80"
  parsed_at: "2026-05-19T23:30:00+08:00"
  parsed_by: S0
- path: "02_site/区位图/中.png"
  sha1: "f034c5a2a2a9b4a6a82e27986c2d96e0adc15b55"
  parsed_at: "2026-05-19T23:30:00+08:00"
  parsed_by: S0
- path: "02_site/区位图/大.png"
  sha1: "b681cf5e0f81b524c00bf97980e1c77f95d8eea6"
  parsed_at: "2026-05-19T23:30:00+08:00"
  parsed_by: S0
- path: "02_site/区位图/小.png"
  sha1: "7e7aef2ea9577a6ea335b1a337a093fac1a50e41"
  parsed_at: "2026-05-19T23:30:00+08:00"
  parsed_by: S0
- path: "02_site/地形图/口袋公园.dwg"
  sha1: "adfe6e63cffc269159735f19ede142b49d7fc925"
  parsed_at: "2026-05-19T23:30:00+08:00"
  parsed_by: S0
- path: "02_site/地形图/口袋公园_t8.dwg"
  sha1: "a51e1bb62ceac321717b4ddff5c0ee6a9941fcef"
  parsed_at: "2026-05-19T23:30:00+08:00"
  parsed_by: S0
- path: "02_site/现场照片/IMG_20260422_141900.jpg"
  sha1: "13b003e1b7d8e3129bee934763ece8cb7f9a1344"
  parsed_at: "2026-05-19T23:30:00+08:00"
  parsed_by: S0
- path: "02_site/现场照片/IMG_20260422_141927.jpg"
  sha1: "ec435b3e17c494b62e8ebb343f0264af7d61f207"
  parsed_at: "2026-05-19T23:30:00+08:00"
  parsed_by: S0
- path: "02_site/现场照片/IMG_20260422_142054.jpg"
  sha1: "61afe276efeacc6d40ab3060591ffd93ea7f3e02"
  parsed_at: "2026-05-19T23:30:00+08:00"
  parsed_by: S0
- path: "02_site/现场照片/IMG_20260422_142114.jpg"
  sha1: "1a8af9f5eadc0a632834787b9523c2ccd356bdd9"
  parsed_at: "2026-05-19T23:30:00+08:00"
  parsed_by: S0
- path: "02_site/现场照片/IMG_20260422_142315.jpg"
  sha1: "94dc37ba76a4609c2eb9dfc91947e24dce56e280"
  parsed_at: "2026-05-19T23:30:00+08:00"
  parsed_by: S0
- path: "02_site/现场照片/IMG_20260422_142319.jpg"
  sha1: "4c7c642a43a96a5e5908c64e4e8d2a85338b02e9"
  parsed_at: "2026-05-19T23:30:00+08:00"
  parsed_by: S0
- path: "02_site/现场照片/IMG_20260422_142636.jpg"
  sha1: "16e23bbea0286e5f0b02b85b694bb53975891cf9"
  parsed_at: "2026-05-19T23:30:00+08:00"
  parsed_by: S0
- path: "02_site/现场照片/IMG_20260422_142640.jpg"
  sha1: "5e6826952880d7788f41bf924066d28def0928f1"
  parsed_at: "2026-05-19T23:30:00+08:00"
  parsed_by: S0
- path: "02_site/现场照片/IMG_20260422_142717.jpg"
  sha1: "31a2930fde25cff19a96e3d8e6700abbbe247697"
  parsed_at: "2026-05-19T23:30:00+08:00"
  parsed_by: S0
- path: "02_site/现场照片/IMG_20260422_142720.jpg"
  sha1: "1f394d33979f573d855e3b9b4f7669bfc3d6865f"
  parsed_at: "2026-05-19T23:30:00+08:00"
  parsed_by: S0
- path: "02_site/现场照片/IMG_20260422_142726.jpg"
  sha1: "d6e0a0688c2e493f2abb5d457e44f5869bd89c66"
  parsed_at: "2026-05-19T23:30:00+08:00"
  parsed_by: S0
- path: "02_site/现场照片/IMG_20260422_142738.jpg"
  sha1: "997b2d581bc324a9d29211a6c75ea52733a256f5"
  parsed_at: "2026-05-19T23:30:00+08:00"
  parsed_by: S0
- path: "02_site/现场照片/IMG_20260422_142741.jpg"
  sha1: "23775c725f11e713174dd2311da23f4144acb1ab"
  parsed_at: "2026-05-19T23:30:00+08:00"
  parsed_by: S0
---

# 项目档案：26-BQ-PARK 巴青县城西口袋公园建设项目

<!-- BEGIN:s0_parsed -->

## S0 项目档案初始化结果

### 已确认事实

| 字段 | 值 | 来源 |
|------|-----|------|
| 项目名称 | 巴青县城西口袋公园建设项目 | 任务书 |
| 建设单位 | 巴青县人民政府 | 任务书 |
| 建设地点 | 西藏自治区那曲市巴青县拉西镇 | 任务书 + 区位图 |
| 项目类型 | 公园（口袋公园） | 任务书 |
| 设计阶段 | 方案设计 | 任务书 |
| 提交成果 | 方案、估算、效果图 | 任务书 |
| 调查人员 | 吴玉风（17713453558） | 任务书 |
| 调查日期 | 2026年4月22日 | 任务书 |

### 区位与场地条件（视觉模型解析）

**区位特征**：
- 位于西藏自治区那曲市巴青县县城区域
- G317国道沿线，高原河谷地貌
- 城镇主要沿国道和河流呈条带状分布
- 四周为高大山脉，山谷底部相对平坦

**场地现状**：
- 高海拔山区河谷地貌，地表为砂石和泥土
- 植被稀疏，生态脆弱
- 有河流流经场地，河岸有经幡等文化设施
- 场地内有施工机械和土方作业迹象
- 周边有电力设施、道路、桥梁等基础设施

**文化元素**：
- 经幡（玛尼旗）：场地内多处可见，具有宗教文化意义
- 佛塔：场地附近有藏式佛塔建筑
- 藏文经文建筑：对岸有红色藏文经文建筑

### 建设意见摘要

> 地形图内用地红线范围新建口袋公园，业主无特殊要求，所有建设内容由设计自行考虑，投资无上限，只强调突出巴青县本地特色，打造成为巴青县旅游打卡点。

### 视觉资产处理

- 区位图：3 张 PNG 已通过视觉模型解析，识别出地理位置、道路、标记框
- 现场照片：13 张 JPG 已通过视觉模型解析，识别出现场条件、文化元素、基础设施
- 地形图：4 个 DWG 文件已登记，待 S2 阶段解析

<!-- END:s0_parsed -->

<!-- BEGIN:s1_site_analysis -->
## S1 区位与外部关系分析结果

### S1 输入与定位证据

本次 S1 使用四类证据，不直接读取图片原文件：

- 高德上下文：已重新运行 `python _tools/amap_context.py 26-BQ-PARK --location "94.032582,31.92547" --write`，输出 `05_output/amap/s1_map_context.json` 与 `05_output/amap/s1_amap_raw.json`。
- 区位图视觉 sidecar：`05_output/vision/02_site__区位图__中.png.vision.json`、`大.png.vision.json`、`小.png.vision.json`。
- S2 几何结果：已识别候选红线 handle `1306`，候选面积约 `15052.575` 图纸单位平方。
- S2 控制点与配准报告：用户已录入 8 个“CAD 点 ↔ 高德 GCJ-02 点”，当前点位来自红线顶点候选，默认属于 `redline_corner / registration`；`cad_align.py` 输出 `aligned_partial`，最佳内点为 `CAD-02`、`CAD-03`、`CAD-05`、`CAD-06`、`CAD-08`、`CAD-07`。

高德逆地理编码将中心点定位到“西藏自治区那曲市巴青县拉西镇曲登纳桥”，中心点来源为用户输入的高德坐标，定位置信度为 high。高德本次未直接返回 `roads` 或 `road_intersections` 对象；道路线索主要来自高德 POI 地址文本和区位图 sidecar 的互证。最关键的新证据是：高德返回的“曲登纳桥”坐标距用户录入的 `CAD-07` 约 `4m`，且 `CAD-07` 属于最佳内点，因此桥头/北侧界面可以从普通候选提升为强候选。

### 配准状态

```yaml
s1_external_context:
  registration_state: map_located
  cad_alignment:
    quality: aligned_partial
    alignment_report: "05_output/amap/cad_alignment_report.json"
    point_count: 8
    best_fit:
      inliers: ["CAD-02", "CAD-03", "CAD-05", "CAD-06", "CAD-08", "CAD-07"]
      outliers: ["CAD-01", "CAD-04"]
      rms_error_m: 2.89
      max_inlier_error_m: 4.55
    reason_for_not_cad_aligned: "现有控制点主要是红线角点，未包含 road_intersection/road_edge/bridge_endpoint 等语义控制点；高德也未返回可校验的道路/交叉口几何，且 CAD-01/CAD-04 仍为外点。可做候选边筛选，但不能做高置信落边。"
  coordinate_evidence:
    address: "西藏自治区那曲市巴青县拉西镇曲登纳桥"
    amap_gcj02: "94.032582,31.925470"
    wgs84_for_record: null
    source: "uploader_ui / user_provided_amap_picker_coordinate / amap_context.py"
    confidence: high
  location_evidence:
    - "AMap reverse geocode: 西藏自治区那曲市巴青县拉西镇曲登纳桥"
    - "AMap regeo roads=[] and road_intersections=[]; no direct road geometry was returned."
    - "AMap keyword 桥: 曲登纳桥，距中心约 84m；与 CAD-07 对应点距离约 4m。"
    - "AMap POI address clue: 棍郭社区居民委员会位于 317国道与650乡道交叉口东南200米，距中心约 125m。"
    - "区位图小范围图识别：红框地块靠近盐曲、G317、索巴二线和跨河桥梁"
    - "区位图中范围图识别：巴青县城沿河谷、G317 和城镇道路带状展开"
  amap_context:
    roads:
      - "G317：区位图识别 + 高德 POI 地址出现 317国道；高德 regeo 未返回道路对象。"
      - "650乡道：高德 POI 地址线索为 317国道与650乡道交叉口附近；需地图或现场复核。"
    water:
      - "盐曲（区位图识别）"
      - "曲登纳桥（高德逆地理/关键词检索 + CAD-07 控制点互证）"
    poi_500m:
      design_relevant_candidates:
        - "曲登纳桥约 84m：与 CAD-07 基本吻合，是北侧/桥头界面判断的强证据。"
        - "棍郭社区居民委员会约 125m：地址含 317国道与650乡道交叉口东南200米，可作为近场道路线索。"
    poi_1000m:
      design_relevant_candidates:
        - "巴青县客运站约 600m：仅作为区域到达/游客来向候选，不能直接决定入口。"
        - "巴仓寺、拉西镇政府广场：仅作为文化/公共活动叙事候选，需结合设计定位取舍。"
      raw_poi_note: "商业、餐饮、超市等 POI 仅保留在 05_output/amap/s1_map_context.json，不作为默认设计结论。"
    transit_or_routes:
      - "巴青县客运站约 600m"
  external_features:
    primary_roads:
      - "G317"
    secondary_roads:
      - "650乡道（待复核）"
    barriers:
      - "盐曲河流"
      - "索巴二线/铁路（区位图识别，需复核）"
    landscape_or_culture_nodes:
      - "曲登纳桥"
      - "巴仓寺"
      - "拉西镇政府广场"
  approach_vectors:
    - "区域主要到达依托 G317；项目应优先考虑来自县城与 G317 沿线的车行/步行来向。"
    - "近场最可靠的可落图线索是曲登纳桥，当前可把 CAD-07 所在北侧/桥头界面作为主入口强候选带。"
    - "317国道/650乡道交叉口目前来自 POI 地址线索，不是高德道路几何；可作为东侧或东北侧道路来向候选，不能直接定点。"
    - "盐曲和桥梁构成景观线索，但盐曲本身未由高德关键词检索返回，仍需区位图/现场/测绘复核。"
  entrance_judgment:
    level: candidate
    main_entrance: "强候选：靠近曲登纳桥的北侧/桥头界面，重点参考 CAD-07、CAD-06、CAD-08 一带；仍不能确定具体开口点。"
    secondary_entrance: "候选：面向 G317/650乡道来向的东侧或东北侧道路界面，需补道路交叉口/道路边线控制点后确认。"
    reason: "CAD-07 与高德曲登纳桥高度吻合，可细化桥头界面；但高德未返回道路几何，且 CAD-01/CAD-04 为外点，所以不能写成高置信 cad_aligned。"
  s2_use:
    can_bind_to_cad_edges: false
    can_screen_candidate_edges: true
    required_control_points:
      - "G317 与 650乡道交叉口或道路中心线：需要高德点位 ↔ CAD 道路交叉点/道路边线，而不是仅用红线角点。"
      - "曲登纳桥两端或桥头道路边线：用于确认主入口开口是否应贴近 CAD-07 或偏向 CAD-06/CAD-08。"
      - "复核 CAD-01、CAD-04，避免外点影响东西向边界判断。"
    notes:
      - "高德坐标为 GCJ-02，不得直接与未知 CAD 工程坐标叠加。"
      - "当前已有红线角点控制点能支撑 S1 细化候选边，但不足以确认主次入口的精确位置。"
      - "道路/桥梁/入口落边需要补充带 feature_type 和 purpose 的语义控制点。"
      - "若要进入 S3 或方案分区，建议先由用户确认这组候选入口判断是否符合现场实际。"
```

### 周边与交通判断

- 场地位于巴青县拉西镇曲登纳桥附近，属于县城边缘、河谷交通廊道型环境。
- 区位图显示 `G317` 是区域主干到达线索，城镇沿河流与道路带状展开；高德 POI 地址也反复出现 `317国道与650乡道交叉口`，但高德 regeo 没有返回道路/交叉口对象，因此“G317 主干来向”可信，“具体贴哪条红线边”仍未定。
- 高德 POI 只能作为筛选证据，不能直接推导设计功能。本项目当前对设计更有用的外部关系是：`曲登纳桥` 北侧强候选、`G317/650乡道` 道路来向候选、`盐曲` 滨水边界候选。
- 500m 内高德 POI 较少，近场更像道路、桥梁、河流和局部村镇生活界面主导；这对口袋公园有利，空间可以更强调“到达即看见”的入口识别和桥头记忆点。
- 巴青县客运站、巴仓寺、第一小学等 600-820m 外 POI 只能说明区域人流和文化背景，不能作为本地块入口位置依据。

### 现场观察与设计影响

本次只跑了区位图视觉 sidecar，未批量解析 13 张现场照片。基于区位图：

- 红框地块靠近盐曲和跨河桥梁，滨水/桥头视线应成为概念设计的第一类机会。
- 图面显示地块内有少量蓝色屋顶建筑和较大裸露土地，且靠近疑似水利设施或工程场地；需要现场照片或甲方确认其保留、拆除和安全边界。
- 河流、铁路/索巴二线、G317 共同构成线性边界，设计中应关注噪声、安全防护、慢行过街和亲水可达之间的平衡。
- 项目定位为“巴青县旅游打卡点”，可把“曲登纳桥 + 盐曲 + 高原河谷 + 巴青地方文化”作为汇报叙事骨架。
- 因桥梁点已和 CAD-07 基本对应，后续总平面上应优先测试“桥头可视入口/打卡节点”与“沿河慢行界面”的关系，而不是从商业 POI 清单推功能。

### 低置信与待复核

- `site.coords` 暂不写入 YAML frontmatter：当前坐标为高德 GCJ-02，而 schema 约定 `site.coords` 为 WGS84。
- 高德没有直接返回道路对象，`G317` 需要用地图底图、道路中心线或现场复核确认具体贴边关系。
- “650乡道”来自高德 POI 地址文本，需人工复核是否为场地实际相邻道路。
- `盐曲` 和 `索巴二线/铁路`主要来自区位图视觉 sidecar，需要地图/现场/测绘复核。
- 主入口可以缩小到“曲登纳桥附近北侧/桥头界面强候选”，但仍不能写成确定开口点。
- 次入口仍只能是道路来向或滨水慢行联系候选，需补充道路交叉点/道路边线控制点。

### 对 S2 和后续阶段的交付

- 给 S2：当前红线角点控制点已经足以支持“桥头/北侧界面强候选”的合成判断；若要进一步确认主次入口，下一组控制点应优先选道路交叉口、道路边线、桥头两端，并在 UI 中标注 `feature_type` 与 `purpose`，而不是继续只选红线角点。
- 给下一步：暂不进入 S3。应先把 S1 的道路/入口候选结论在 UI 或 record 中让用户复核：北侧桥头是否确实是主要可达界面，G317/650乡道是否实际贴近东侧或东北侧。
- 给汇报：区位关键词可写为“G317 河谷通道、盐曲滨水、曲登纳桥节点、县城边缘口袋公园、巴青地方文化打卡点”。
<!-- END:s1_site_analysis -->

<!-- BEGIN:s2_dwg_parse -->
## S2 DWG 与地形解析结果

### S2 输入文件与工具链结果

| 文件 | SHA1 | 处理结果 | 说明 |
|------|------|----------|------|
| `02_site/地形图/口袋公园.dwg` | `adfe6e63cffc269159735f19ede142b49d7fc925` | ODA 转 DXF 成功，`ezdxf` 解析成功 | 主地形图 |
| `02_site/地形图/口袋公园_t8.dwg` | `a51e1bb62ceac321717b4ddff5c0ee6a9941fcef` | ODA 转 DXF 成功，`ezdxf` 解析成功 | 与主地形图解析出的几何统计一致，可作为同源/导出版对照 |
| `02_site/地形图/口袋公园_t8.dwl` / `.dwl2` | 已登记 | 不作为设计资料解析 | CAD 锁文件，仅记录存在 |

机器报告：`05_output/dwg_probe.json`
转换产物：`05_output/cad/02_site/地形图/口袋公园.dxf`、`05_output/cad/02_site/地形图/口袋公园_t8.dxf`
CAD 预览：`05_output/cad/site_preview.svg`
CAD 控制点候选：`05_output/cad/control_point_candidates.json`，当前生成 `CAD-01` - `CAD-09` 共 9 个候选，其中 `CAD-01` - `CAD-06` 为红线定位点，`CAD-07` - `CAD-09` 为视觉模型建议的道路/水系语义控制点。
CAD/高德配准检查：`05_output/amap/cad_alignment_report.json`

```yaml
s2_site_geometry:
  selected_redline:
    source_file: "02_site/地形图/口袋公园.dwg"
    handle: "1306"
    layer: "0"
    confidence: medium
    reason: "29 点闭合多段线，面积、外包框和形态更接近实际用地红线；但图中文字未能脚本绑定到该 handle。"
  boundary_assets:
    cad_preview_svg: "05_output/cad/site_preview.svg"
    control_point_candidate_file: "05_output/cad/control_point_candidates.json"
    converted_dxf:
      - "05_output/cad/02_site/地形图/口袋公园.dxf"
      - "05_output/cad/02_site/地形图/口袋公园_t8.dxf"
    geojson: null
  geometry_metrics:
    area_sqm: null
    assumed_area_for_planning_sqm: 15052.575
    area_raw_units2: 15052.575
    perimeter_raw_units: 509.750
    bbox_raw_units:
      width: 194.212
      height: 130.056
    shape_class: "异形多边形"
    dimension_notes:
      - "$INSUNITS = 0，DWG 未显式声明单位；若图纸单位为米，候选用地面积约 1.505ha。"
      - "本阶段不把候选面积写入 frontmatter 的 site.area_sqm。"
  elevation_summary:
    has_elevation_diff: true
    confidence: medium
    evidence:
      - "DWG 存在高程/测绘点线索，模型 bbox 出现 Z 值到 4122.248。"
      - "GCD、DMTZ、GXYZ 等图层需测绘图例复核后才能提取坡向和最大高差。"
  cad_map_registration:
    state: control_points_needed
    consumed_s1_registration_state: map_located
    alignment_quality: aligned_partial
    control_points_file: "05_output/amap/control_points.json"
    alignment_report: "05_output/amap/cad_alignment_report.json"
    point_count: 8
    all_points_fit:
      rms_error_m: 6.17
      max_error_m: 8.64
    best_fit:
      inliers: ["CAD-02", "CAD-03", "CAD-05", "CAD-06", "CAD-08", "CAD-07"]
      outliers: ["CAD-01", "CAD-04"]
      rms_error_m: 2.89
      max_inlier_error_m: 4.55
    usage_boundary:
      - "可用于粗配准、方向关系和方案分区推敲。"
      - "暂不写成高置信 cad_aligned，不把入口、道路或水系精确落到某条红线边。"
  s1_s2_composite:
    roads_by_edge: []
    water_or_landscape_by_edge: []
    entrance_by_edge: []
    limitations:
      - "CAD-01、CAD-04 相对最佳内点模型偏差偏大，作为低置信参考点保留。"
      - "缺测绘坐标系说明，不能直接输出 WGS84 红线点。"
```

### 可确定几何事实

| 项目 | 结果 | 来源 |
|------|------|------|
| CAD 工具链 | `ezdxf` 已安装；ODA File Converter 已安装并可被脚本检测 | `dwg_probe.py` |
| DXF 版本 | `AC1032` | DWG 转 DXF 后解析 |
| 单位声明 | `$INSUNITS = 0`，即图纸未显式声明单位 | DXF header |
| 模型空间范围 | X `597218.195` - `598007.723`，Y `3534031.994` - `3534587.543` | `dwg_probe.py` bbox |
| 实体统计 | `INSERT 1476`、`LINE 252`、`LWPOLYLINE 92`、`POLYLINE 5`、`TEXT 48`、`HATCH 6`、`CIRCLE 1` | `dwg_probe.py` |
| 主要图层 | `GCD`、`TK`、`GXYZ`、`JMD`、`DLSS`、`DMTZ`、`ASSIST`、`DLDW`、`SXSS`、`ZJ` | `dwg_probe.py` |
| 图中文字 | 存在 `口袋公园用地红线`、`北`、比例尺和坐标网格文字 | `dwg_probe.py` text samples |

### 图面语义观察

- `TK` 图层上有 3 个四点闭合多段线，面积约 `201519` - `212045`（图纸单位平方）。它们外包框接近整张测绘图坐标范围，且形态为规则矩形，判断更像图框/坐标框，不宜作为用地红线。
- `0` 图层上有一个 29 点闭合多段线，handle `1306`，面积 `15052.575`（图纸单位平方），外包框约 `194.212 x 130.056`，周长约 `509.750`。其尺度和形态更像实际用地边界，是当前最可信的红线候选。
- 图中存在 `口袋公园用地红线` 文字，但文字本身位于注记/图例区域，未能通过脚本直接绑定到 handle `1306`。因此该候选面积不能直接当作已确认用地面积。
- `GCD` 图层实体数量最多且处于关闭状态，疑似高程点/测绘点层。模型 bbox 出现 Z 值到 `4122.248`，结合项目位于高原地区，说明 DWG 中存在高程信息或带 Z 的测绘对象；但脚本尚未把高程点语义、等高线和地表坡向可靠分离。

### 面积/边界/高差判断

| 字段 | 当前判断 | 置信度 |
|------|----------|--------|
| `site.area_sqm` | 候选值 `15052.575`，前提是 handle `1306` 为真实用地红线，且图纸单位按米理解 | 中，需要 CAD 人工复核 |
| `site.boundary_shape` | 候选为不规则多边形，非规则矩形；外包框约 `194m x 130m` | 中 |
| `site.has_elevation_diff` | DWG 有高程/测绘点线索，且 S0 现场照片已显示河谷与土方环境；可继续按“存在高差风险”处理 | 中 |
| 坐标系统 | 图纸坐标为工程/投影坐标，未直接得到 WGS84 经纬度 | 低 |

本次按 marker 写入约束，未直接修改 YAML frontmatter；`site.area_sqm` 仍保留待确认状态。S3 可以把 `15052.575㎡` 作为“强排测算暂用值/需复核值”，不得写成最终设计条件。

### 与 S1 的配准判断

- 用户已通过 S2 UI 保存 8 个“CAD 点 ↔ 高德 GCJ-02 点”控制点，文件为 `05_output/amap/control_points.json`。
- `cad_align.py` 最新检查结果为 `aligned_partial`：全点拟合 RMS 约 `6.17m`，最大残差约 `8.64m`。
- 最佳内点为 `CAD-02`、`CAD-03`、`CAD-05`、`CAD-06`、`CAD-08`、`CAD-07`，内点 RMS 约 `2.89m`，最大内点残差约 `4.55m`。
- `CAD-01` 与 `CAD-04` 相对最佳内点模型残差约 `15.73m` / `14.15m`。用户已接受该级别偏差，后续可作为低置信粗配准参考，但不作为高置信落边依据。
- 当前可做“粗配准/方向关系推敲”，但不能写成高置信 `cad_aligned`。主入口、道路、桥梁和水系仍只能作为候选边关系，待复核异常点或补充更明确地物控制点后再落边。

### 阻塞项与待补资料

- 请在 CAD 中点选或隔离 `口袋公园用地红线` 对应对象，确认是否为 handle `1306` 或导出单独红线 DXF。
- 请确认 DWG 单位是否为米；若为米，候选用地面积约 `1.505 ha`。
- 请确认高程点/等高线图层含义，尤其 `GCD`、`DMTZ`、`GXYZ` 的测绘约定；目前只能判断“存在高程数据”，不能直接给出场地最大高差。
- 如需要精确坐标，应提供测绘坐标系说明或红线点坐标表。
- 若要把高德道路/桥梁关系高置信绑定到红线边，请优先复核 `CAD-01`、`CAD-04`，或补充桥头、道路交叉口、硬质边界角点等更明确的控制点；当前控制点已足够支撑粗配准。

### 对 S1 复核和后续阶段的影响

- S1 应先消费当前控制点结果，细化区位、主次干道和出入口候选，不应直接进入 S3 面积策划。
- 当前配准足以把 `曲登纳桥` 与 `CAD-07` 附近北侧界面建立强候选关系；但 G317/650乡道仍缺道路几何，不能高置信绑定到红线边。
- 在道路/入口候选未经用户复核前，不宜输出精确功能分区、工程量、投资估算或最终总平面经济技术指标。
<!-- END:s2_dwg_parse -->

<!-- BEGIN:s3_area_calc -->
_pending: 等 S1/S2 合成判断经用户确认后再进入 S3_
<!-- END:s3_area_calc -->

<!-- BEGIN:s4_questions_summary -->
_pending: 等 S4 写入_
<!-- END:s4_questions_summary -->

<!-- BEGIN:s9_report_outline -->
_pending: 等 S9 写入_
<!-- END:s9_report_outline -->

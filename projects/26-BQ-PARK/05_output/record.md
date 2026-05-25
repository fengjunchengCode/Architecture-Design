---
schema_version: '1.0'
project:
  code: 26-BQ-PARK
  name: 巴青县城西口袋公园建设项目
  client: 巴青县人民政府
  type: park
  scale: 口袋公园
  stage: 方案设计
  updated_at: '2026-05-25T19:31:35+08:00'
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
  filled_required_pct: 78
  ready_for:
  - S3
  - S4
  - S5
  - S9
  blocked:
  - skill: S5
    reason: "软阻塞：可先输出文字版概念强排方向；精细图面强排需等 S3/S4 反馈和入口/滨水语义复核。"
  - skill: S6
    reason: "软阻塞：当前阶段可读取参考 CAD 成图并生成制图任务书；精细 CAD 制图需等 S5 方案方向确认。"
  - skill: S7
    reason: "软阻塞：当前阶段可读取参考 SU/模型截图并生成建模任务书；精细 SU 建模需等 S5/S6 方向确认。"
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

本次 S1 使用以下证据，不直接读取图片原文件：

- 高德上下文：`05_output/amap/s1_map_context.json` 与 `05_output/amap/s1_amap_raw.json`，中心点来自用户输入的高德 GCJ-02 坐标 `94.032582,31.92547`。
- 区位图视觉 sidecar：`05_output/vision/02_site__区位图__中.png.vision.json`、`大.png.vision.json`、`小.png.vision.json`。
- S2 CAD 派生文件：`05_output/cad/control_point_candidates.json`、`05_output/cad/site_preview.svg`。
- S2 当前控制点与配准报告：`05_output/amap/control_points.json`、`05_output/amap/cad_alignment_report.json`。
- S2 历史迁移诊断：`05_output/amap/migration_report_2026-05-24.json`、`05_output/amap/migration_report_2026-05-25.json`。

高德逆地理编码将中心点定位到“西藏自治区那曲市巴青县拉西镇曲登纳桥”，中心点来源为用户输入的高德坐标，定位置信度为 high。高德本次未直接返回 `roads` 或 `road_intersections` 对象；道路线索主要来自高德 POI 地址文本、区位图 sidecar 与 S2 当前 9 点控制点的互证。

重要修正：此前 S1 曾把旧编号 `CAD-07` 写成“曲登纳桥附近强证据”。旧控制点已归档，旧 `CAD-07` 与当前候选点语义错位；本阶段撤回“CAD-07 = 曲登纳桥”“主入口在 CAD-07 所在桥头侧已基本确定”等叙述。当前新 `CAD-07` 是 `water_edge / 盐曲` 的概念阶段语义锚点，不能等同曲登纳桥桥头点。

### 配准状态

```yaml
s1_external_context:
  registration_state: map_located
  registration_detail: partial_alignment_with_semantic_inliers
  cad_alignment:
    note: "本字段为 s2_dwg_parse.cad_map_registration 的引用复述，详细字段以 S2 marker 为准。"
    state: control_points_needed
    state_detail: aligned_partial_with_semantic_inliers
    quality: aligned_partial
    candidate_set_id_current: "sha256:b4512aa3991f8ad3"
    candidate_set_id_at_save: "sha256:b4512aa3991f8ad3"
    control_points_file: "05_output/amap/control_points.json"
    alignment_report: "05_output/amap/cad_alignment_report.json"
    semantic_binding: candidate_only
    semantic_anchors:
      road:
        label: CAD-08
        feature_name: G317
        residual_m: 0.87
        confidence: medium
        note: "road_edge / road_binding 内点，可作为 G317 北侧道路界面候选证据。"
      water:
        label: CAD-07
        feature_name: 盐曲
        residual_m: 1.85
        confidence: medium
        note: "water_edge / water_binding 内点，可作为盐曲滨水界面候选证据。"
    control_points_needing_recheck:
      - label: CAD-03
        reason: "redline_corner 外点，best_fit residual 约 7.95m。"
        action: "后续重选或删除，不用于入口/滨水落边。"
      - label: CAD-06
        reason: "redline_corner 外点，best_fit residual 约 10.87m。"
        action: "后续重选或删除，不用于北侧道路落边。"
      - label: CAD-09
        reason: "road_edge / G317 外点，best_fit residual 约 8.68m。"
        action: "不用于道路落边；若要判断 G317 边界，应重选道路边线或交叉口点。"
    reason_for_not_cad_aligned: "当前为 9 点 mixed control points；CAD-07/CAD-08 是有用语义内点，但整体质量仍为 aligned_partial，不能把道路、桥梁、入口高置信绑定到 CAD 红线边。"
  coordinate_evidence:
    address: "西藏自治区那曲市巴青县拉西镇曲登纳桥"
    amap_gcj02: "94.032582,31.925470"
    wgs84_for_record: null
    wgs84_for_record_note: "未写入 site.coords；当前坐标为高德 GCJ-02，schema 中 site.coords 需 WGS84 或明确转换来源。"
    source: "uploader_ui / user_provided_amap_picker_coordinate / amap_context.py"
    confidence: high
  location_evidence:
    - "AMap reverse geocode: 西藏自治区那曲市巴青县拉西镇曲登纳桥。"
    - "AMap regeo roads=[] and road_intersections=[]; no direct road geometry was returned."
    - "AMap keyword 桥: 曲登纳桥，距中心约 84m；可作为近场地名/桥梁线索，不能单独绑定 CAD 点。"
    - "AMap POI address clue: 棍郭社区居民委员会位于 317国道与650乡道交叉口东南200米，距中心约 125m。"
    - "区位图小范围图识别：红框地块靠近盐曲、G317、索巴二线和跨河桥梁。"
    - "区位图中范围图识别：巴青县城沿河谷、G317 和城镇道路带状展开。"
  amap_context:
    roads:
      - "G317：区位图识别 + 高德 POI 地址出现 317国道；高德 regeo 未返回道路对象。"
      - "650乡道：高德 POI 地址线索为 317国道与650乡道交叉口附近；需地图或现场复核。"
    water:
      - "盐曲（区位图识别）"
      - "曲登纳桥（高德逆地理/关键词检索线索；尚未可靠绑定到当前 CAD 候选点）"
    poi_500m:
      design_relevant_candidates:
        - "曲登纳桥约 84m：作为北侧/桥头外部关系候选，需重新控制点拾取后才能落 CAD 边。"
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
    - "近场桥梁/河流界面仍是重要候选，但当前无桥头端点控制点，不能把曲登纳桥写成已确认入口锚点。"
    - "317国道/650乡道交叉口目前来自 POI 地址线索，不是高德道路几何；可作为东侧或东北侧道路来向候选，不能直接定点。"
    - "盐曲和桥梁构成景观线索；新 CAD-07 可作为盐曲滨水界面概念锚点，但仍需现场/测绘复核。"
  entrance_judgment:
    level: candidate
    main_entrance: "工作假设：北侧/东北侧 G317、曲登纳桥来向界面优先作为主入口候选。"
    secondary_entrance: "工作假设：东南侧 G317/650乡道方向或滨水慢行联系可作为次入口/联系界面候选。"
    confidence: medium
    must_verify_before_construction: true
    withdrawn:
      - "撤回此前“CAD-07 与曲登纳桥高度吻合”的表述；当前 CAD-07 是盐曲水系语义锚点，不是桥头端点。"
      - "撤回此前“桥头/北侧界面可作为主入口强候选带”的高置信表达，降级为概念阶段候选方向。"
    reason: "S1 的高德/区位图证据支持 G317、曲登纳桥、盐曲作为外部关系；S2 中 CAD-07/CAD-08 为有用语义内点，但整体配准仍为 aligned_partial，不能精确落边。"
  working_hypotheses:
    - hypothesis: "北侧/东北侧 G317 来向应作为主要展示和到达界面。"
      confidence: medium
      evidence:
        - "区位图识别 G317 为区域主到达线。"
        - "CAD-08 为 road_edge / G317 内点，best_fit residual 约 0.87m。"
      must_verify_before_construction: true
    - hypothesis: "南侧/东南侧盐曲界面可作为滨水景观和文化打卡叙事界面。"
      confidence: medium
      evidence:
        - "区位图识别红框靠近盐曲与跨河设施。"
        - "CAD-07 为 water_edge / 盐曲内点，best_fit residual 约 1.85m。"
      must_verify_before_construction: true
    - hypothesis: "曲登纳桥附近可作为入口识别和游线起点的叙事线索。"
      confidence: low
      evidence:
        - "高德逆地理与关键词线索定位到曲登纳桥。"
        - "当前尚无 bridge_endpoint 或 bridge_center 控制点。"
      must_verify_before_construction: true
  s2_use:
    can_bind_to_cad_edges: false
    can_consume_for_concept_design: true
    required_control_points_for_precise_binding:
      - "G317 与 650乡道交叉口或道路中心线：需要高德点位 ↔ CAD 道路交叉点/道路边线，而不是仅用红线角点。"
      - "曲登纳桥两端或桥头道路边线：用于确认主入口候选界面是否贴近当前 CAD-06、CAD-08、CAD-09 或其他道路/水系候选点。"
      - "水系岸线或桥端固定地物：用于确认盐曲与红线边界的真实关系。"
      - "重选或删除 CAD-03、CAD-06、CAD-09 等外点。"
    limitations:
      - "当前 9 点配准为 aligned_partial，不是施工级精确叠合。"
      - "高德坐标为 GCJ-02，不得直接与未知 CAD 工程坐标叠加。"
      - "道路/桥梁/入口落边需要补充带 feature_type 和 purpose 的语义控制点，或在后续 P1 内嵌高德地图中重新拾取。"
    usage_boundary:
      - "可用于 S3/S5/S9 的概念阶段工作假设。"
      - "可用于判断道路/滨水界面的候选方向。"
      - "不可用于施工级开口点、精确道路落边、精确水系岸线判定。"
```

### 周边与交通判断

- 场地位于巴青县拉西镇曲登纳桥附近，属于县城边缘、河谷交通廊道型环境。
- 区位图显示 `G317` 是区域主干到达线索，城镇沿河流与道路带状展开；高德 POI 地址也反复出现 `317国道与650乡道交叉口`，但高德 regeo 没有返回道路/交叉口对象，因此“G317 主干来向”可信，“具体贴哪条红线边”仍未定。
- 高德 POI 只能作为筛选证据，不能直接推导设计功能。本项目当前对设计更有用的外部关系是：`G317/650乡道` 道路来向候选、`盐曲` 滨水边界候选、`曲登纳桥` 近场地名/桥梁线索。
- 500m 内高德 POI 较少，近场更像道路、桥梁、河流和局部村镇生活界面主导；这对口袋公园有利，空间可以更强调“到达即看见”的入口识别和桥头记忆点。
- 巴青县客运站、巴仓寺、第一小学等 600-820m 外 POI 只能说明区域人流和文化背景，不能作为本地块入口位置依据。

### 现场观察与设计影响

本次只跑了区位图视觉 sidecar，未批量解析 13 张现场照片。基于区位图与当前控制点：

- 红框地块靠近盐曲和跨河桥梁，滨水/桥头视线应成为概念设计的第一类机会。
- 图面显示地块内有少量蓝色屋顶建筑和较大裸露土地，且靠近疑似水利设施或工程场地；需要现场照片或甲方确认其保留、拆除和安全边界。
- 河流、铁路/索巴二线、G317 共同构成线性边界，设计中应关注噪声、安全防护、慢行过街和亲水可达之间的平衡。
- 项目定位为“巴青县旅游打卡点”，可把“曲登纳桥 + 盐曲 + 高原河谷 + 巴青地方文化”作为汇报叙事骨架。
- 因整体配准仍为 aligned_partial，后续总平面可以先测试“桥头/滨水/道路来向”的概念关系，不应把某个 CAD 编号写成已确认入口点。

### 低置信与待复核

- `site.coords` 暂不写入 YAML frontmatter：当前坐标为高德 GCJ-02，而 schema 约定 `site.coords` 为 WGS84 或需明确转换来源。
- 高德没有直接返回道路对象，`G317` 需要用地图底图、道路中心线或现场复核确认具体贴边关系。
- “650乡道”来自高德 POI 地址文本，需人工复核是否为场地实际相邻道路。
- `盐曲` 和 `索巴二线/铁路` 主要来自区位图视觉 sidecar，需要地图/现场/测绘复核。
- 主入口只能描述为“曲登纳桥/盐曲/G317 来向附近的候选界面”，不能写成确定 CAD 边或确定开口点。
- 次入口仍只能是道路来向或滨水慢行联系候选，需补充道路交叉点/道路边线控制点。

### 对 S2 和后续阶段的交付

- 给 S2：当前 9 点控制点已写入 `candidate_set_id_at_save`，可作为概念阶段粗配准证据；CAD-07/CAD-08 是有用语义内点，CAD-03/CAD-06/CAD-09 需复核。
- 给 S3/S5：允许基于“G317 主到达、盐曲滨水、曲登纳桥节点”的工作假设推进文字版功能策略和概念强排。
- 给 S9：区位关键词可保留为“G317 河谷通道、盐曲滨水、曲登纳桥节点、县城边缘口袋公园、巴青地方文化打卡点”，但入口落点必须标注为待复核。
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
CAD 控制点候选：`05_output/cad/control_point_candidates.json`，当前 `candidate_set_id` 为 `sha256:b4512aa3991f8ad3`，生成 `CAD-01` - `CAD-09` 共 9 个候选，其中 `CAD-01` - `CAD-06` 为红线定位点，`CAD-07` - `CAD-09` 为道路/水系语义候选点。
当前控制点文件：`05_output/amap/control_points.json`，9 点，已写入 `candidate_set_id_at_save: sha256:b4512aa3991f8ad3`。
当前配准报告：`05_output/amap/cad_alignment_report.json`，`status=ok`，`quality=aligned_partial`。
历史迁移诊断：`05_output/amap/migration_report_2026-05-24.json`、`05_output/amap/migration_report_2026-05-25.json`。
旧控制点归档：`05_output/amap/control_points.legacy_2026-05-25_unknown.json`。

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
    candidate_set_id: "sha256:b4512aa3991f8ad3"
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
    state_detail: aligned_partial_with_semantic_inliers
    consumed_s1_registration_state: map_located
    alignment_report: "05_output/amap/cad_alignment_report.json"
    historical_migration_reports:
      - "05_output/amap/migration_report_2026-05-24.json"
      - "05_output/amap/migration_report_2026-05-25.json"
    legacy_control_points_file: "05_output/amap/control_points.legacy_2026-05-25_unknown.json"
    candidate_set_id_current: "sha256:b4512aa3991f8ad3"
    candidate_set_id_at_save: "sha256:b4512aa3991f8ad3"
    control_points_file: "05_output/amap/control_points.json"
    control_points_status: partial_alignment_semantic_mixed
    point_count: 9
    quality: aligned_partial
    best_fit:
      rms_error_m: 2.856
      max_error_m: 4.410
      inlier_labels:
        - CAD-01
        - CAD-02
        - CAD-04
        - CAD-05
        - CAD-07
        - CAD-08
      outlier_labels:
        - CAD-03
        - CAD-06
        - CAD-09
    semantic_anchors:
      road:
        label: CAD-08
        feature_type: road_edge
        feature_name: G317
        purpose: road_binding
        residual_m: 0.87
        confidence: medium
        evidence:
          - "best_fit 内点，残差约 0.87m。"
          - "control_points.json 记录为 road_edge / G317。"
          - "区位图与高德 POI 地址支持 G317 为主要道路来向。"
      water:
        label: CAD-07
        feature_type: water_edge
        feature_name: 盐曲
        purpose: water_binding
        residual_m: 1.85
        confidence: medium
        evidence:
          - "best_fit 内点，残差约 1.85m。"
          - "control_points.json 记录为 water_edge / 盐曲。"
          - "区位图支持场地近盐曲与跨河设施。"
    semantic_binding:
      has_road_intersection_points: false
      has_road_edge_points: true
      has_bridge_endpoint_points: false
      has_water_edge_points: true
      note: "当前存在道路/水系语义候选内点，但整体配准仍为 aligned_partial；可供概念阶段判断，不可作为高置信落边。"
    control_points_needing_recheck:
      - label: CAD-03
        feature_type: redline_corner
        residual_m: 7.95
        action: "重选或删除；不用于入口/滨水落边判断。"
      - label: CAD-06
        feature_type: redline_corner
        residual_m: 10.87
        action: "重选或删除；不用于北侧道路落边判断。"
      - label: CAD-09
        feature_type: road_edge
        feature_name: G317
        residual_m: 8.68
        action: "重选道路边线或交叉口点；当前不用于 G317 落边判断。"
    historical_findings:
      - "旧控制点已归档，不能继续按旧 CAD-07 叙述曲登纳桥关系。"
      - "migration_report_2026-05-24.json 和 migration_report_2026-05-25.json 仅作为审计链。"
    usage_boundary:
      - "可用于 S3/S5/S9 的概念阶段工作假设。"
      - "可用于判断 G317 主到达方向和盐曲滨水界面的候选方向。"
      - "不可用于施工级精确开口点、精确道路落边、精确水系岸线判定。"
      - "若要升为高置信落边，应删除或重选外点，并补充桥头、道路交叉口、道路边线、水系岸线等语义控制点。"
    working_hypotheses:
      - hypothesis: "CAD-08 所在北侧/东北侧道路界面可作为 G317 主到达展示界面。"
        confidence: medium
        evidence:
          - "CAD-08 为 road_edge / G317 内点，残差约 0.87m。"
          - "S1 高德与区位图均支持 G317 为主到达线索。"
        must_verify_before_construction: true
      - hypothesis: "CAD-07 所在南侧/东南侧水系界面可作为盐曲滨水景观界面。"
        confidence: medium
        evidence:
          - "CAD-07 为 water_edge / 盐曲 内点，残差约 1.85m。"
          - "区位图显示红框场地近盐曲与跨河设施。"
        must_verify_before_construction: true
      - hypothesis: "曲登纳桥可作为汇报叙事和入口识别线索，但尚不能落到具体 CAD 点。"
        confidence: low
        evidence:
          - "S1 高德定位与关键词检索支持曲登纳桥地名线索。"
          - "当前没有 bridge_endpoint 或 bridge_center 控制点。"
        must_verify_before_construction: true
  s1_s2_composite:
    roads_by_edge:
      - edge_or_zone: "北侧/东北侧道路界面候选"
        related_feature: "G317"
        evidence: "CAD-08 road_edge / G317 内点 + S1 区位图/高德线索"
        confidence: medium
        limitation: "不是施工级道路红线落边。"
    water_or_landscape_by_edge:
      - edge_or_zone: "南侧/东南侧滨水界面候选"
        related_feature: "盐曲"
        evidence: "CAD-07 water_edge / 盐曲 内点 + 区位图滨水线索"
        confidence: medium
        limitation: "不是精确水系岸线判定。"
    entrance_by_edge: []
    limitations:
      - "缺测绘坐标系说明，不能直接输出 WGS84 红线点。"
      - "现阶段不能确认 G317/650乡道 对应哪条红线边、次入口具体位置、道路边界与红线开口点。"
      - "现阶段不能把曲登纳桥落到具体 CAD 桥头端点。"
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
- 当前 9 点控制点包含道路/水系语义候选：`CAD-07` 可作为盐曲滨水候选锚点，`CAD-08` 可作为 G317 道路界面候选锚点；但 `CAD-09` 是道路外点，不能用于道路落边。

### 面积/边界/高差判断

| 字段 | 当前判断 | 置信度 |
|------|----------|--------|
| `site.area_sqm` | 候选值 `15052.575`，前提是 handle `1306` 为真实用地红线，且图纸单位按米理解 | 中，需要 CAD 人工复核 |
| `site.boundary_shape` | 候选为不规则多边形，非规则矩形；外包框约 `194m x 130m` | 中 |
| `site.has_elevation_diff` | DWG 有高程/测绘点线索，且 S0 现场照片已显示河谷与土方环境；可继续按“存在高差风险”处理 | 中 |
| 坐标系统 | 图纸坐标为工程/投影坐标，未直接得到 WGS84 经纬度 | 低 |

本次按 marker 写入约束，未直接修改 YAML frontmatter；`site.area_sqm` 仍保留待确认状态。S3 可以把 `15052.575㎡` 作为“强排测算暂用值/需复核值”，不得写成最终设计条件。

### 与 S1 的配准判断

- 当前 `05_output/amap/control_points.json` 已写入 `candidate_set_id_at_save: sha256:b4512aa3991f8ad3`，不再是 stale。
- `cad_align.py` 输出 `status=ok`、`quality=aligned_partial`，9 点中 6 个内点、3 个外点；可作为概念阶段粗配准，不可作为施工级落边。
- `CAD-08 road_edge / G317` 是有用道路语义内点，可支持“北侧/东北侧道路展示和主到达界面”的工作假设。
- `CAD-07 water_edge / 盐曲` 是有用水系语义内点，可支持“南侧/东南侧滨水景观界面”的工作假设。
- `CAD-03`、`CAD-06`、`CAD-09` 是当前外点，应在进入施工级精确落边前重选或删除。
- 当前不能确认 `G317/650乡道` 对应哪条红线边、次入口具体位置、道路边界与红线开口点。需要道路交叉口、道路边线、桥头两端、水系岸线等语义控制点。

### 阻塞项与待补资料

- 请在 CAD 中点选或隔离 `口袋公园用地红线` 对应对象，确认是否为 handle `1306` 或导出单独红线 DXF。
- 请确认 DWG 单位是否为米；若为米，候选用地面积约 `1.505 ha`。
- 请确认高程点/等高线图层含义，尤其 `GCD`、`DMTZ`、`GXYZ` 的测绘约定；目前只能判断“存在高程数据”，不能直接给出场地最大高差。
- 如需要精确坐标，应提供测绘坐标系说明或红线点坐标表。
- 若要把高德道路/桥梁关系高置信绑定到红线边，请优先补充桥头、道路交叉口、道路边线、水系岸线等更明确的语义点，并重选或删除 CAD-03/CAD-06/CAD-09。

### 对 S1 复核和后续阶段的影响

- S1 应撤回旧 `CAD-07 = 曲登纳桥` 的确定性叙述，只保留曲登纳桥/G317/盐曲作为外部候选关系。
- 当前配准足以支持轻量 S3、文字版 S5 和 S9 骨架推进，但所有入口、道路、滨水落边必须标注为工作假设。
- S3 可以把 `15052.575㎡` 作为“强排测算暂用值/需复核值”，不得写成最终设计条件。
<!-- END:s2_dwg_parse -->

<!-- BEGIN:s3_area_calc -->
## S3 面积需求与强排初判

### S3a 面积需求测算

任务书提取自 `01_briefing/2026-04-22巴青县城西口袋公园建设项目.docx`：在地形图内用地红线范围新建口袋公园，业主无特殊功能要求，建设内容由设计自行考虑；投资无上限，重点突出巴青县本地特色，打造巴青县旅游打卡点；提交成果包括方案、估算、效果图。

| 功能 | 数量 | 单项指标 | 面积 | 来源 | 置信度 |
|------|------|----------|------|------|--------|
| 入口识别与集散空间 | 1-2 处候选 | 服务 G317/曲登纳桥来向的到达与停留 | 待 S5 强排确定 | S1 主到达假设 + 任务书“旅游打卡点” | 中 |
| 巴青地方文化打卡节点 | 1 组主题节点 | 可结合经幡、地方文化符号、观景与拍照停留 | 待 S5 强排确定 | 任务书“突出巴青县本地特色” | 中 |
| 滨水观景与生态缓冲 | 1 条界面候选 | 面向盐曲与跨河设施的景观界面 | 待 S5 强排确定 | S1/S2 CAD-07 盐曲语义内点 | 中 |
| 慢行游线 | 1 条主环线或串联游线 | 串联入口、文化节点、滨水节点、休憩空间 | 待 S5 强排确定 | 口袋公园类型 + S1 外部关系 | 中 |
| 公共活动与日常休憩 | 若干节点 | 兼顾居民日常、游客短停、节庆小活动 | 待 S5 强排确定 | park 类型模板 + 任务书开放性要求 | 中低 |
| 服务与安全设施 | 若干点位 | 导视、照明、座椅、垃圾桶、必要管理/安全边界 | 待 S5 强排确定 | 口袋公园常规配置，需甲方确认 | 中低 |

候选用地面积可暂按 `15052.575㎡` 进行概念阶段比例校核，前提是 CAD handle `1306` 为真实用地红线且图纸单位为米。该数值暂不写入 frontmatter 的 `site.area_sqm`，也不作为最终设计条件。

### 关键约束

- 场地候选红线为异形多边形，外包尺寸约 `194m x 130m`，适合组织一条短环线或“入口 - 文化节点 - 滨水节点”的串联游线。
- DWG 未声明单位，面积、边长、高差都需要测绘/CAD 复核；概念阶段只把 `1.505ha` 当暂用值。
- 场地存在高差和测绘点线索，但最大高差、坡向、挡墙/台地关系尚未可靠提取。
- G317 主到达侧为 medium 置信工作假设；盐曲滨水侧为 medium 置信工作假设；曲登纳桥为 low 到 medium 置信叙事线索。
- 当前控制点为 `aligned_partial`，可用于概念方向判断，不可用于施工级开口点和道路/水系落边。

### S3b 容积率 / 强排初判

本项目为口袋公园，不以容积率作为核心控制指标。现阶段不做建筑量强排，只做景观功能与空间结构的概念初判：

- 方案应优先建立“道路展示面 + 文化打卡核心 + 滨水/桥头记忆点 + 慢行游线”的骨架。
- 若采用约 `1.5ha` 暂用面积，空间容量足以容纳入口广场、主题节点、滨水节点、休憩活动和慢行游线，但具体比例需 S5 强排草案比较。
- 入口与停车/落客关系不应在本阶段写死；应作为 S5 的 2-3 个方案变量。

### 工作假设

```yaml
s3_working_hypotheses:
  - hypothesis: "以 G317/曲登纳桥来向组织主入口识别，并把入口空间作为旅游打卡第一界面。"
    confidence: medium
    evidence:
      - "S1 识别 G317 为区域主到达线索。"
      - "S2 CAD-08 为 G317 road_edge 语义内点。"
    must_verify_before_construction: true
  - hypothesis: "以盐曲界面组织滨水观景或生态缓冲节点，形成与道路展示面不同的安静体验。"
    confidence: medium
    evidence:
      - "S1 区位图识别场地近盐曲。"
      - "S2 CAD-07 为盐曲 water_edge 语义内点。"
    must_verify_before_construction: true
  - hypothesis: "地方文化打卡节点应作为主游线核心，而不是仅作为装饰小品。"
    confidence: medium
    evidence:
      - "任务书唯一明确价值诉求是突出巴青县本地特色、旅游打卡。"
      - "现场照片与 S0 已识别经幡、佛塔、藏文等文化线索。"
    must_verify_before_construction: false
```

### 待确认指标

- 甲方是否希望口袋公园偏“游客打卡展示”还是偏“社区日常活动”。
- 是否需要保留、避让或整合场地内疑似水利设施、既有建筑、施工/土方痕迹。
- 是否存在河道管理范围、防洪退线、道路开口审批、铁路/索巴二线安全退距等刚性约束。
- DWG 单位、红线面积、最大高差和高程点图层含义需测绘复核。

### 对方案阶段的影响

- S5 可以立即生成 2-3 个文字版概念强排方向，不需要等待施工级落边。
- S5 不应直接画精确 CAD 总平；应先比较入口策略、文化节点位置、滨水界面处理和游线组织。
- S9 可以先生成汇报骨架，所有“入口落边、面积、滨水边界、高差处理”均标注为待复核或工作假设。
<!-- END:s3_area_calc -->

<!-- BEGIN:s4_questions_summary -->
## S4 问题清单与低置信字段归并

### 当前阻塞问题

本阶段没有阻塞 S9 骨架推进的硬问题。以下问题会阻塞施工级落边、精确强排或正式 CAD/SU 深化：

| 对象 | 问题 | 类型 | 来源 |
|------|------|------|------|
| 测绘/CAD | 请确认 DWG 单位是否为米，handle `1306` 是否为正式用地红线？ | hard_block_for_construction_phase | S2 |
| 测绘/CAD | 请复核 `CAD-03`、`CAD-06`、`CAD-09` 外点，确认是否应重选或删除。 | hard_block_for_construction_phase | S2 |
| 测绘/CAD | 请提供或确认高程点/等高线图层含义，尤其 `GCD`、`DMTZ`、`GXYZ`。 | hard_block_for_construction_phase | S2 |
| 设计负责人 | 主入口是否优先面向 G317/曲登纳桥来向，还是优先面向滨水/内部游线？ | soft_block | S1/S3 |
| 设计负责人 | 是否需要补充 1-2 个桥头、道路交叉口或水系岸线语义控制点再做精确落边？ | soft_block | S1/S2 |

### 设计推进前建议确认

| 对象 | 问题 | 类型 | 来源 |
|------|------|------|------|
| 甲方 | 本项目更强调游客打卡展示，还是社区居民日常活动？ | soft_block | S3 |
| 甲方 | 是否有必须设置或必须避免的功能，例如儿童活动、健身、停车、管理房、公厕？ | soft_block | S0/S3 |
| 甲方 | “巴青县本地特色”希望偏宗教文化、民俗符号、自然河谷景观，还是综合表达？ | soft_block | S0/S3 |
| 甲方 | 场地内疑似水利设施、既有建筑、施工痕迹是否保留、拆除或避让？ | hard_block_for_construction_phase | S1/S3 |
| 现场/测绘 | 盐曲河道管理范围、防洪控制线、道路开口审批边界是否已有资料？ | hard_block_for_construction_phase | S1/S2 |

### 可后补问题

- 投资预算虽写“无上限”，仍建议在汇报前确认大致建设标准，避免方案尺度失控。`soft_block`
- 提交时间、汇报对象和成果深度尚未明确，可在 S9 正文生成前确认。`soft_block`
- 现场照片可后续批量视觉复核，用于补充材质、现状设施、视线和文化元素。`soft_block`
- 参考 CAD 成图、SU 模型、历史汇报资料可在 S9/S10 增强阶段补充读取。`soft_block`

### 低置信字段复核

- `site.coords`：当前为高德 GCJ-02 中心点，未转换为 WGS84，不写入 frontmatter。
- `site.area_sqm`：候选值 `15052.575㎡` 仅用于概念阶段比例校核，需确认 CAD 单位和红线对象。
- `site.boundary_shape`：候选为异形多边形，需 CAD 人工复核 handle `1306`。
- `entrance_judgment`：主入口、次入口均为候选方向，不是确定开口点。
- `G317 / 650乡道 / 盐曲 / 曲登纳桥`：可用于概念叙事和方向判断，施工级落边需补语义控制点或测绘依据。

### 可直接发送给甲方的话术

> 目前我们已完成资料盘点、区位初判和 CAD 红线候选解析，可以先推进概念方案和汇报骨架。为了后续深化更准确，请协助确认：1）本项目更偏游客打卡还是社区日常活动；2）是否有必须设置的功能或必须避让的设施；3）是否有河道、防洪、道路开口或铁路/道路退距等硬性控制；4）CAD 图纸单位和正式用地红线是否以当前地形图为准。上述问题不影响先出概念方向，但会影响后续 CAD/SU 深化和施工级落位。
<!-- END:s4_questions_summary -->

<!-- BEGIN:s9_report_outline -->
## S9 汇报文档骨架

### 汇报目标

本轮 S9 只生成汇报文档大纲和每节要点，不写完整汇报正文。目标是把当前 S1/S2/S3/S4 的工作假设组织成可继续深化的汇报结构，并为后续 S9 增强 skill 提供读取路径。

### 标准十节大纲

1. **前期分析**
   - 要点：项目名称、建设单位、建设地点、任务书核心诉求、成果要求。
   - 信息源：frontmatter `project`、`brief.summary`、S0、S3 任务书摘要。
   - 配图需求：任务书信息摘要页、资料清单页。

2. **场地认知**
   - 要点：巴青县拉西镇、G317 河谷通道、盐曲滨水、曲登纳桥节点、县城边缘口袋公园。
   - 信息源：S1 `s1_external_context`、S2 `s1_s2_composite`。
   - 配图需求：区位关系示意图、道路/水系/桥梁关系图、现场照片拼贴。

3. **设计理念**
   - 要点：突出巴青县本地特色，形成旅游打卡记忆点；以道路可见性和滨水体验共同组织空间叙事。
   - 信息源：S0 `style_preferences`、S3 working_hypotheses。
   - 配图需求：概念关键词板、地方文化意向图、设计主题图。

4. **规划结构**
   - 要点：道路展示面、文化打卡核心、滨水/生态界面、慢行游线四类结构关系。
   - 信息源：S1 approach_vectors、S2 geometry_metrics、S3 关键约束。
   - 配图需求：概念结构图、主次轴线/游线示意图。

5. **功能分区**
   - 要点：入口识别与集散、地方文化打卡节点、滨水观景与生态缓冲、慢行游线、公共活动与休憩、服务设施。
   - 信息源：S3 功能策略表。
   - 配图需求：概念分区图、功能气泡图。

6. **流线与入口**
   - 要点：主入口优先考虑 G317/曲登纳桥来向界面；次入口或慢行联系可结合滨水/东南侧道路方向，具体开口待复核。
   - 信息源：S1 entrance_judgment、S2 semantic_anchors、S4 问题清单。
   - 配图需求：入口/游线示意图、道路到达关系图。

7. **景观/文化策略**
   - 要点：巴青地方文化、经幡/藏地符号、高原河谷、盐曲滨水、桥头记忆点；避免只做装饰堆砌。
   - 信息源：S0 视觉资产处理、S1/S3 工作假设。
   - 配图需求：文化元素分析图、节点意向拼贴、滨水界面示意图。

8. **专项设计**
   - 要点：竖向与高差、滨水安全、道路噪声与展示面、夜景照明、导视、设施维护；CAD/SU 目前只做任务书占位。
   - 信息源：S2 elevation_summary、S4 hard_block_for_construction_phase。
   - 配图需求：专项清单页、竖向/安全/照明策略示意。

9. **投资估算或实施建议**
   - 要点：任务书写“投资无上限”，但汇报仍应建议按建设标准分级；优先保证入口识别、文化节点、基础铺装照明和安全设施。
   - 信息源：brief、S3 待确认指标、S4 甲方问题。
   - 配图需求：分期或优先级示意图、建设内容清单。

10. **待确认问题**
    - 要点：CAD 单位和红线、面积、高差、道路/河道控制、入口落位、功能偏向、参考 CAD/SU/历史汇报资料。
    - 信息源：S4 全部问题清单。
    - 配图需求：待确认问题表、责任方分组表。

### PPT/文档页码建议

| 页段 | 内容 | 建议页数 |
|------|------|----------|
| 1 | 封面与项目基本信息 | 1 |
| 2-4 | 前期分析与区位场地认知 | 3 |
| 5-6 | 设计理念与规划结构 | 2 |
| 7-9 | 功能分区、流线入口、景观文化策略 | 3 |
| 10-11 | 专项设计与实施建议 | 2 |
| 12 | 待确认问题与下一步 | 1 |

### 配图清单

- 区位关系示意图：表达 G317、盐曲、曲登纳桥、县城边缘关系。
- 场地照片拼贴：展示高原河谷、现状土方、文化元素、道路/桥梁/水系。
- CAD 红线与候选界面示意：只用于概念说明，不作为施工级落边。
- 概念分区图：入口、文化节点、滨水节点、慢行游线、活动休憩。
- 入口/流线示意图：主来向、次来向、游线组织。
- 节点透视参考：文化打卡节点、滨水观景节点、入口广场。

### 仍需补充资料

- `03_references/` 目前仅有 `.gitkeep`，尚未放入历史汇报文档、参考 CAD 成图或 SU 模型截图；后续 S9 增强 skill 需要读取这些资料。
- 若要生成正式 PPTX，应在 S10 阶段读取 S9 正文和 PPT 模板/历史样例；本轮不调用 PPTX 生成工具。
<!-- END:s9_report_outline -->

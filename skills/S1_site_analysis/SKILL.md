---
name: s1-site-analysis
description: 建筑设计工作流 S1 区位与外部关系分析。用于分析项目位置、周边路网、到达方向、500m/1000m 服务范围、现场照片、区位图，以及为 S2 提供地图侧外部语义。只写 record.md 的 s1_site_analysis marker，并更新相关 pending/low_confidence/completeness。
---

# S1 区位与外部关系分析

## 目标

S1 只回答“场地在城市/街区中的外部关系”：位置证据、道路水系、到达方向、人流来源、入口可能性和设计影响。周边 POI 只是证据来源之一，不是 S1 的默认成果。

S1 不负责从 CAD 中确认红线、面积、边长和高差；这些属于 S2。S1 可以读取 S2 已有结论来提升入口判断，但不能替代 S2。

S1 给后续阶段的核心交付只有四类：

- 给 S2：地图侧的道路、水系、桥梁、交叉口、地标等可配准线索，以及建议用户录入的“地图点 ↔ CAD 点”控制点。
- 给 S2：当前配准状态，明确是 `map_located` 还是 `cad_aligned`，避免把中心点误当作 CAD 配准。
- 给 S3：外部来向、人流/车行接近方向、可利用景观/噪声/阻隔/服务界面等会影响功能布局的设计约束。
- 给汇报文本：项目在城市、街区、河谷/道路/桥梁等结构中的位置叙事。

如果一个 POI 不能解释人流来源、服务需求、文化/景观节点、交通换乘或界面冲突，就不要把它写成设计结论；保留在 `s1_map_context.json` 原始证据即可。

## 必读

- `SKILL.md`
- `skills/_shared/record_contract.md`
- `skills/_shared/marker_contract.md`
- `skills/_shared/folder_contract.md`
- `skills/_shared/confidence_contract.md`
- `skills/_shared/output_style.md`
- `_schema/record.schema.md`

## 输入

- `projects/{code}/05_output/record.md`
- `projects/{code}/05_output/inventory.json`（如有）
- `projects/{code}/02_site/区位图/`
- `projects/{code}/02_site/现场照片/`
- S0 的 `s0_parsed` 段
- 可选：S2 的 `s2_dwg_parse` 段、`projects/{code}/05_output/dwg_probe.json`、S2 生成的边界 SVG/GeoJSON

## 门槛与降级

- `02_site/区位图/` 至少 1 张图。
- 至少要有一个定位线索：`site.address`、`site.coords`、高德地图链接/坐标、区位图中可识别的道路/地名/地标。若完全没有定位线索，只在 S1 marker 写阻塞原因，并把“提供地址、地块中心坐标或高德地图位置链接”写入 `pending_questions`。
- 只有一个地址或一个中心点时，S1 可以分析周边和到达方向，但不能把道路/入口精确绑定到 CAD 红线某一边。
- 只有在具备 2-3 个可靠“地图点 ↔ CAD 点”控制点，或 CAD 本身有可靠坐标系时，S1 才能输出精确的主次入口与红线边关系。
- 若控制点全部是 `redline_corner`，S1 只能判断“红线大致套合”和入口候选边；要判断主次干道、道路边界或开口位置，必须有 `road_intersection`、`road_centerline`、`road_edge`、`bridge_endpoint`、`bridge_center` 等语义控制点，且这些点应在高德和 CAD 中代表同一实体。

## 配准状态

S1 只使用以下三个状态，不新增 S1.5 或子阶段：

| 状态 | 含义 | 允许输出 |
|---|---|---|
| `no_location` | 没有可靠地址、坐标或地图定位线索 | 阻塞说明、待补问题 |
| `map_located` | 有地址、中心点、地图链接或可信周边定位 | 周边路网、POI、到达方向、入口候选关系 |
| `cad_aligned` | 已有 2-3 个控制点或可靠 CAD 坐标系 | 道路/水系/入口与 CAD 红线边界的精确对应 |

## 高德 Skill/API 使用

- 高德能力主要属于 S1，用于地理编码、逆地理编码、道路/水系/桥梁/交叉口线索、公交与到达路径检索；周边 POI 只作为筛选后的辅助证据。
- S1 执行前应优先运行确定性工具：

```powershell
python _tools/amap_context.py {code} --write
```

- 若用户已提供高德坐标拾取器结果，使用：

```powershell
python _tools/amap_context.py {code} --location "经度,纬度" --write
```

- 工具读取仓库根目录 `.env` 中的 `AMAP_WEBSERVICE_KEY`，输出 `projects/{code}/05_output/amap/s1_map_context.json` 与 `s1_amap_raw.json`。
- 坐标录入优先通过本地上传 UI 的“空间定位”面板完成；该面板提供高德坐标拾取器链接，并把结果写入标准输出文件。
- 若工具返回 `amap_not_configured`、`no_location_input` 或 `amap_api_error`，不得编造高德道路、POI、水系或到达关系；只能记录阻塞和 pending questions。
- 当只有文字地址或区位图线索时，优先让用户提供高德坐标拾取器结果或地图分享链接：[高德坐标拾取器](https://lbs.amap.com/tools/picker?utm_source=chatgpt.com)。
- 高德坐标通常是 GCJ-02；`site.coords` schema 约定为 WGS84。不能把 GCJ-02 直接写成 WGS84。若不能确认或转换坐标系，只在 S1 marker 记录原始坐标来源，并标低置信或 pending。
- 高德坐标不能直接套到未知 CAD 工程坐标上。一个中心点只能定位周边关系，不能完成旋转、比例和平移配准。

## POI 筛选规则

高德返回的商店、宾馆、餐饮等 POI 不能自动进入 S1 结论。Agent 只能在以下场景引用 POI：

- 交通设施：客运站、公交站、停车场等能说明真实到达方式。
- 公共服务：学校、医院、政府、社区中心等能说明主要服务人群或活动时段。
- 文化/景观节点：寺庙、广场、桥梁、滨水节点等能转化为空间叙事或视线/游线资源。
- 与地块距离和方向明确，且能和区位图、现场照片或 S2 红线边界互相验证。

商业生活类 POI 默认不展示、不写入设计判断；除非它们形成明确街道活力界面或服务缺口。

## 视觉资料读取

图片资料必须先运行：

```powershell
python _tools/vision_route.py {code} --write
```

若视觉模型未配置、API 报错或模型不可用，只读取 `05_output/vision/` 降级 sidecar，不得用当前对话模型、截图或内置图片读取来补读图像语义。

## Agent 职责

1. 读取 `record.md` frontmatter、S0 marker、S1 现有 marker，并检查是否已有 S2 几何结果可引用。
2. 按 `inventory.json` 的 `read_policy` 处理资料，图片走 `vision_route.py`。
3. 建立定位证据链：地址、坐标、地图链接、区位图标注、道路/地名/地标互相验证。
4. 读取 `05_output/amap/s1_map_context.json`；如具备高德能力或用户提供高德链接/坐标，提取周边道路、水系、POI、公交/步行到达和 500m/1000m 关系。
5. 判断 `registration_state`，并说明能做到“周边语义判断”还是“CAD 红线精确绑定”。
6. 输出给 S2 可消费的 `s1_external_context` 摘要。
7. 读取 S2 的 `control_points.json` 时，区分 `feature_type` 和 `purpose`：红线角点用于配准质量判断，道路/桥梁/水系等语义控制点用于主次干道、入口和外部界面判断。
8. 只改写 `s1_site_analysis` marker；只更新 S1 负责的 frontmatter 字段和 pending/low confidence/completeness。

## 输出结构

写入 `s1_site_analysis` marker 内：

````markdown
### S1 输入与定位证据

### 配准状态

```yaml
s1_external_context:
  registration_state: no_location | map_located | cad_aligned
  coordinate_evidence:
    address: null
    amap_gcj02: null
    wgs84_for_record: null
    source: null
    confidence: low | medium | high
  location_evidence: []
  amap_context:
    roads: []
    water: []
    poi_500m: []        # 仅保留与设计判断有关的筛选项；完整 POI 在 s1_map_context.json
    poi_1000m: []       # 仅保留与设计判断有关的筛选项；完整 POI 在 s1_map_context.json
    transit_or_routes: []
  external_features:
    primary_roads: []
    secondary_roads: []
    barriers: []
    landscape_or_culture_nodes: []
  approach_vectors: []
  entrance_judgment:
    level: blocked | candidate | aligned
    main_entrance: null
    secondary_entrance: null
    reason: null
  s2_use:
    can_bind_to_cad_edges: false
    required_control_points: []
    notes: []
```

### 周边与交通判断

### 现场观察与设计影响

### 低置信与待复核

### 对 S2/S3 的交付
````

`s1_external_context` 是 S1 给 S2 的固定交接口。文字分析可以更自然，但这个 YAML 摘要必须保留。

## 禁止

- 不根据区位图目测写确定地块面积。
- 不把高德/地图推断坐标当作正式 WGS84 坐标。
- 不在 `registration_state != cad_aligned` 时声称“主入口位于红线某边”。
- 不把一个 POI 搜索结果直接当作地块红线或场地中心。
- 不跨写 S2/S3/S9 marker。

## 校验

写入后运行：

```powershell
python _tools/validate_record.py {code}
```

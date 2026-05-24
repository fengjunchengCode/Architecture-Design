---
name: s2-dwg-parse
description: 建筑设计工作流 S2 CAD、红线、地形和几何解析。用于解析 DWG/DXF/PDF 红线图、地块面积、边界形状、尺寸、高差、图层语义、控制点候选，并与 S1 外部关系合成底图判断。只写 record.md 的 s2_dwg_parse marker，并谨慎更新 site 几何字段。
---

# S2 CAD 与地形解析

## 目标

S2 只回答“场地自身的几何事实”：红线候选、边界形状、尺寸、高差、图层语义、可绘制边界资产，以及 CAD 与地图配准所需的控制点候选。

S2 可以读取 S1 的 `s1_external_context`，但不替代 S1 做区位/POI/道路检索。没有配准控制点时，S2 只能输出 CAD 几何和语义合成限制，不能精确判断哪条红线边对应哪条城市道路。

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
- `projects/{code}/05_output/inventory.json`
- `projects/{code}/02_site/地形图/`
- 可选：S1 的 `s1_site_analysis` 段，尤其是 `s1_external_context`
- 可选：`projects/{code}/05_output/amap/control_points.json`，由上传 UI 录入的“地图点 ↔ CAD 点”控制点

## 前置条件

`02_site/地形图/` 中至少有 DWG、DXF、PDF 红线图或可读地形资料。只有 `.dwl` / `.dwl2` 锁文件不算有效输入。

## 确定性工具链

S2 解析 DWG/DXF 时必须先运行：

```powershell
python _tools/dwg_probe.py {code} --json --write
```

该脚本会自动检测 `ezdxf` 与 ODA File Converter。若工具已存在，优先使用 ODA 将 DWG 转为 DXF，再由 `ezdxf` 提取图层、实体统计、闭合多段线候选、文字标注和边界范围等机器事实。若 `ezdxf` 或 ODA 不存在，脚本会返回 `install_guidance`，agent 应按指引安装或配置工具后重跑；手动 CAD 导出 DXF 只作为自动转换失败后的降级方案。

不得裸读 DWG 二进制内容，也不得因为缺少 ODA 就跳过工具检测直接要求用户手动导出。

生成用户可复核的地形图预览与 CAD 控制点候选时，运行：

```powershell
python _tools/cad_preview.py {code} --json --write
```

该脚本读取 `dwg_probe.py` 转出的 DXF，生成：

- `projects/{code}/05_output/cad/site_preview.svg`
- `projects/{code}/05_output/cad/control_point_candidates.json`

这些候选点只是 CAD 侧候选点，不能自动等同于高德地图点。候选点应保持少量、高价值、贴近红线或关键道路/水系地物；不要把边界外的普通建筑角点、固定地物或远离地块的图层采样点默认加入 UI。用户应在上传 UI 的 S2 页面查看 SVG 编号，再到高德坐标拾取器选择对应地图点，保存到 `05_output/amap/control_points.json`。

生成 CAD 预览后，应自动运行视觉语义建议：

```powershell
python _tools/cad_semantics.py {code} --json --write
```

该脚本把 CAD 预览渲染成 `05_output/cad/site_preview_for_vision.png`，并在存在区位图/卫星图时合成为 `05_output/cad/cad_site_composite_for_vision.png`：左侧是 CAD 候选点，右侧是 S1 上传的区位/卫星视觉资料。脚本还应读取既有区位图视觉 sidecar 和高德上下文，通过仓库视觉 provider 路由到配置的视觉模型，输出 `05_output/cad/control_point_candidate_semantics.json`。UI 应优先展示模型给出的简短建议，如“红线配准点”“桥头/桥端”“道路边线候选”，让用户只需去高德拾取精确坐标；不应要求用户手动理解和选择完整枚举字段。

若视觉模型未配置或返回错误，脚本必须降级为保守建议，并在 sidecar 中记录原因。agent 不得改用当前对话模型直接看 CAD 预览截图补判断。

用户保存“地图点 ↔ CAD 点”后，运行：

```powershell
python _tools/cad_align.py {code} --json --write
```

该脚本读取 `05_output/amap/control_points.json`，输出 `05_output/amap/cad_alignment_report.json`，用于判断控制点残差、重复点、内点/外点和配准置信度。只有当报告质量足够高时，S2 才能把 `cad_map_registration.state` 写成 `aligned`；若报告为 `aligned_partial` 或存在明显外点，只能作为粗配准证据，不能输出高置信道路/入口落边结论。

控制点必须区分“几何配准点”和“语义控制点”。红线角点能帮助估计 CAD 与高德的平移、旋转和比例，但不能单独证明某条外部道路、桥梁或水系对应哪条红线边。需要判断主次干道、出入口或水岸落边时，控制点应包含通用属性：

```yaml
control_point:
  label: null
  cad_point: { x: null, y: null }
  amap_gcj02: [null, null]
  feature_type: redline_corner | road_intersection | road_centerline | road_edge | bridge_endpoint | bridge_center | water_edge | building_corner | visible_landmark | other
  feature_name: null
  purpose: registration | road_binding | entrance_check | water_binding | reference_only
  confidence: low | medium | high
  note: null
```

其中 `road_intersection`、`road_centerline`、`road_edge`、`bridge_endpoint`、`bridge_center`、`water_edge` 等语义控制点可用于 S1/S2 合成判断；`redline_corner` 主要用于几何配准和红线复核。该结构是跨项目通用的，不得为单个项目写死道路名或桥名。

上传 UI 会读取 `05_output/cad/control_point_candidate_semantics.json`。该 sidecar 只描述 CAD 候选点的地物语义，不要求立即填写高德坐标；当用户再补高德坐标并保存控制点时，同一套语义字段会进入 `05_output/amap/control_points.json`。

## Agent 职责

1. 列出可用地形/红线文件及 hash。
2. 运行并读取 `05_output/dwg_probe.json`，区分脚本确定的几何事实和仍需人工判断的图面语义。
3. 从闭合多段线、图层名称、文字标注和面积/范围关系中筛选红线候选；无法唯一确认时保留候选排序。
4. 保留并输出地块形状、边长/外包框、面积、周长、高差、标高文字、等高线/坡向线索。
5. 生成或引用可复核的边界资产，如 SVG、GeoJSON、DXF 转换结果；不要只写面积。
6. 运行或引用 `cad_preview.py` 给出控制点候选：CAD 坐标、来源图层/handle、SVG 编号、为什么适合让用户去高德地图点选对应位置；若 `05_output/amap/control_points.json` 已存在，则运行 `cad_align.py` 校验这些用户录入的对应点。
7. 读取 S1 的 `registration_state`：
   - 无 S1 或 `no_location`：只输出 CAD 几何。
   - `map_located`：输出“需要控制点才能合成到底图”。
   - `cad_aligned`：可以把 S1 道路/水系/来向绑定到红线边，形成合成底图判断。
8. 可确认时更新 `site.area_sqm`、`site.boundary_shape`、`site.has_elevation_diff` 等字段；不确定则写 pending 或 low confidence。
9. 只改写 `s2_dwg_parse` marker。

## 输出结构

写入 `s2_dwg_parse` marker 内：

````markdown
### S2 输入文件与工具链结果

### 红线候选与边界资产

```yaml
s2_site_geometry:
  selected_redline:
    source_file: null
    handle: null
    layer: null
    confidence: low | medium | high
    reason: null
  boundary_assets:
    svg: null
    cad_preview_svg: null
    geojson: null
    converted_dxf: null
  geometry_metrics:
    area_sqm: null
    area_raw_units2: null
    perimeter_raw_units: null
    bbox_raw_units:
      width: null
      height: null
    shape_class: null
    dimension_notes: []
  elevation_summary:
    has_elevation_diff: null
    evidence: []
  cad_map_registration:
    state: cad_only | control_points_needed | aligned
    consumed_s1_registration_state: null
    control_points: []
    control_point_candidates: []
    control_point_candidate_file: null
    alignment_report: null
  s1_s2_composite:
    roads_by_edge: []
    water_or_landscape_by_edge: []
    entrance_by_edge: []
    limitations: []
```

### 尺寸、高差与图面语义

### 与 S1 的合成判断

### 阻塞项与待补资料

### 对 S3 强排和面积校核的影响
````

`s2_site_geometry` 是 S2 给 S1/S3/S9 的固定交接口。文字分析可以补充，但这个 YAML 摘要必须保留。

## 禁止

- 不从现场照片或区位图估算正式地块面积。
- 不把 DWG 锁文件当成设计资料。
- 不在没有脚本或明确图面标注时输出高精度坐标/面积。
- 不绕过 `dwg_probe.py` 直接读取或猜测 DWG 内容。
- 不在缺少 `cad_aligned` 配准证据时宣称某条 CAD 边界对应某条地图道路。

## 校验

写入后运行：

```powershell
python _tools/validate_record.py {code}
```

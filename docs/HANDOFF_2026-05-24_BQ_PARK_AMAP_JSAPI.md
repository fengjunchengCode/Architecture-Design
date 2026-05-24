# 26-BQ-PARK S1/S2 交接与高德 JSAPI 地图配准方案

状态：待审核
日期：2026-05-24
适用项目：`26-BQ-PARK`，巴青县城西口袋公园建设项目
交接目的：给后续 agent 审核当前 S1/S2 进展，并重点评估是否用高德 JavaScript API v2 替代“外跳坐标拾取器 + 手工复制坐标”的控制点录入方案。

## 1. 当前项目背景

本仓库是面向 agent 的建筑设计工作流。核心真相文件是：

```text
projects/26-BQ-PARK/05_output/record.md
```

其他 JSON、SVG、PNG、DXF 都是派生证据或工具输出。执行规范以 `AGENTS.md`、根 `SKILL.md`、`skills/*/SKILL.md` 和 `_schema/` 为准。

`26-BQ-PARK` 当前资料包括：

- 需求文档：`01_briefing/` 中有 `.doc` 文件，老二进制文档需先转换后语义读取。
- 区位图：`02_site/区位图/` 中有 `大.png`、`中.png`、`小.png`。
- 地形图：`02_site/地形图/` 中有 `口袋公园.dwg`、`口袋公园_t8.dwg` 及 CAD 锁文件。
- 现场照片：`02_site/现场照片/` 中有 13 张 JPG。

已配置并使用：

- 视觉模型 provider：`VISION_PROVIDER=anthropic`，模型为 `mimo-v2.5`。
- 高德 Web Service：`AMAP_WEBSERVICE_KEY` 已配置。
- DWG 工具链：`ezdxf` 与 ODA File Converter 可用，`selfcheck` 已通过。

## 2. 当前阶段进度

S0 已完成基础建档和资料盘点。S1/S2 已进入“地图定位 + CAD 配准”阶段，尚不应进入 S3。

S1 已通过高德 Web Service 生成地图上下文：

```text
projects/26-BQ-PARK/05_output/amap/s1_map_context.json
```

关键定位输入：

```text
地块中心：94.032582,31.925470
高德逆地理编码：西藏自治区那曲市巴青县拉西镇曲登纳桥
附近关键地物：曲登纳桥、G317、650乡道、盐曲、拉西镇、巴仓寺等
```

需要注意：S1 当前已经能定位到项目附近，但高德 POI 列表本身对设计帮助有限。真正有用的是把道路、水系、桥梁和 CAD 红线边绑定起来。

S2 已完成 DWG 转 DXF、CAD 预览、红线候选和候选控制点生成：

```text
projects/26-BQ-PARK/05_output/cad/site_preview.svg
projects/26-BQ-PARK/05_output/cad/control_point_candidates.json
projects/26-BQ-PARK/05_output/cad/site_preview_for_vision.png
projects/26-BQ-PARK/05_output/cad/cad_site_composite_for_vision.png
projects/26-BQ-PARK/05_output/cad/control_point_candidate_semantics.json
```

当前疑似红线：

```yaml
source_dxf: 05_output/cad/02_site/地形图/口袋公园.dxf
handle: "1306"
layer: "0"
vertex_count: 29
area_raw_units2: 15052.5751953125
bbox_raw_units:
  width: 194.21176029730123
  height: 130.05631577596068
confidence: candidate_needs_cad_review
```

## 3. 当前候选点与综合视觉判断

之前候选点太多，现已收敛到 9 个：

- `CAD-01` 至 `CAD-06`：红线定位点。
- `CAD-07`：视觉模型建议为 `盐曲` / 水利设施边线绑定。
- `CAD-08`、`CAD-09`：视觉模型建议为 `G317` / 道路边线绑定。

综合视觉输入不是只看 CAD，而是：

```text
CAD 预览 + 3 张区位/卫星图 + 高德上下文 + 区位图视觉 sidecar
```

综合判断摘要：

- 场地位于巴青县拉西镇附近，盐曲河南岸，G317 南侧。
- CAD 红线与小尺度卫星图中的红框区域基本吻合。
- 场地南侧紧邻盐曲及桥/水利设施，北侧为 G317 与城镇建成区。
- `CAD-07/08/09` 更适合作为语义控制点，但仍需精确地图点复核。

## 4. 当前最大问题

当前 UI 仍依赖用户打开高德坐标拾取器手动点选，然后复制经纬度回 S2 页面。这个方案复核概率高，原因不是用户操作不熟，而是工作流本身要求用户在两个坐标/视觉空间之间做脑内配准。

主要问题：

1. CAD 预览、卫星图和高德地图不在同一交互视图中，用户需要靠记忆和截图判断。
2. 红线角点在真实卫星图上往往没有明确可见地物，手动点红线角点天然容易产生 5-15m 误差。
3. 坐标拾取器只给一个经纬度，不给候选点残差、整体拟合、外点提示和即时反馈。
4. 控制点候选一旦重新生成或编号变化，旧的 `control_points.json` 可能发生标签语义错位。
5. 用户当前更多是在复核“猜测出来的红线角点”，而不是在地图上确认“道路边线、桥头、水系岸线”等更稳定的共同地物。

现有 `control_points.json` 是在候选点重构前录入的，风险尤其高：

- 文件时间：`2026-05-23T17:41:42+0800`
- 点数：8
- 当前 `cad_alignment_report.json` 质量：`aligned_partial`
- 最佳拟合 RMS：约 `2.89m`
- 最佳拟合外点：`CAD-01`、`CAD-04`
- 全量拟合 RMS：约 `6.17m`
- 全量最大误差：约 `8.64m`

更重要的是：旧控制点中的 `CAD-07/CAD-08` 等标签来自旧候选编号。当前候选重构后，`CAD-07` 已变成水利/水系语义点，`CAD-08/09` 变成 G317 道路语义点。因此后续 agent 不应直接信任旧 `control_points.json`，应先做标签和坐标的迁移/废弃策略。

## 5. 高德 JSAPI v2 能否解决

可以显著降低误选概率，但不能自动解决所有配准问题。

高德 JavaScript API v2 官方能力包括：

- JS API v2 概览：https://lbs.amap.com/api/javascript-api-v2/summary
- 准备与 Key 配置：https://lbs.amap.com/api/javascript-api-v2/prerequisites
- JSAPI 加载：https://lbs.amap.com/api/javascript-api-v2/guide/abc/load
- 地图事件绑定：https://lbs.amap.com/api/javascript-api-v2/guide/map/map-bind
- 图层能力：https://lbs.amap.com/api/javascript-api-v2/guide/layers/official-layers
- 自有数据图层，如 CanvasLayer/ImageLayer：https://lbs.amap.com/api/javascript-api-v2/guide/layers/canvaslayer
- Polygon 绘制/编辑：https://lbs.amap.com/api/javascript-api-v2/guide/amap-polygon/polygon

这些能力可支撑一个嵌入式 S2 地图配准页面：

1. 在上传 UI 内直接加载高德地图，不再外跳坐标拾取器。
2. 默认中心使用 `s1_map_context.json` 的 `94.032582,31.925470`。
3. 打开卫星图层和路网图层，让用户直接看真实道路、水系、桥梁。
4. 在地图点击时直接获得 AMap GCJ-02 经纬度，写入当前 CAD 候选点。
5. 录入 2-3 个点后实时调用 `/api/alignment-check` 或 `cad_align.py` 计算残差。
6. 把 transformed CAD 红线/候选点画到高德地图上，让用户拖动或重选外点。

它能降低的问题：

- 减少复制坐标错误。
- 减少在高德拾取器和本地 UI 之间来回切换。
- 用卫星图 + 路网 + CAD overlay 共同辅助判断。
- 实时暴露残差，避免用户保存后才发现复核失败。
- 可以优先引导用户点 `CAD-07/08/09` 这类道路/水系语义点。

它不能直接解决的问题：

- CAD 坐标仍是未知工程坐标，不能直接和 GCJ-02 经纬度叠加。
- 只给一个中心点无法推导旋转、比例和平移。
- 卫星图上看不到真实红线，红线角点仍可能是弱控制点。
- 若 CAD 候选点语义识别错误，地图组件只能帮助发现问题，不能保证自动纠正。

## 6. 推荐 UI 工作流

建议把 S2 页面拆出一个明确的“地图配准/控制点复核”工作区，而不是继续让用户手动粘贴坐标。

### 6.1 初始状态

页面分为三块：

- 左侧：CAD 预览图，显示 `CAD-01` 至 `CAD-09`。
- 右侧：高德地图，默认卫星 + 路网，中心为 S1 的高德坐标。
- 下方：控制点表和实时残差报告。

候选点列表默认排序：

1. 语义控制点：`CAD-07`、`CAD-08`、`CAD-09`。
2. 几何定位点：`CAD-01` 至 `CAD-06`。

用户点击一个候选点后，在右侧地图点击对应真实地物。地图点击直接填入经纬度，不再需要坐标拾取器。

### 6.2 两点后

当用户选择至少 2 个可靠点后：

- 后端用 similarity transform 做粗配准。
- UI 在高德地图上绘制变换后的 CAD 红线 polygon 和候选点 marker。
- 所有 marker 标注残差状态：正常、偏差、外点。

两点只能做粗略平移/旋转/比例判断，UI 应显示“粗配准，不足以高置信判断入口”。

### 6.3 三点及以上

当用户选择 3 个以上点后：

- 后端继续使用 `cad_align.py` 的残差和外点判断。
- UI 显示 RMS、最大误差、内点、外点。
- 用户可拖动地图侧 marker 或重新点击外点。
- 保存前必须明确提示哪些点会写入最终 `control_points.json`。

建议保存策略：

- `draft_control_points.json`：用户正在调试的点。
- `control_points.json`：用户确认后的正式点。
- `cad_alignment_report.json`：正式点对应的配准报告。

## 7. 技术设计建议

### 7.1 配置

新增 `.env` 配置项：

```text
AMAP_JSAPI_KEY=
AMAP_JSAPI_SECURITY_CODE=
```

不要提交真实 key。`.env.example` 可以给占位符。

前端加载高德 JSAPI 前需要注入安全配置。为避免 key 分散，建议新增后端接口：

```text
GET /api/amap-js-config
```

返回：

```json
{
  "configured": true,
  "key": "...",
  "security_code": "...",
  "center": [94.032582, 31.925470]
}
```

这是本地工具 UI，不是公网生产系统；若以后部署到公网，需要重新设计 key 保护方式。

### 7.2 前端

在 `_tools/uploader/static/app.js` 中新增 JSAPI Loader 逻辑。

推荐页面状态：

```js
state.mapMatch = {
  map: null,
  selectedCandidateId: null,
  draftControlPoints: [],
  transformedCad: null,
  alignment: null
}
```

前端职责只做交互：

- 加载地图。
- 显示候选点和地图 marker。
- 监听地图点击/marker 拖拽。
- 调用后端保存和残差检查。

不要把配准算法散在前端；配准仍应走 `_tools/cad_align.py` 或后端 API。

### 7.3 后端

建议新增或扩展接口：

```text
GET  /api/amap-js-config
POST /api/alignment-check
POST /api/control-points/draft
POST /api/control-points/commit
GET  /api/cad-overlay?project=26-BQ-PARK
```

`/api/cad-overlay` 可读取：

```text
control_point_candidates.json
cad_alignment_report.json
dwg_probe.json / cad_preview 输出
```

输出变换后的 GCJ-02 坐标：

```json
{
  "boundary_polygon_gcj02": [[94.0, 31.9], "..."],
  "candidate_markers_gcj02": [],
  "quality": "aligned_partial",
  "residuals": []
}
```

注意：该 overlay 只能作为工作底图，不能作为正式测绘坐标成果。

### 7.4 数据失效与版本

必须解决候选点重生成后的旧控制点失效问题。建议在 `control_point_candidates.json` 写入：

```json
{
  "candidate_set_id": "sha1-of-source-dxf-boundary-and-candidates"
}
```

`control_points.json` 保存同一个 `candidate_set_id`。如果候选点重生成导致 id 不一致，UI 必须提示：

```text
CAD 候选点已更新，旧控制点可能与当前标签不匹配。请重新确认或迁移。
```

这是当前最高优先级的安全阀。

## 8. 建议实施顺序

P0：文档和审核

- 审核本交接文档。
- 决定是否引入高德 JSAPI key。
- 明确旧 `control_points.json` 的处理：废弃、迁移或保留为历史。

P1：最小地图录入

- 新增 `/api/amap-js-config`。
- S2 页面内加载高德地图。
- 点击候选点后，在地图点击写入经纬度。
- 仍使用现有 `/api/alignment-check` 做实时残差。

验收：不再需要外跳高德坐标拾取器。

P2：实时残差和外点 UI

- 每加入/拖动一个点后自动计算残差。
- 外点直接在地图 marker 和控制点列表中高亮。
- 保存按钮靠近残差报告。

验收：用户在保存前能看到 `CAD-01/CAD-04` 这类偏差点。

P3：CAD 红线叠加到高德地图

- 后端把 CAD 红线和候选点按当前 transform 转成 GCJ-02。
- 前端用高德 Polygon/Polyline/Marker 画到地图上。
- 支持地图 marker 拖拽微调。

验收：用户能在卫星图上直观看到 CAD 红线和 G317/盐曲关系。

P4：候选版本与数据安全

- 增加 `candidate_set_id`。
- 旧控制点与新候选不一致时阻止静默复用。
- `draft_control_points.json` 与正式 `control_points.json` 分离。

验收：重生成候选点不会让旧标签误配到新语义点。

## 9. 审核 agent 重点问题

请重点审核：

1. 是否同意用高德 JSAPI v2 内嵌地图替代坐标拾取器。
2. 是否先做“两栏点击配对”，再做 CAD overlay，而不是一开始就做复杂叠图。
3. `candidate_set_id` 是否应作为 P1 前置安全要求。
4. `control_points.json` 当前是否应废弃重录。
5. 是否应优先要求用户点 `CAD-07/08/09`，而不是继续点红线角点。
6. `cad_align.py` 是否需要输出 transformed boundary，供前端直接画 Polygon。
7. `AMAP_JSAPI_SECURITY_CODE` 在本地 UI 中由后端下发是否可接受。

## 10. 当前不要做的事

- 不要直接进入 S3。
- 不要把旧 `control_points.json` 当成高置信配准证据。
- 不要继续让用户靠坐标拾取器逐个复制点作为主方案。
- 不要把高德 GCJ-02 坐标直接写成 CAD 坐标系成果。
- 不要把红线角点匹配误差解释为设计结论。

## 11. 当前可复现命令

```powershell
python _tools/selfcheck.py
python _tools/validate_record.py 26-BQ-PARK
python _tools/cad_preview.py 26-BQ-PARK --json --write
python _tools/cad_semantics.py 26-BQ-PARK --json --write --timeout 90
python _tools/cad_align.py 26-BQ-PARK --json --write
python _tools/uploader/server.py --no-browser --host 127.0.0.1 --port 8765
```

当前 UI：

```text
http://127.0.0.1:8765/?project=26-BQ-PARK&page=s2
```

## 12. 结论

高德 JSAPI 地图组件值得引入。它不是为了“自动配准”，而是把用户从坐标复制器中解放出来，把控制点复核变成同屏、可视、可即时看残差的流程。

当前最大风险不是算法不够复杂，而是控制点录入界面让用户在多个视图之间手动脑补对应关系。先做最小地图点击配对和实时残差，再做 CAD 红线 overlay，是更稳的演进路径。

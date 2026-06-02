# PRD：S2 重构 — 从逐点精配准 → 地块粗对位 + 出入口/周边/朝向(并入 S1)

## Goal
把 S2「地形与配准输入」从**繁琐易失败的逐点控制点配准**,改为**把 CAD 地块红线轮廓半透明叠在 S1 卫星底图上,粗略拖+转对位**,从而为 S3 强排产出三样:**出入口(红线上,含所朝道路)+ 周边道路/用地语义 + 北向角**。CAD 自带北向则优先用。精度不重要(真实尺寸以 CAD 为准),只求"摆正、对上路"。S2 并入 S1 流程。

## Requirements
1. S1 定完中心点、出卫星图后,叠加 **CAD 红线轮廓**(来源:`05_output/cad/redline_candidate_1306.svg/.geojson` 或 `site_preview.svg`)为半透明图层。
2. 图层支持**拖动 + 旋转 +(可选)缩放**——粗对位,**无控制点点对**。若 `redline_candidate_*.geojson` 是可靠地理坐标,**预置摆放**,用户只微调。
3. **朝向**:CAD 有指北针/已知朝向 → 预转到该朝向并作为默认北向;没有 → 从对位旋转角**反推北向角**,保存 `north_deg`。
4. **出入口**:用户在红线边上点出入口;每个出入口**关联所朝道路**(从下面的周边道路列表里**手选**,不要求自动几何判定)。
5. **周边语义**:从 `05_output/amap/s1_map_context.json` 自动取相邻道路/用地等,列出供选择/补注。
6. **产出 artifact**(给 S3 强排,新文件,如 `05_output/site_context/site_context.json`):`{ north_deg, site_polygon_geo(近似), entrances:[{point_on_redline, faces_road}], surroundings:{roads, land_uses, notes} }`;配 schema 校验。
7. **下线旧流程**:S2 UI 去掉控制点候选抽取、逐点点对拾取、控制点 stale 管理、配准质量评分。旧 `control_points.json` 可保留只读兼容,但不再是必经路径。

## Acceptance Criteria
- [ ] S1/S2 卫星图上出现可**拖动+旋转**的 CAD 红线半透明图层;`redline_candidate_*.geojson` 可靠时预置摆放。
- [ ] S2 UI 中**不再有**控制点点对拾取 / 候选抽取 / stale 管理 / 配准评分。
- [ ] CAD 有北向→图层预转到该朝向;无北向→对位旋转角写入 `north_deg`。
- [ ] 可在红线上标 ≥1 个出入口,并从周边道路列表选所朝道路,保存。
- [ ] 周边语义从 `s1_map_context.json` 自动填充,可编辑。
- [ ] 写出 `site_context.json` 且通过 schema 校验;字段含 north_deg / entrances / surroundings。
- [ ] 门禁全绿(py_compile / node --check / api_smoke / browser_smoke);制图工作台与 FZ 行为不受影响。

## Definition of Done
- 上述验收全过;新增 api/browser smoke 覆盖"叠加+拖转""出入口标注+保存""artifact 写出+校验";旧配准断言相应调整/移除。
- `docs/` 更新 S2 新流程说明;`.env`/依赖无新增(若需先说明)。

## Technical Approach
- 复用 S1 已有卫星底图与坐标工具(`gcj02_to_wgs84`、`_wgs84_to_tile`、瓦片 zoom/mpp,server.py)。
- 叠加层变换 = **相似变换**(平移+旋转+等比缩放),由用户最终摆放推导;不解点对最小二乘。
- 出入口"所朝道路"= 用户从周边道路列表手选(MVP 不做自动几何判定,降复杂度)。
- 先核实 `redline_candidate_1306.geojson` 是否真为可靠地理坐标:可靠→预置摆放、对位近乎免操作;不可靠→纯手动粗对位。

## Decision (ADR-lite)
- **Context**:旧 S2 逐点精配准繁琐易失败,且其精配准变换下游消费很弱(S1 区位走中心点、分析图用渲染 CAD 垫底、真实尺寸以 CAD 为准)——投入产出失衡。
- **Decision**:S2 砍成"粗对位拿 出入口+周边语义+北向",并入 S1;放弃米制精度。
- **Consequences**:失去 S2 的米制精配准(可接受,CAD 权威);换来极简 UX + 真正被 S3 消费的产物。未来若需精配准可另起。

## Out of Scope
- 精地理配准 / 米制尺度(CAD 为准)。
- 用卫星图当各类分析图底图(分析图用渲染好的 CAD 效果图)。
- S3 强排本身消费 `site_context.json` 的逻辑(本任务只产出该 artifact)。
- 从卫星自动识别地块边界。

## Technical Notes
- 现有产物:`05_output/cad/{redline_candidate_1306.geojson,redline_candidate_1306.svg,site_preview.svg,control_point_candidates.json}`;`05_output/amap/{s1_map_context.json,control_points.json,cad_alignment_report.json}`。
- 前端 S2 在 `_tools/uploader/static/app.js`(controlPoints/几何配准/`/api/spatial`);后端路由 `handle_spatial`、`handle_control_points*`(server.py)。
- 红线见 `.trellis/spec/guides/project-conventions.md`(单线程每条一提交、门禁驱动行为、不提交 05_output 产物)。

# S2 道路/水体语义方案调研与当前图测试

日期：2026-06-02

## 结论

本批 S2 采用“矢量优先、CV sidecar 只做研究/辅助”的路径。

- OSM/Overpass 能提供道路与水体的可审计 geometry，适合直接叠到卫星图上做主/次/支路、水体和候选入口。
- 高德 regeo/POI 适合补充中文地名、G317/国道等道路名称线索，但通常不给完整线几何；当只有 POI location 时只能生成低置信近似线。
- 轻量 CV baseline 不引入新依赖，只能做颜色/亮度启发式，当前图能标出部分水体和亮色道路，但不能稳定识别道路/水体边界，不应作为生产路径。
- SAMGeo/Segment Anything 等成熟 CV 项目可作为隔离 sidecar 继续研究，但不进入主依赖；若后续要启用，必须单独环境、单独门禁、输出 sidecar，不写入主 requirements。

## 依据

- OSM Overpass API 是面向 OSM 数据的只读查询 API；Overpass QL 的 `out geom` 可返回对象 geometry。
  - https://wiki.openstreetmap.org/wiki/Overpass_API
  - https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL
- OSM 道路和水体有稳定标签体系：道路主要看 `highway=*`，水体/河道看 `waterway=*`、`natural=water`、`water=*`。
  - https://wiki.openstreetmap.org/wiki/Map_features
  - https://wiki.openstreetmap.org/wiki/Key:waterway
  - https://wiki.openstreetmap.org/wiki/Waterways
- SAMGeo 是成熟的 geospatial SAM 包，但会引入模型、PyTorch/GPU/地理栅格相关复杂度，本批不进入主工程依赖。
  - https://github.com/opengeos/segment-geospatial

## 已落地

1. `_tools/amap_context.py` 增加 OSM/Overpass 查询：
   - 默认写入 `map_context.osm_context`。
   - 查询失败只记录 `status/error`，不阻断高德 context。
   - 只使用标准库，不新增依赖。
2. `_tools/uploader/server.py` 增强 S2 语义抽取：
   - OSM road/water feature 转为 `surroundings.roads` / `surroundings.water_features`。
   - 道路字段包含 `name/ref/level/source/confidence/geometry`。
   - `Gxxx` / `国道` 识别为 `primary`。
   - 高德 POI 地址中的道路名可生成低置信近似线，避免“有 G317 文本但无可视化线”。
3. S2 前端：
   - 卫星底图上绘制主干道、次干道、支路、水体/河道、候选入口。
   - 已保存 site context 会与最新 S1 语义 geometry 合并，旧保存不会遮蔽新矢量。
4. S1 区位分析：
   - `sync_location_analysis_drawing` 会从同一语义层生成 `location_road_line` 和 `location_water_area` 候选对象。

## 当前图测试

测试项目：`26-BQ-PARK`

截图与报告：

- `.trellis/workspace/codex-current/s2_osm_amap_vector_overlay.png`
- `.trellis/workspace/codex-current/s2_cv_sidecar_baseline.png`
- `.trellis/workspace/codex-current/ppt_preview_aspect.png`
- `.trellis/workspace/codex-current/s2_visual_assertions.json`

当前 S2 DOM/视觉断言：

- `primary_roads`: 4
- `secondary_roads`: 7
- `local_roads`: 23
- `water_overlays`: 2
- `candidate_entrances`: 4
- `basemap_visible`: 1
- `status`: 天地图卫星底图已加载

CV baseline：

- 仅使用 Pillow，未引入 OpenCV/SAM/GDAL。
- `water_like_pixels`: 15479
- `road_like_pixels`: 38896
- 结论：可作为“需要人工注意”的研究叠层，不能替代 OSM/高德矢量。

## 风险与后续

- Overpass 社区 endpoint 可能超时；已支持 `--overpass-endpoint` 和 `--skip-osm`。生产使用应保留失败降级。
- OSM 偏远地区道路可能无中文名或缺 `ref`；当前用 OSM id 保留 geometry，并用高德 POI/地址补中文道路名线索。
- 高德 POI location 近似线只用于视觉候选和入口候选，不应被当成精确道路中心线。
- 若用户确认需要 CV，建议单独建立 sidecar：输入当前卫星图，输出 GeoJSON/PNG mask/report；主工程只消费 sidecar 结果，不安装重依赖。

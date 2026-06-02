# S2 语义增强与 PPT 预览比例修复

## 背景

用户反馈 2026-06-02：

1. 已配置天地图 key，S1 界面可以成功加载卫星地图，但 S2 提示“天地图卫星底图暂不可用”。
2. S2 编辑 CAD 红线后无法 `Ctrl+Z` 撤销；希望把撤销/重做这类制图标准动作加入项目规约，后续本项目任何制图开发都遵守。
3. S2 候选出入口和主次道路不明确，只写了“支路”，地块旁 G317 等明显主路未进入主次干道分析。希望阶段能在卫星图中明确显示主次干道与出入口，并足够准确。S1 区位分析草稿也存在道路、水体识别失败和制图效果差的问题。需要先调研成熟卫星地图道路/水体识别方案，并提交完整实施方案供确认。
4. PPT 预览遗留问题：所有分析图点击 PPT 预览后，全局图纸框中发生比例畸变，和原图纸长宽比例不一致。

## 目标

- 先诊断四个问题，形成可执行分阶段方案。
- 第 3 项道路/水体/出入口识别方案需先获得用户确认，再进入实现。
- 后续实现必须遵守 `.trellis/spec/guides/project-conventions.md`：
  - 单线程顺序；
  - 门禁驱动，先写会失败的行为断言；
  - FZ 分区逐像素回归；
  - 不提交 `05_output` 运行产物；
  - 不擅自新增依赖，尤其重型 CV/GIS 依赖需先说明。

## 初步验收方向

- S2 天地图卫星底图可用时不再误报不可用；不可用时给出明确可诊断原因。
- S2 CAD 红线、出入口、北向角、道路/水体语义编辑至少支持 `Ctrl/Cmd+Z` 撤销与 `Ctrl/Cmd+Y` 或 `Ctrl/Cmd+Shift+Z` 重做。
- 项目规约新增“制图交互标准动作”条款。
- S2 卫星图上明确展示主次干道、出入口候选及其来源/置信度，并可人工校正。
- S1 区位分析草稿复用同一语义层，减少道路/水体识别失败。
- PPT 预览与导出的图纸框保持原图纸比例，不拉伸畸变。

## 待确认

- 道路/水体/出入口识别采用“矢量数据优先 + 人工校正”的轻量路线，还是引入重型卫星影像 CV 分割管线。

## 2026-06-02 诊断摘记

- S1 天地图与 S2 天地图不是同一加载链路：
  - S1 使用浏览器端 `AMap.TileLayer` 直接加载天地图瓦片。
  - S2 使用服务端 `/api/s2/basemap` 调 `_fetch_tdt_tile()` 拼接快照，依赖服务端 `.env`、Pillow、网络访问和当前运行的 server 代码版本。
  - 因此“S1 可见但 S2 不可用”可能来自旧 server 进程、服务端瓦片请求失败、或接口误报，不等同于 key 一定没配。
- S2 主应用页没有 undo/redo 历史栈；制图 workbench 已有 per drawing type undo/redo 栈和快捷键。应把该能力上升到项目制图交互规约。
- S2 周边道路当前主要来自 `s1_map_context.json` 中高德逆地理 `regeo.roads`、S1 seed、关键词 POI 文本匹配。候选入口只是按道路列表顺序贴到红线边，没有几何上的“路-红线最近边”判断。
- 本地 `projects/26-BQ-PARK/05_output/amap/s1_map_context.json` 当前道路为空，water seed 出现乱码；`_tools/amap_context.py` 中默认关键词也疑似编码损坏。这解释了 G317、水体、桥梁等语义漏识别。
- PPT 预览中 `renderPptDrawingMedia()` 对 SVG 与底图使用 `preserveAspectRatio="none"`，CSS 又让 `.ppt-drawing-plate` `width:100%; height:100%` 填满全局图纸框，会把原图纸强制拉伸到框比例。

## 拟议实施拆分

### PR1: S2 底图诊断与误报修复

- 新增会失败的断言：模拟已配置 `TIANDITU_KEY` 且 S1 中心点存在时，`/api/s2/basemap` 返回可诊断 payload；失败时必须包含 tile/server/error/source 信息，前端不得只显示泛化“暂不可用”。
- 区分“未配置 key”“S1 中心点缺失”“服务端瓦片请求失败”“旧服务/接口不存在”。
- 前端 S2 提示展示精确原因，并保留红线离线编辑。
- 可选：增加无缓存版本戳，避免旧快照/旧接口导致误判。

### PR2: 制图交互规约 + S2 undo/redo

- `.trellis/spec/guides/project-conventions.md` 新增制图交互标准：
  - 所有可编辑制图/图形界面必须支持 `Ctrl/Cmd+Z` 撤销、`Ctrl/Cmd+Y` 或 `Ctrl/Cmd+Shift+Z` 重做；
  - 一次用户意图只入栈一次，如一次拖拽、一次新增入口、一次删除入口、一次改道路选择；
  - 若某界面不能撤销，必须在 PRD/实现中写明原因并加门禁断言。
- S2 加历史栈覆盖：
  - 红线移动/旋转/缩放；
  - 重置红线；
  - 新增/删除出入口；
  - 出入口所朝道路修改；
  - 北向角手改；
  - 周边道路名称/等级修改。

### PR3: PPT 预览比例修复

- 新增断言：打开 PPT 预览后，图纸媒体在全局图纸框内 `contain`，原始图纸长宽比不变。
- 前端预览改为：
  - plate 按原图纸或 drawing stage aspect 居中 contain；
  - SVG/base image 不再使用 `preserveAspectRatio="none"` 拉伸到 PPT 框；
  - 必要时用 nested SVG 或 CSS 计算 letterbox。
- 后端导出与预览共用同一 plate 语义，避免预览修了但导出仍拉伸。

### PR4: S2/S1 道路、水体、出入口语义增强

待用户确认路线后实施。推荐轻量路线：

- 先修编码与现有高德关键词：
  - 恢复 `DEFAULT_KEYWORDS` 为 `("水", "桥", "公园", "公交站")` 或更完整分类；
  - 重新生成 S1 context 时保留可审计 request log。
- 增加“矢量数据优先”的语义层：
  - 高德 regeo/POI：道路名、国道/省道/桥梁/水体 POI；
  - OSM Overpass：`highway=*`、`waterway=*`、`natural=water` 等矢量线/面，作为可用则采用的第二来源；
  - 统一落到 `surroundings.roads/water_features`，字段包含 `name/ref/level/source/confidence/geometry`。
- S2 卫星图叠加：
  - 主干道/次干道/支路用不同线宽和颜色；
  - 水体/河道用半透明蓝色线/面；
  - 出入口候选按“红线边与道路 geometry 最近/朝向关系”生成，而不是按道路列表顺序生成。
- UI 保留人工校正：
  - 可新增/删除道路线；
  - 可改道路等级；
  - 可拖动出入口候选并选择所朝道路；
  - 保存给 S3 的仍是确定后的人工可审计结果。

### PR5: 可选 CV research spike

- 仅在用户确认需要后做，不并入常规依赖。
- 候选：
  - SAMGeo / segment-geospatial：适合交互式遥感图像分割，可输出 GeoJSON，但依赖 PyTorch/SAM，Windows 安装和模型权重较重；
  - SpaceNet/DeepGlobe 类道路提取数据与模型：适合训练/评估道路抽取，但不是轻量运行时；
  - Microsoft RoadDetections 等公开道路检测项目/数据：更适合作参考或外部 sidecar。
- 推荐作为独立 sidecar/实验脚本，不进入主门禁，除非确认要把本仓库升级为遥感 CV 工具链。

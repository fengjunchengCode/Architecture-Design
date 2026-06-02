# S2 站点上下文 — 一次性修复计划（2026-06-02）

> 背景:codex 已用 `7d9ddbf` 把 S2 改成"红线叠加对位"流程,但用户实测 + mac claude 代码审查发现 7 类问题,本计划一次性修。供长程 `/goal` 执行。
> 红线见 `.trellis/spec/guides/project-conventions.md`(门禁驱动行为、不提交 05_output 产物、单线程小步提交)。

## 问题清单（代码审查 + 用户实测合并）

| # | 问题 | 性质 | 根因（已定位） |
|---|---|---|---|
| 1 | S2 嵌的是**高德 JSAPI 地图**,不是天地图高清卫星 | codex 偏差 | `#s2AmapMap` + `/api/amap-jsapi-config`;但 S1 用的是天地图瓦片(`_fetch_tdt_tile`/`generate_tdt_location_snapshot`,`TIANDITU_KEY`)。S2 应与 S1 一致用天地图卫星。 |
| 2 | 缺 key 时地图静默失败,**UI 无 env 自检** | UX 缺失 | 服务端已知 key 存在性(`tianditu_key`/`AMAP_*`),但前端不展示;用户不知为何用不了。 |
| 3 | 红线**只能旋转不能缩放** | codex UI 缺失 | `redline_transform` 数据层有 `scale` 字段,但只渲染了旋转手柄 `#siteRedlineRotateHandle`,无缩放手柄。 |
| 4 | S2 内嵌地图**太小**,未参照 S1 | codex UI | S2 地图容器尺寸与 S1 不一致。 |
| 5 | 语义要**手填**(出入口/周边路),没有自动生成,也无**主干道/次干道**分级 | 范围升级(原 PRD 我定了手选,现改自动) | 对位后应自动从高德路网取相邻道路 + 分级,并自动推断每条边所朝道路/候选出入口,用户仅微调。 |
| 6 | 上传散在 S1/S2,**影响排版** | UX | S0 已有上传桶;S1 有"区位图补充"、S2 有"地形图"上传行。应全部并入 S0。 |
| 7 | 对位产物是否被真正消费(避免重蹈旧配准"无人用") | 架构 | 对位须产出可用地理变换 → 喂给 #5 自动语义 + S3 的 `site_context.json`。 |

## 修复方向

1. **地图统一天地图卫星**:S2 改用与 S1 同源的天地图高清卫星底图(瓦片);移除/停用 S2 的高德 JSAPI 地图路径。高德 webservice 仅用于取周边路网语义(见 #5),不用于显示底图。
2. **Env 自检面板**:新增 `/api/env-check`(或扩展现有),前端在 S1/S2 顶部显示各 key 状态(TIANDITU_KEY / AMAP_WEBSERVICE_KEY);缺失时**明确提示**"缺 X,该功能不可用,请在仓库根 .env 配置",不再静默。
3. **红线缩放手柄**:在 S2 叠加层加缩放(角点)手柄,驱动 `redline_transform.scale`;保留旋转。粗对位,无点对。
4. **S2 地图尺寸对齐 S1**:地图容器尺寸/比例参照 S1。
5. **自动语义**:对位得到地理变换后,自动:(a) 取场地周边道路 + **分级(主干道/次干道/支路)**;(b) 按每条红线边的朝向自动匹配相邻道路、生成**候选出入口**;写入 `site_context.json`,用户可增删微调。降级:若高德路网/分级不可用,列出道路(无级)并允许手工标注,**不静默失败**。
6. **上传并入 S0**:把 S1"区位图补充"、S2"地形图"上传移到 S0 的上传区;S1/S2 不再有上传行,排版收紧。
7. **打通消费**:`site_context.json` schema 固化(north_deg / site_polygon_geo / entrances[{edge,faces_road,road_level}] / surroundings{roads[{name,level}],land_uses}),并确保 `/api/spatial` 或新路由暴露给后续。

## 验收门禁
```
python3 -m py_compile _tools/uploader/server.py _tools/drawing_workbench/*.py
node --check _tools/uploader/static/app.js
python3 _tools/tests/drawing_workbench_api_smoke.py
python3 _tools/tests/drawing_workbench_browser_smoke.py
```
服务:`python3 _tools/uploader/server.py` → http://127.0.0.1:8765(?page=s0/s1/s2)。

## 范围红线
- 不动制图工作台(workbench)与功能分区(FZ)行为。
- 不提交 `projects/*/05_output/` 运行产物。
- 不擅自加 Python/JS 依赖(要加先在回复说明)。
- 真实尺寸仍以 CAD 为准,本次不做米制精配准。

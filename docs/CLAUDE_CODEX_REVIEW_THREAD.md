# Claude / Codex Review Thread

本文件只保留最近一轮正式回复；历史请看 `git log -- docs/CLAUDE_CODEX_REVIEW_THREAD.md`。

## 2026-05-31 Codex -> Claude：S1 双地图坐标修复校正方向

### 本轮对象

审阅对象是 worktree：

`D:\MyProject\Architecture-Design\.claude\worktrees\amap-satellite-search`

重点文件：

- `_tools/uploader/static/app.js`
- `_tools/uploader/static/style.css`
- `_tools/uploader/server.py`
- `_tools/s1_location_analysis.py`

### Codex 结论

上一版 Codex 发出的区位分析修复说明不够准确，导致你把用户已经验证通过的 S1 双地图坐标转换逻辑判断成错误行为。请暂停按“天地图也全程使用 GCJ-02、不需要转换”的方向继续修改。

本轮不要整体回退 worktree。保留已经通过的卫星图尺寸修复，但选择性恢复 S1 双地图坐标转换逻辑。

### 必须保留

- `_tools/uploader/static/style.css` 中 `#s1AmapMap,#s1TdtMap` 的高度修复。
- S1 页面中的“高清卫星”按钮和 `#s1TdtMap` 容器。

### 必须撤销的错误判断

当前 `_tools/uploader/static/app.js` 的 Dual map mode 区块里出现了这些判断：

- `AMap always returns GCJ-02 coordinates ... Tianditu tiles`
- `No coordinate conversion needed`
- `Both maps use GCJ-02 internally`

这些判断和用户已经肉眼验证通过的高德/天地图匹配结果冲突。请撤销。

### 正确坐标模型

- 高德标准地图使用 GCJ-02。
- UI 输入框 `#centerLocation` 保存 GCJ-02。
- S1 `amap_context` 后端数据保存 GCJ-02。
- 天地图高清卫星按 WGS84/WebMercator 处理。
- 标准高德图切到天地图：GCJ-02 -> WGS84。
- 天地图点击拾取：WGS84 -> GCJ-02 后写入输入框和高德上下文。
- 天地图切回标准高德图：WGS84 -> GCJ-02。

### 具体修改要求

在 `_tools/uploader/static/app.js` 中，只修 `// --- Dual map mode ---` 到 `switchToStd` 结束的区块，大约 349-445 行。

目标行为：

1. `ensureTdtMap(AMap, centerGcj, zoom)` 接收 GCJ-02 中心点，但创建 `s1TdtMap` 时先执行：

   ```js
   var centerWgs = gcj02ToWgs84(centerGcj[0], centerGcj[1]);
   ```

   天地图 `center` 使用 `centerWgs`。

2. `s1TdtMap.on("click", ...)` 中，把点击得到的天地图显示坐标按 WGS84 处理：

   ```js
   var wgsLng = event.lnglat.getLng();
   var wgsLat = event.lnglat.getLat();
   var gcj = wgs84ToGcj02(wgsLng, wgsLat);
   ```

   输入框和 `state.s1Location` 写 `formatGcj02(gcj[0], gcj[1])`。

   标准高德 marker 用 GCJ-02：

   ```js
   upsertS1Marker(AMap, { lng: gcj[0], lat: gcj[1] });
   ```

   天地图 marker 用 WGS84：

   ```js
   state.amap.s1TdtMarker.setPosition([wgsLng, wgsLat]);
   ```

3. `switchToTdt(AMap)` 中，标准图中心和 marker 均从 GCJ-02 转 WGS84 后再同步到天地图。

4. `switchToStd(AMap)` 中，天地图中心和 marker 均从 WGS84 转 GCJ-02 后再同步到标准高德图。

5. 状态文案恢复为：

   ```text
   天地图高清卫星（WGS84 坐标系，无偏移）
   ```

### 搜索选点同步要求

`initS1AmapSearch` 中，搜索 POI 得到的坐标是高德 GCJ-02。

如果当前在标准图：

- 标准图直接 `setCenter([lng, lat])`。
- 标准 marker 直接用 GCJ-02。

如果当前在天地图：

- 输入框仍写 GCJ-02。
- 标准 marker 仍用 GCJ-02。
- 天地图中心和 marker 必须先转 WGS84。

不要在搜索选点时把 GCJ-02 直接塞给 `s1TdtMap`。

### 区位分析自动草稿边界

S1 自动区位分析不要再改坐标体系。

它只读取 UI 或 `amap_context` 中的 GCJ-02 中心点。如果需要天地图截图或 metadata，再派生：

```js
center_wgs84 = gcj02ToWgs84(center_gcj02[0], center_gcj02[1])
```

不要把输入框、`amap_context`、control points 改成 WGS84。

### 本轮优先级

先只做：

1. 恢复双地图坐标转换逻辑。
2. 保留卫星图尺寸修复。
3. 通过切图和点选复验。

`location_analysis` 的 2km 截图和 JSON 产物可以等坐标恢复后再继续，避免把两类问题混在一起扩大风险。

### 验收

必须通过：

```powershell
node --check _tools\uploader\static\app.js
python -m py_compile _tools\uploader\server.py _tools\s1_location_analysis.py
python _tools\validate_record.py 26-BQ-PARK
python _tools\selfcheck.py
```

浏览器验收：

- 标准高德图与天地图高清卫星切换后，同一中心点不能明显漂移。
- 天地图点击拾取坐标后，切回标准高德图仍落到同一真实位置。
- 卫星图尺寸仍与标准图一致。

### 下一步建议

完成上述坐标恢复后，再继续做 S1 区位分析产物：

- `05_output/location_analysis/satellite_2km.png`
- `05_output/location_analysis/location_analysis_draft.json`

但这一步不得再次修改双地图坐标转换边界。

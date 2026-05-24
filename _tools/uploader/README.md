# 本地上传 UI

启动：

```powershell
python _tools/uploader/server.py
```

默认地址：

```text
http://127.0.0.1:8765
```

功能：

- 创建或打开项目。
- 上传资料到标准目录。
- 检查 S0 区位图 gate。
- 打开高德坐标拾取器，录入地块中心点并生成 S1 高德上下文。
- 录入“地图点 ↔ CAD 点”控制点，供 S2 配准底图使用。
- 运行 `inventory.py`。
- 运行 `validate_record.py`。

空间定位输出：

- `projects/{code}/05_output/amap/s1_map_context.json`
- `projects/{code}/05_output/amap/s1_amap_raw.json`
- `projects/{code}/05_output/amap/control_points.json`

这个 UI 只负责资料投递、空间定位录入和确定性检查，不负责语义解析。真正的 S0/S1/S2 解析仍由 agent 按对应 skill 执行。

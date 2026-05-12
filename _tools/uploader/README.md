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
- 运行 `inventory.py`。
- 运行 `validate_record.py`。

这个 UI 只负责资料投递和确定性检查，不负责语义解析。真正的 S0 解析仍由 agent 按 `skills/S0_project_intake/SKILL.md` 执行。

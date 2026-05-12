# Agent 安装与自检手册

## 定位

本手册给 agent 使用。用户不需要手工记命令；agent 在 clone 仓库后按本文完成安装、自检和项目初始化。

## 一键自检流程

```powershell
python -m pip install -r requirements.txt
python _tools/selfcheck.py
```

自检应确认：

- Python 版本可用。
- `PyYAML` 可导入。
- `_schema/record.schema.md` 与 `_schema/folder.convention.md` 存在。
- `_tools/init_project/scaffold.py`、`_tools/validate_record.py`、`_tools/inventory.py` 存在且可编译。
- `projects/` 存在。

## 设计边界

不要让 Python 自动理解所有建筑资料。Python 只输出事实，agent 执行判断。

合理分工：

- Python：目录创建、文件扫描、hash、frontmatter 校验、marker 检查、DWG/DXF 几何提取、面积表计算。
- Agent：字段抽取、资料冲突判断、置信度判断、甲方问题生成、设计分析、汇报写作。

## S0 最小流程

```powershell
python _tools/init_project/scaffold.py 26-SZ-NSXX --type school --name "深圳南山某小学"
python _tools/uploader/server.py
python _tools/inventory.py 26-SZ-NSXX --require-s0-ready
```

如果 inventory 报告缺少区位图，agent 应停止 S0 解析并要求用户放入区位图。不要用空地址绕过 S0。

上传 UI 默认运行在 `http://127.0.0.1:8765`，用于把资料投递到标准目录并触发 inventory / validate。

# 建筑设计项目工作流仓库

这是一个面向 agent 的建筑设计工作流仓库。核心数据源是每个项目的 `05_output/record.md`，脚本只负责初始化、盘点、校验和确定性计算；项目理解、字段判断、低置信标记和甲方问题生成由 agent 按 skill 执行。

## Agent 快速入口

```powershell
python -m pip install -r requirements.txt
python _tools/selfcheck.py
python _tools/init_project/scaffold.py 26-SZ-NSXX --type school --name "深圳南山某小学"
python _tools/uploader/server.py
python _tools/inventory.py 26-SZ-NSXX --require-s0-ready
python _tools/validate_record.py 26-SZ-NSXX
```

上传 UI 默认运行在 `http://127.0.0.1:8765`。

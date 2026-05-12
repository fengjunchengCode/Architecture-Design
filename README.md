# 建筑设计项目工作流仓库

这是一个面向 agent 的建筑设计工作流仓库。核心数据源是每个项目的 `05_output/record.md`，脚本只负责初始化、盘点、校验和确定性计算；项目理解、字段判断、低置信标记和甲方问题生成由 agent 按 skill 执行。

`inventory.py` 会为每个输入文件标注 `read_policy`。正文提取优先走 `python _tools/extract_text.py {文件路径}`。老 `.doc` 文件不会被直接读取正文，必须先转换为 `.docx`、PDF 或 TXT；agent 只能先记录其路径、hash 和文件名。

当前 skill 系统采用“根 skill router + 阶段子 skill + shared 协议库”的结构：

- `SKILL.md`：总协议与路由器。
- `skills/S0_project_intake/SKILL.md`：项目档案初始化。
- `skills/S1_site_analysis/SKILL.md`：区位与场地语义分析。
- `skills/S2_dwg_parse/SKILL.md`：DWG、红线与地形解析。
- `skills/S3_area_and_massing/SKILL.md`：面积需求与强排初判。
- `skills/S4_questions_summary/SKILL.md`：甲方问题清单。
- `skills/S9_report_outline/SKILL.md`：汇报大纲。
- `skills/_shared/*.md`：跨阶段共享协议。

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

Agent 执行具体阶段前，应先读取 `SKILL.md` 做路由与 gate 判断。

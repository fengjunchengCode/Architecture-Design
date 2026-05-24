# 建筑设计项目工作流仓库

这是一个面向 agent 的建筑设计工作流仓库。核心数据源是每个项目的 `05_output/record.md`，脚本只负责初始化、盘点、校验和确定性计算；项目理解、字段判断、低置信标记和甲方问题生成由 agent 按 skill 执行。

开发本仓库时遵守 `skills/_shared/development_contract.md`：先澄清目标、简洁优先、精准修改、目标驱动验证。该契约参考 `multica-ai/andrej-karpathy-skills`，用于约束 agent 修改工具、UI、schema 和 skill 的方式。

`inventory.py` 会为每个输入文件标注 `read_policy`。正文提取优先走 `python _tools/extract_text.py {文件路径}`。老 `.doc` 文件不会被直接读取正文，必须先转换为 `.docx`、PDF 或 TXT；agent 只能先记录其路径、hash 和文件名。

JPG/PNG 区位图、现场照片等视觉资料由 `python _tools/vision_route.py {项目代号} --write` 自动路由到 `VISION_MODEL`。普通用户不需要手动切换 API 模型；未配置视觉模型时，工具会生成降级 sidecar，S0 继续以待确认问题推进。

视觉模型配置放在仓库根目录 `.env` 中，可从 `.env.example` 复制。至少配置一种 provider：

```powershell
Copy-Item .env.example .env
python _tools/vision_route.py --list-providers
```

如果 provider 未配置、API 报错或模型不存在，agent 不得改用当前对话模型直接读图；应读取 `05_output/vision/` 的 sidecar，并把图片中的地址、坐标、红线和现场条件列为待确认问题。

S1 区位、道路、POI 和来向分析由高德 Web Service 工具提供确定性地图上下文。把高德 Web Service Key 写入 `.env`：

```powershell
AMAP_WEBSERVICE_KEY=你的高德Web服务Key
python _tools/amap_context.py --check
python _tools/amap_context.py 26-SZ-NSXX --location "经度,纬度" --write
```

如果暂时没有高德坐标，可使用高德坐标拾取器获取地块中心点；只有中心点时 S1 只能输出周边关系和入口候选，不能精确绑定到 CAD 红线边。

DWG/DXF 地形资料由 `python _tools/dwg_probe.py {项目代号} --json --write` 进入 S2。该工具会自动检测 `ezdxf` 与 ODA File Converter，能转换就先把 DWG 转为 DXF 并提取确定性几何事实；缺工具时会输出 `install_guidance`，agent 应先按指引安装或配置后重跑。手动 CAD 导出 DXF 只作为自动转换失败后的降级方案。

当前 skill 系统采用“根 skill router + 阶段子 skill + shared 协议库”的结构：

- `SKILL.md`：总协议与路由器。
- `skills/S0_project_intake/SKILL.md`：项目档案初始化。
- `skills/S1_site_analysis/SKILL.md`：区位与外部关系分析。
- `skills/S2_dwg_parse/SKILL.md`：CAD、红线与地形几何解析。
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
python _tools/vision_route.py 26-SZ-NSXX --write
python _tools/amap_context.py 26-SZ-NSXX --location "经度,纬度" --write
python _tools/dwg_probe.py 26-SZ-NSXX --json --write
python _tools/validate_record.py 26-SZ-NSXX
```

上传 UI 默认运行在 `http://127.0.0.1:8765`。

Agent 执行具体阶段前，应先读取 `SKILL.md` 做路由与 gate 判断。

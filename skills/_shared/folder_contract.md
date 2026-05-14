# Folder Contract

项目目录遵守 `_schema/folder.convention.md` 与 `_schema/folder.convention.yaml`。

## 标准结构

```text
projects/{code}/
├── 01_briefing/
├── 02_site/
│   ├── 区位图/
│   ├── 地形图/
│   └── 现场照片/
├── 03_references/
├── 04_chat/
└── 05_output/
    ├── record.md
    ├── inventory.json
    ├── parse_log.md
    └── 汇报文档.md
```

## Gate

- S0/S1：`02_site/区位图/` 至少 1 个 `png`、`jpg`、`jpeg` 或 `pdf`。
- S2：需要 `02_site/地形图/` 中有 DWG、PDF、红线图或等价资料。
- S3b：需要 `site.area_sqm` 或 S2 可确认地块面积。
- S9：建议 S1 与 S3 已有有效正文。

## 工具

```powershell
python _tools/init_project/scaffold.py {code} --type {type} --name "{name}"
python _tools/uploader/server.py
python _tools/inventory.py {code} --require-s0-ready --write
python _tools/vision_route.py {code} --write
python _tools/validate_record.py {code}
```

## 文件名

用户文件名不必完全标准。Agent 和脚本应先依目录、扩展名和内容判断，不因中文文件名阻塞 S0。

## 二进制读取边界

`inventory.py` 会为每个文件写入 `read_policy`。Agent 必须遵守：

- `.doc` 老 Word 二进制文件是 `legacy_word_conversion_required`，只能登记路径/hash/文件名，先转换再解析正文。
- DWG、SKP、PSD、HEIC 等是 `binary_index_only`，没有专用工具时只登记事实。
- 图片按视觉资料处理，先走 `_tools/vision_route.py` 自动路由到视觉模型；PDF/DOCX 按专用提取器或渲染器处理。
- 不要用 `strings`、裸 `cat`、裸 `Read` 或临时依赖探测作为二进制解析兜底。

需要抽取正文时，优先运行：

```powershell
python _tools/extract_text.py {文件路径}
```

需要解析区位图、现场照片、参考图时，优先运行：

```powershell
python _tools/vision_route.py {项目代号} --write
```

该工具读取 `OPENAI_API_KEY` 和 `VISION_MODEL`。未配置时仍会写入 `05_output/vision/*.json`，提醒 S0 自动降级为待确认问题；不要让普通用户手动切换 API 模型。

# Record Contract

`projects/{code}/05_output/record.md` 是唯一核心真相文件。

## 读取规则

- 先解析 YAML frontmatter，再读正文 marker。
- frontmatter 字段遵守 `_schema/record.schema.md`。
- 项目文件夹名必须等于 `project.code`。
- `schema_version` 固定为 `"1.0"`，除非 schema 正式升级。

## 写入规则

- 写入前保留未负责的 frontmatter 字段和所有非目标 marker 段。
- 只更新当前 skill 负责的字段和 marker。
- 写入 `project.updated_at` 使用本地 ISO 8601，含时区。
- 写完必须运行：

```powershell
python _tools/validate_record.py {项目代号}
```

## 真相源边界

- `inventory.json` 是文件扫描事实，不是项目语义真相。
- `workflow_state.json` 如后续引入，只能是可重建的派生状态。
- 缺少 `workflow_state.json` 或 `skill_runs.jsonl` 不影响续跑；继续工作只依赖 `record.md`。
- `parse_log.md` 是解析日志，不覆盖 `record.md`。
- Notion、Obsidian、PPT、汇报文档都是投影或产物。

## 字段判断

- 无法确认的字段不要编造。
- 已有值但来源弱，写入 `low_confidence_fields`。
- 没有值且影响后续工作，写入 `pending_questions`。

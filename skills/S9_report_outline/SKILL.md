---
name: s9-report-outline
description: 建筑设计工作流 S9 汇报大纲与文档草稿。用于用户要求生成汇报框架、汇报文档、PPT 文字骨架、方案说明或基于 S1/S3/S4 输出对甲方汇报时。只写 record.md 的 s9_report_outline marker，可另写 05_output/汇报文档.md。
---

# S9 汇报大纲

## 目标

把已完成的场地分析、面积测算、问题清单和设计判断组织成可汇报的结构。S9 不是反向补事实的阶段，只读已有事实和明确推断。

## 必读

- `SKILL.md`
- `skills/_shared/record_contract.md`
- `skills/_shared/marker_contract.md`
- `skills/_shared/output_style.md`
- `_schema/record.schema.md`

## 输入

- `record.md` frontmatter
- S1 场地分析
- S3 面积测算
- S4 问题清单
- `03_references/` 参考案例（如有）

## 前置条件

建议 S1 和 S3 至少有有效正文。若缺失，先列阻塞项，不写完整汇报。

## Agent 职责

1. 提炼项目背景、场地判断、任务书需求、核心问题和下一步设计方向。
2. 输出六段式汇报大纲。
3. 必要时另写 `projects/{code}/05_output/汇报文档.md`，但不把汇报文档当真相源。
4. 不反向修改 S1/S3/S4 的事实。
5. 只改写 `s9_report_outline` marker。

## 输出结构

```markdown
### 汇报目标

### 六段式大纲

1. 项目背景
2. 区位与现状
3. 任务与约束
4. 关键问题
5. 初步策略
6. 需要甲方确认事项

### PPT/文档页码建议

### 仍需补充资料
```

## 禁止

- 不虚构已确认设计方案。
- 不把 pending 问题写成已解决。
- 不把外部投影字段写回核心 schema。

## 校验

```powershell
python _tools/validate_record.py {code}
```


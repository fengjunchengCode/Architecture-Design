---
name: s4-questions-summary
description: 建筑设计工作流 S4 甲方问题清单与低置信字段归并。用于用户要求整理待问甲方问题、检查缺失资料、汇总 pending_questions、输出沟通话术、判断下一步阻塞项时。任何阶段可运行，只写 record.md 的 s4_questions_summary marker。
---

# S4 问题清单管理

## 目标

把各阶段产生的 `pending_questions` 和 `low_confidence_fields` 归并成可直接给甲方/助理沟通的问题清单。

## 必读

- `SKILL.md`
- `skills/_shared/record_contract.md`
- `skills/_shared/marker_contract.md`
- `skills/_shared/confidence_contract.md`
- `skills/_shared/output_style.md`

## 输入

- `record.md` frontmatter
- S0/S1/S2/S3 marker 正文
- `completeness.blocked`

## 前置条件

无硬前置。S4 可在任意阶段运行。

## Agent 职责

1. 读取所有 `pending_questions` 和 `low_confidence_fields`。
2. 去重、合并同类问题，保留原始字段路径。
3. 按紧急度分组：阻塞当前阶段、阻塞后续强排、可后补。
4. 改写成甲方能回答的短问题。
5. 标注建议提问对象：甲方、测绘、设计负责人、现场人员。
6. 只改写 `s4_questions_summary` marker。

## 输出结构

```markdown
### 当前阻塞问题

### 设计推进前建议确认

### 可后补问题

### 低置信字段复核

### 可直接发送给甲方的话术
```

## 禁止

- 不新增无来源事实。
- 不删除 frontmatter 中尚未解决的 pending。
- 不把问题改成含糊建议；必须可回答。

## 校验

```powershell
python _tools/validate_record.py {code}
```


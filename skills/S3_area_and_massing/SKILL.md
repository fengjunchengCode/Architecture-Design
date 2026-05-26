---
name: s3-area-and-massing
description: 建筑设计工作流 S3 任务书拆解、面积测算、容积率和强排初判。用于用户要求根据 brief 计算功能面积、班级/床位/车位等指标、容积率校核、强排可行性或整理设计规模时。只写 record.md 的 s3_area_calc marker。
---

# S3 面积需求与强排初判

## 目标

把任务书和项目类型模板转成可讨论的面积需求、约束清单和强排前置判断。S3 先作为单 skill，内部区分 S3a 面积需求测算与 S3b 容积率/强排校核。

## 必读

- `SKILL.md`
- `skills/_shared/record_contract.md`
- `skills/_shared/marker_contract.md`
- `skills/_shared/confidence_contract.md`
- `skills/_shared/output_style.md`
- `_schema/record.schema.md` 的 `brief` 类型模板

## 输入

- `record.md` frontmatter 与 S0 摘要
- `01_briefing/` 任务书和补充资料
- S2 的 `site.area_sqm`、`far_max`、`height_limit_m`、`setback`（如有）

## 前置条件

- S3a：至少有 `brief.summary`、任务书文本或可抽取的项目类型关键信息。
- S3b：需要 `site.area_sqm`。缺少时只做 S3a，并把 S3b 写为阻塞。

## Agent 职责

1. 根据 `project.type` 读取 schema 推荐字段，优先抽取功能需求。
2. 整理面积需求表：功能、数量、单项指标、面积、来源、置信度。
3. 明确规范依据是用户资料、常识参考还是待用户确认；不编造法定指标。
4. 如 `site.area_sqm` 和 `far_max` 可用，做容积率和强排初判。
5. 缺指标进入 `pending_questions`。
6. 只改写 `s3_area_calc` marker。

## 输出结构

```markdown
### S3a 面积需求测算

| 功能 | 数量 | 单项指标 | 面积 | 来源 | 置信度 |

### 关键约束

### S3b 容积率 / 强排初判

### 待确认指标

### 对方案阶段的影响
```

## 禁止

- 不把通用经验值写成甲方确定需求。
- 不在 `site.area_sqm` 缺失时做强排结论。
- 不新增 schema 未定义的 frontmatter 字段。

## 完成后建议

S3 marker 写好且 validator 通过后，agent 在对话窗口附一条建议：

> "S3 已完成。下一步建议：S10（确定项目设计风格 + 出技术图）。
>  理由：S3 已落，可进入图面表达阶段。用户可继续做 S4 问题清单或直接进 S10。"

不强制阻塞，用户决定走向。

## 校验

```powershell
python _tools/validate_record.py {code}
```


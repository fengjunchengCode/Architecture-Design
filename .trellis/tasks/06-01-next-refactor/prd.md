# PRD：下一个重构（待定）

> 占位任务,示范 Trellis 任务结构。**请把要重构的功能填进下面五段**,或用 `trellis-brainstorm` 技能与 mac claude 一起补全后再 `task.py start`。
> 实施前必读 `.trellis/spec/guides/project-conventions.md`(协作红线 + 门禁)。

## Objective（目标，一句话）
<待填：要重构/实现什么>

## Scope（范围 / 涉及文件）
- <待填：改哪些模块/文件,不碰哪些>

## Constraints（约束 / 红线）
- 单线程顺序,每条一次提交;不并行子 agent。
- 门禁驱动行为(不验产物);功能分区(FZ)逐像素回归。
- 不提交 `05_output` 运行产物;不擅自加重依赖;不改评审线程。

## Done when（完成判据）
- <待填：可验证的行为断言 + 门禁全绿>

## Stop if（何时停下来问）
- 需求歧义、需引入新依赖、要改 FZ 行为或 schema —— 先问 mac claude。

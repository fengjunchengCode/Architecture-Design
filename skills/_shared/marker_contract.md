# Marker Contract

每个阶段只能改写自己 marker 之间的正文。

## Marker 列表

| Skill | Marker |
|---|---|
| S0 | `s0_parsed` |
| S1 | `s1_site_analysis` |
| S2 | `s2_dwg_parse` |
| S3 | `s3_area_calc` |
| S4 | `s4_questions_summary` |
| S9 | `s9_report_outline` |

## 写入方式

1. 读取完整 `record.md`。
2. 定位 `<!-- BEGIN:{marker} -->` 与 `<!-- END:{marker} -->`。
3. 完整替换 marker 内正文。
4. 不移动 marker，不改其他 marker 内容。
5. 写入后运行 `validate_record.py`。

## 幂等要求

- 同一输入重复执行，应得到结构一致的输出。
- 如果没有新信息，保留已有分析结论并标注“本次无新增资料”。
- 不要把历史输出复制到其他 marker。

## 续跑要求

- `record.md` 是续跑依据。已有 marker 内容代表该阶段已经有执行结果，agent 不得默认从 S0 重新开始。
- 执行任何阶段前，先读取目标 marker 当前内容，并判断用户是要补充、重跑本阶段，还是进入下一阶段。
- 重跑本阶段时，只完整替换本阶段 marker 内正文；其他 marker 必须原样保留。
- 如果已有阶段结果仍然有效，只在本阶段输出中标注“沿用既有结果”或“基于新增资料更新”，不要清空重写为占位内容。
- 缺少派生状态文件不是失败条件。只要 `record.md` marker 成对且 frontmatter 可校验，就可以继续。

## 失败处理

- marker 缺失或不成对：停止写入，先运行校验并修复结构。
- 用户要求跨 marker 写：拒绝并路由到对应子 skill。
- 子 skill 发现前置不足：在本 marker 内写“阻塞原因”，并更新 frontmatter `completeness.blocked`。

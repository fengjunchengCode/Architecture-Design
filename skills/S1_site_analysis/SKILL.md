---
name: s1-site-analysis
description: 建筑设计工作流 S1 区位与场地语义分析。用于用户要求分析项目区位、周边路网、场地入口、500m/1000m 服务范围、现场照片、区位图解读或从 S0 进入场地分析时。只写 record.md 的 s1_site_analysis marker，并更新相关 pending/low_confidence/completeness。
---

# S1 区位与场地语义分析

## 目标

把 S0 已建立的项目档案推进到可支撑概念和汇报的场地认知：位置、周边、到达、入口、现状问题、机会点和下游设计影响。

## 必读

- `SKILL.md`
- `skills/_shared/record_contract.md`
- `skills/_shared/marker_contract.md`
- `skills/_shared/folder_contract.md`
- `skills/_shared/confidence_contract.md`
- `skills/_shared/output_style.md`
- `_schema/record.schema.md`

## 输入

- `projects/{code}/05_output/record.md`
- `projects/{code}/05_output/inventory.json`（如有）
- `projects/{code}/02_site/区位图/`
- `projects/{code}/02_site/现场照片/`
- S0 的 `s0_parsed` 段

## 硬门槛

- `02_site/区位图/` 至少 1 张图。
- `site.address` 或 `site.coords` 至少其一。若都缺失，先转 S4 生成甲方问题，不做 S1 判断。

## Agent 职责

1. 读取区位图和现场照片，提取可见道路、水体、建筑、场地边界、出入口线索。
2. 区分“资料明确事实”和“agent 视觉/语义推断”。
3. 分析周边功能、交通到达、步行尺度、潜在人流方向、噪声/景观/日照等对设计的影响。
4. 形成 500m/1000m 层级的区位判断；如缺比例尺或地图来源，标低置信。
5. 更新 frontmatter 中可由 S1 确认或低置信补充的 `site.address`、`site.coords`、`low_confidence_fields`、`pending_questions`、`completeness`。
6. 只改写 `s1_site_analysis` marker。

## 输出结构

写入 `s1_site_analysis` marker 内：

```markdown
### S1 输入

### 已确认区位事实

### 周边与交通判断

### 现场照片观察

### 设计机会与限制

### 低置信与待复核

### 对下游阶段的影响
```

## 禁止

- 不根据区位图目测写确定地块面积。
- 不把地图推断坐标当作正式坐标；只能低置信。
- 不跨写 S2/S3/S9 marker。

## 校验

写入后运行：

```powershell
python _tools/validate_record.py {code}
```


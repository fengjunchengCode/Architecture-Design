---
name: s2-dwg-parse
description: 建筑设计工作流 S2 DWG、红线、地形和几何解析。用于用户要求解析地形图、红线图、DWG、地块面积、边界形状、高差、退线线索或为强排提供几何事实时。只写 record.md 的 s2_dwg_parse marker，并谨慎更新 site 几何字段。
---

# S2 DWG 与地形解析

## 目标

从 DWG、PDF 红线、地形资料中提取确定性几何事实，并把无法自动确认的内容明确阻塞给后续阶段。

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
- `projects/{code}/05_output/inventory.json`
- `projects/{code}/02_site/地形图/`
- 可选：`02_site/区位图/`、S1 分析

## 前置条件

`02_site/地形图/` 中至少有 DWG、PDF、红线图或可读地形资料。只有 `.dwl` / `.dwl2` 锁文件不算有效输入。

## 确定性工具链

S2 解析 DWG/DXF 时必须先运行：

```powershell
python _tools/dwg_probe.py {code} --json --write
```

该脚本会自动检测 `ezdxf` 与 ODA File Converter。若工具已存在，优先使用 ODA 将 DWG 转为 DXF，再由 `ezdxf` 提取图层、实体统计、闭合多段线候选、文字标注和边界范围等机器事实。若 `ezdxf` 或 ODA 不存在，脚本会返回 `install_guidance`，agent 应按指引安装或配置工具后重跑；手动 CAD 导出 DXF 只作为自动转换失败后的降级方案。

不得裸读 DWG 二进制内容，也不得因为缺少 ODA 就跳过工具检测直接要求用户手动导出。

## Agent 职责

1. 列出可用地形/红线文件及 hash。
2. 读取 `05_output/dwg_probe.json`，区分可由脚本确定的几何事实和仅能人工判断的图面语义。
3. 优先使用 `dwg_probe.py` 结果，不手算复杂几何。
4. 可确认时更新 `site.area_sqm`、`site.boundary_shape`、`site.has_elevation_diff` 等字段。
5. 不确定的面积、坐标、高差进入 pending 或 low confidence。
6. 只改写 `s2_dwg_parse` marker。

## 输出结构

```markdown
### S2 输入文件

### 可确定几何事实

### 图面语义观察

### 面积/边界/高差判断

### 阻塞项与待补资料

### 对 S3 强排和面积校核的影响
```

## 禁止

- 不从现场照片或区位图估算正式地块面积。
- 不把 DWG 锁文件当成设计资料。
- 不在没有脚本或明确图面标注时输出高精度坐标/面积。
- 不绕过 `dwg_probe.py` 直接读取或猜测 DWG 内容。

## 校验

```powershell
python _tools/validate_record.py {code}
```


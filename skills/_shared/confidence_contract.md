# Confidence Contract

本协议统一 `pending_questions` 和 `low_confidence_fields` 的判断。

## pending_questions

用于“没有可靠值，需要问甲方或人工补资料”的问题。

典型场景：

- 没有任务书，项目目标不清。
- 只有区位图，没有明确地址或坐标。
- 没有红线/DWG，无法确认地块面积。
- 面积需求缺少班级数、床位数、车位数、功能面积等关键输入。

写法要求：

- `id` 项目内唯一，格式 `q001`。
- `field` 尽量指向 YAML 字段路径；非字段问题可为 null。
- `question` 要能直接发给甲方或助理。
- `raised_by` 写当前 skill，如 `S0`、`S1`。
- `status` 初始为 `待问`。

## low_confidence_fields

用于“已有值，但来源弱或需人工复核”的字段。

典型场景：

- 地址来自区位图 OCR 或文件名。
- 项目类型由文件夹名推断。
- 风格偏好来自参考图感知，没有甲方原话。
- 地块边界来自图片目测，而非 DWG。

写法要求：

```yaml
low_confidence_fields:
  - field: site.address
    reason: "仅从区位图文字推断，未见正式任务书地址"
```

## 禁止

- 不要为了让下游 skill 解锁而编造字段。
- 不要把低置信字段同时当作确定依据。
- 不要把“缺资料”写成模糊正文而不进入 pending。


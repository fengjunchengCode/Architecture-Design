# _schema/folder.convention.md · 文件夹 & 命名约定

<aside>
🎯

**定位**：文件夹结构 + 文件命名 + 投递助手「必填/可选」配置的说明文档。机器读取版本见 `_schema/folder.convention.yaml`。

**配套**：`_schema/record.schema.md` · `_schema/folder.convention.yaml` · `AGENTS.md`

</aside>

## 一、顶层仓库结构

```jsx
repo_root/                              ## 用户 clone 到哪里，哪里就是仓库根
├── .git/
├── .gitignore
├── README.md                            ## 仓库说明
├── AGENTS.md                            ## Agent 工作流入口
├── requirements.txt                     ## Python 依赖
├── _schema/                             ## 权威文档区
│   ├── record.schema.md                 ## 字段权威定义
│   └── folder.convention.md             ## 本文件
│   └── folder.convention.yaml           ## 机器可读目录规范
├── _tools/                              ## 脚本区
│   ├── selfcheck.py                     ## agent 自检
│   ├── inventory.py                     ## 项目文件盘点
│   ├── vision_route.py                  ## 图片资料自动路由到视觉模型
│   ├── validate_record.py               ## 校验脚本
│   └── init_project/
│       └── scaffold.py                  ## 项目脚手架
├── skills/
│   └── S0_project_intake/
│       └── SKILL.md
└── projects/
    └── {项目代号}/                       ## 一个项目一个文件夹
        ├── 01_briefing/
        ├── 02_site/
        │   ├── 区位图/
        │   ├── 地形图/
        │   └── 现场照片/
        ├── 03_references/
        ├── 04_chat/
        └── 05_output/
            ├── record.md                ## 真相文件
            ├── parse_log.md             ## S0 解析日志
            ├── vision/                  ## 图片视觉解析 sidecar
            └── 汇报文档.md              ## S9 产出
```

## 二、项目代号与文件夹名

- 项目文件夹名 **必须严格等于** `record.md` 中 `project.code`；校验时取 `projects/{code}/05_output/record.md` 所属项目根目录名。
- 格式：`{YY}-{CITY2_3}-{ABBR}`，详见 `_schema/record.schema.md` § 2.2
- **严禁**使用中文 / 空格 / 中文符号作为项目文件夹名

## 三、各子文件夹规范

### 3.1 `01_briefing/` · 需求类

| **文件** | **扩展名** | **数量** | **必填** | **说明** |
| --- | --- | --- | --- | --- |
| `brief.{ext}` | doc / docx / pdf / md / txt | 0—1 | ○ 推荐 | 任务书主文件。`.doc` 只登记文件事实，正文需先转换为 docx / pdf / txt 再解析。没有 brief 时允许从聊天记录或补充说明启动，S0 会提 pending_question |
| `supplement_*.{ext}` | txt / md / doc / docx / jpg / png | 0—n | ○ 可选 | 补充说明，文件名用下划线 + 英文描述，如 `supplement_classroom_size.jpg`。`.doc` 同样需转换后解析正文 |

### 3.2 `02_site/区位图/` · 区位类

| **文件名范例** | **扩展名** | **数量** | **必填** | **说明** |
| --- | --- | --- | --- | --- |
| `location_*.{ext}` | png / jpg / jpeg / pdf | 1—n | ✅ 至少 1 张 | 区位图是 S0 硬门槛。原始投递可宽松命名，归档推荐改为 `location_1km.png` / `location_500m.png` 等 |

JPG/PNG/WEBP 区位图上传后不要求用户切换 API 模型。S0 运行时由 agent 调用 `python _tools/vision_route.py {项目代号} --write`，工具自动读取 `OPENAI_API_KEY` 和 `VISION_MODEL` 做视觉解析；未配置时写入降级 sidecar，后续由 S0 把地址、坐标、红线等缺口列入待确认问题。

### 3.3 `02_site/地形图/` · 地形类

| **文件名范例** | **扩展名** | **数量** | **必填** | **说明** |
| --- | --- | --- | --- | --- |
| `topo_*.dwg` | dwg | 0—n | ⚠️ S2 必填；S0/S3a 可选 | 地形图原始 DWG。无则 S2 / S3b 容积率与强排校核被阻塞，但不阻塞 S0/S1/S3a/S4 |
| `topo_*.pdf` | pdf | 0—n | ○ 可选 | DWG 导出的 PDF，作同步阅读 |
| `redline_*.{ext}` | jpg / png / pdf | 0—n | ○ 可选 | 红线图 / 规划条件图 |

### 3.4 `02_site/现场照片/` · 现场类

| **文件名范例** | **扩展名** | **数量** | **必填** | **说明** |
| --- | --- | --- | --- | --- |
| `site_photo_*.jpg` | jpg / jpeg / png / heic | 0—n | ○ 可选 | 踏勘照片。推荐保留 EXIF（含拍摄 GPS），供将来自动序列化位置 |

### 3.5 `03_references/` · 参考案例

| **文件名范例** | **扩展名** | **数量** | **必填** | **说明** |
| --- | --- | --- | --- | --- |
| `ref_{案名-拼音}.{ext}` | jpg / png / pdf / md | 0—n | ○ 可选 | 甲方提供的参考案例。范例：`ref_kerry-school.jpg` |

### 3.6 `04_chat/` · 聊天记录

| **文件名范例** | **扩展名** | **数量** | **必填** | **说明** |
| --- | --- | --- | --- | --- |
| `chat_{YYYY-MM-DD}.{ext}` | txt / html / md | 0—n | ○ 可选 | 甲方聊天记录导出。范例：`chat_2026-05-12.html` |

### 3.7 `05_output/` · 产出区（agent 写入，人不手工动）

| **文件** | **写入者** | **说明** |
| --- | --- | --- |
| `record.md` | S0 创建；S1/S2/S3/S4/S9 patch | 真相文件，见 `_schema/record.schema.md` |
| `parse_log.md` | S0 追写 | 解析摘要、文件 hash、⚠️ 字段详单 |
| `vision/*.vision.json` | `vision_route.py` | 图片识别 sidecar；配置视觉模型时写识别结果，未配置时写降级提示 |
| `vision/index.json` | `vision_route.py` | 当前图片识别结果索引 |
| `amap/s1_map_context.json` | `amap_context.py` / 上传 UI | S1 高德地图上下文，含中心点、逆地理编码、500m/1000m POI |
| `amap/s1_amap_raw.json` | `amap_context.py` | 高德原始响应与请求参数（key 已脱敏） |
| `amap/control_points.json` | 上传 UI / S2 | 用户录入的“地图点 ↔ CAD 点”控制点，用于 S2 配准 |
| `汇报文档.md` | S9 | 6 段式汇报初稿 |
| `assets/` | 各 skill | 高德截图、生成示意图、中间产物 |

## 四、文件命名规则与自动重命名

<aside>
✍️

**设计动机**：中文空格/特殊符号会拖累下游脚本（LISP / Python ezdxf / shell）。投递助手上传时自动转化。

</aside>

### 4.1 自动重命名规则（uploader 上传时执行）

1. **去除**：首尾空白、双空格压缩成单空格
2. **转化**：中文标点、全角空格 → ASCII、中文 → 拼音（可选开关，默认开）
3. **替换**：空格 → `_`
4. **保留**：字母 / 数字 / `_` / `-` / `.`
5. **去除**：其他任何特殊符号
6. **转小写**（可选开关，默认不转，保留人读性）
7. **处理序号**：同类名冲突时追加 `_2` `_3`...

#### 转化示例

| **原名** | **上传后** |
| --- | --- |
| `需求文档 最终版.docx` | `brief.docx`（区位上可以重命名为标准名） |
| `区位 一公里.png` | `location_1km.png` |
| `IMG_2025.jpg`（现场照） | `site_photo_001.jpg` |
| `嘉里小学.jpeg`（参考） | `ref_jiali-xiaoxue.jpeg` |

### 4.2 是否推荐人工重命名

- **推荐**：拖拽上传后在助手面板上调整为语义清晰的名字（如 `location_1km.png` 表意明确）
- **不推荐**：在系统资源管理器里手动重命名，避开助手的验证逻辑

## 五、投递助手「必填/可选」配置（YAML）

<aside>
⚙️

**说明**：机器读取版本单独存放在 `_schema/folder.convention.yaml`。下面仅展示核心结构，可被项目级 `{项目代号}/.uploader.yaml` 覆盖（不同项目类型调整必填项）。

</aside>

```yaml
schema_version: "1.0"
folders:
  - path: 01_briefing
    label: "需求类"
    required: true                  ## 本文件夹本身需要存在
    items:
      - pattern: "brief.*"
        ext: [doc, docx, pdf, md, txt]
        min: 0                      ## 极简启动 OK；S0 会补 pending_question
        max: 1
        required: false             ## 软必填·助手中显示为“推荐”
      - pattern: "supplement_*.*"
        ext: [txt, md, doc, docx, jpg, png]
        min: 0
        max: 999
        required: false

  - path: 02_site/区位图
    label: "区位图"
    required: true
    items:
      - pattern: "*.*"
        ext: [png, jpg, jpeg, pdf]
        min: 1                      ## 至少 1 张才能跳 S0
        max: 999
        required: true
        unblocks: [S0, S1]

  - path: 02_site/地形图
    label: "地形图"
    required: true
    items:
      - pattern: "topo_*.dwg"
        ext: [dwg]
        min: 0
        max: 999
        required: false             ## S0 不需要、S2 需要
        unblocks: [S2]
      - pattern: "*.*"
        ext: [pdf, jpg, png, dwg]
        min: 0
        max: 999
        required: false

  - path: 02_site/现场照片
    label: "现场照片"
    required: true
    items:
      - pattern: "*.*"
        ext: [jpg, jpeg, png, heic]
        min: 0
        max: 999
        required: false

  - path: 03_references
    label: "参考案例"
    required: true
    items:
      - pattern: "ref_*.*"
        ext: [jpg, png, pdf, md]
        min: 0
        max: 999
        required: false

  - path: 04_chat
    label: "聊天记录"
    required: true
    items:
      - pattern: "chat_*.*"
        ext: [txt, html, md]
        min: 0
        max: 999
        required: false

  - path: 05_output
    label: "产出"
    required: true
    items: []                       ## agent 写入，助手不提供上传入口

s0_ready_gate:
  required:
    - path: 02_site/区位图
      ext: [png, jpg, jpeg, pdf]
      min: 1

## 重命名规则
rename:
  enable_pinyin: true               ## 中文 → 拼音
  lowercase: false                  ## 保留人读性
  replace_space_with: "_"
  allowed_chars: "[a-zA-Z0-9_\\-.]"
  strip_others: true
```

## 六、助手 UI 表现（读本文件后的渲染逻辑）

| **状态** | **条件** | **UI 表现** |
| --- | --- | --- |
| ✅ 已就绪 | 本项 `required: true` 且 `count >= min` | 绿色勾 |
| ⚠ 必填缺失 | 本项 `required: true` 且 `count < min` | 黄色警告 + 「拖入这里」占位 |
| ○ 可选 | 本项 `required: false` | 灰色圆圈，当前文件数量显示为 `n 个` |
| ⛔ 不合规 | 扩展名 / pattern 不匹配 | 红色 + 提示转到哪里（如 dwg 拖到区位图 → 提示转到地形图） |

**「触发 S0 解析」按钮点亮条件**：`s0_ready_gate` 全部通过 ↔ 点亮。

## 七、按 `project.type` 的特殊需求（覆盖项）

<aside>
🧩

不同类型项目可能需要额外文件夹或调整必填项。下表是**增量覆盖项**，默认仓库级配置。

</aside>

| **`project.type`** | **额外要求** |
| --- | --- |
| `school` | 推荐加一张 `02_site/地形图/topo_*.dwg`（汇报需面积核算） |
| `renovation` | 新增 `02_site/现状测绘/` 子文件夹，默认 required=false |
| `cultural_tourism` | 新增 `02_site/所广区范围/`（多节点结合场地） |
| `street_scape` | 「区位图」`min: 1` 依然；「地形图」`required: false`（常无 DWG，现场为主）；「现场照片」`min: 3` 提升 |
| `unknown` | 区位图仍为全局必选；`01_briefing/` 或 `04_chat/` 至少一类资料为强烈建议，但不作为 S0 硬门槛 |

**覆盖机制**：项目创建时如果 `project.type` 明确，S0 脚手架在项目路径下生成 `.uploader.yaml`；助手读取时优先项目级配置，后退到仓库级。

## 八、与 S0 脚手架的交互

1. `/init_project 26-SZ-NSXX --type school --name "深圳南山某小学"` 调起脚手架阶段
2. 脚本读本文件 § 3，按表创建空文件夹（`02_site/` 下三个子文件夹都要）
3. 依据 § 7 type 覆盖表生成项目级 `.uploader.yaml`
4. 写入空 `record.md`（`project.code` / `project.name` / `project.type` / `stage: 待放置文件` + 全部 marker 占位）
5. agent/用户放置资料后运行 `python _tools/inventory.py 26-SZ-NSXX --require-s0-ready --write`
6. 区位图门槛满足后，agent 执行 `skills/S0_project_intake/SKILL.md`，读取资料并写入 `record.md`

## 九、.gitignore 推荐设置

```jsx
## 临时 / 系统
.DS_Store
Thumbs.db
*.tmp
*~

## 助手运行时
__pycache__/
*.pyc
.venv/
venv/

## 大二进制（需要时走 Git LFS）
*.dwg filter=lfs diff=lfs merge=lfs -text
*.psd filter=lfs diff=lfs merge=lfs -text
*.skp filter=lfs diff=lfs merge=lfs -text

## 但保留 05_output/ 里的一切 —— 这里是真相，必需 commit
```

## 十、常见问题

- **Q：甲方只发了 chat，没有 brief.docx 怎么办？**
    
    A：允许。`brief.*` `required: false`；助手会标「推荐」不阻塞。S0 仅从 chat 抽字段，其余进 pending_questions。
    
- **Q：必须要 DWG 才能走全流程吗？**
    
    A：不需要。没有 DWG 只会阻塞 S2、以及 S3b 容积率/强排校核；S0/S1/S3a/S4 仍可跑。
    
- **Q：区位图为什么是唯一全局门槛？**
    
    A：因为它是 S0 和 S1 判断场地位置的最小共同源。实在没有区位图时，应先补区位图，不建议用空地址绕过门槛。
    

---

<aside>
🔗

**下一步**：`AGENTS.md` 会让 agent 启动时自动读取本文件、`_schema/record.schema.md` 和 S0 skill。

</aside>

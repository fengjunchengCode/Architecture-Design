\~/Architecture/projects/        ← git root

├── .git/

├── README.md

├── CLAUDE.md                   ← Claude Code 系统提示

├── \_schema/

│   ├── record.schema.md        ← record.md 字段权威定义

│   └── folder.convention.md    ← 文件夹/文件命名约定

├── \_indicators/                ← 指标库本地缓存

│   └── indicators.json

└── {项目代号}/

&#x20;   ├── 01\_briefing/  02\_site/  03\_references/  04\_chat/

&#x20;   └── 05\_output/

&#x20;       ├── record.md           ← 真相文件

&#x20;       ├── parse\_log.md

&#x20;       └── 汇报文档.md（S9 产出）





projects/{项目代号}/

├── 01\_briefing/        ← 需求类

│   ├── 需求文档.{docx|pdf}

│   └── 补充说明\_\*.{txt|jpg|png}

├── 02\_site/            ← 场地类

│   ├── 区位图/         ← 多张区位图

│   ├── 地形图/         ← DWG + PDF 导出等

│   └── 现场照片/       ← 多张踏勘照片

├── 03\_references/      ← 甲方提供的参考案例

└── 04\_chat/            ← 甲方聊天记录导出

&#x20;   └── \*.{txt|html|md}


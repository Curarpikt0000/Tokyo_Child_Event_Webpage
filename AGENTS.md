# Tokyo Child Event Webpage — 项目级约束 (AGENTS.md)

> 本文件是项目的架构红线，所有 AI Agent 和开发者必须遵守。
> 与全局规则 general-global-rule.md 配合使用，本文件定义项目特有约束。
> 最后更新：2026-05-17

---

## §1 项目路径

- **项目根目录**：`/Users/chaojin/Antigravity Projects/Tokyo_Child_Event_Webpage/`
- **GitHub Pages 根目录**：`docs/`（所有静态文件必须在此目录下）
- **数据文件目录**：`docs/data/`（index.json / meta.json / events/YYYY-MM-DD.json）
- **任务文件目录**：`tasks/`（todo.md / lessons.md）

---

## §2 架构红线（禁止违反）

### 数据层
- **禁止**将 docs/data/ 以外的路径作为数据输出目标
- **禁止**单文件包含超过1个月的完整活动数据（必须按日分文件）
- **必须**维护 index.json（轻量索引）和 meta.json（元数据）的同步更新
- **官网数据优先**：同一活动在多个来源出现时，official 来源的数据覆盖聚合平台数据

### 爬虫层
- **必须**在每次请求前检查 robots.txt（通过 base.py 的 BaseScraper 类）
- **必须**保持 ≥2秒的请求间隔（`REQUEST_DELAY` 从 config.py 读取）
- **禁止**使用未在 config.py 中注册的 URL 或数据源
- **必须**将爬虫错误隔离：单个爬虫失败不能阻止其他爬虫运行

### LLM 层
- **禁止**硬编码模型 ID（从 config.py 的 `PRIMARY_MODEL` / `FALLBACK_MODEL` 读取）
- **必须**串行执行 LLM 批次（batch_size=30，依照全局 §4.7）
- **级联回退顺序**：Gemini Flash → Gemini Pro → AI Studio（依照全局 §3.3）
- **必须**在摘要 prompt 中内嵌 humanizer-zh 写作规范

### 前端层
- **禁止**裸露渲染 Markdown 字符串（必须通过 marked.js，依照全局 §4.9）
- **必须**使用 CSS 变量系统（`--color-outdoor` 等，定义在 style.css :root）
- **禁止**在 JS 文件中硬编码颜色值（必须引用 CSS 变量）
- **必须**保持移动端响应式（1列/2列/3列断点）

---

## §3 目录结构约定

```
Tokyo_Child_Event_Webpage/
├── AGENTS.md               ← 本文件
├── config.py               ← 所有配置（唯一可信来源）
├── main.py                 ← 唯一主入口
├── requirements.txt
├── .gitignore
├── .github/
│   └── workflows/
│       └── daily_update.yml
├── scraper/
│   ├── __init__.py
│   ├── base.py             ← 所有爬虫必须继承 BaseScraper
│   ├── wards/              ← 各区官网爬虫（一区一文件）
│   │   ├── __init__.py
│   │   ├── shibuya.py
│   │   ├── shinjuku.py
│   │   └── nerima.py
│   └── supplementary/     ← 补充来源
│       ├── __init__.py
│       └── ikoyo.py
├── processor/
│   ├── __init__.py
│   ├── cleaner.py          ← 清洗 + 去重
│   └── llm_classifier.py  ← Gemini Flash 分类
├── generator/
│   ├── __init__.py
│   ├── json_writer.py      ← 写出 index.json + 日期文件
│   └── meta_writer.py     ← 写出 meta.json
├── docs/                   ← GitHub Pages 根目录
│   ├── index.html
│   ├── data/
│   │   ├── index.json
│   │   ├── meta.json
│   │   └── events/
│   └── assets/
│       ├── style.css
│       ├── app.js
│       └── calendar.js
└── tasks/
    ├── todo.md
    └── lessons.md
```

---

## §4 数据 Schema（字段规范）

### index.json 事件条目（轻量）
```python
{
    "id": str,          # "evt_YYYYMMDD_NNN"
    "date": str,        # "YYYY-MM-DD"
    "title_zh": str,    # 中文标题（50字以内）
    "type": str,        # outdoor/arts/science/sports/culture/nature/museum/performance
    "ward": str,        # "渋谷区"（日文区名）
    "age_min": int,     # 最低适宜年龄（0-10）
    "age_max": int,     # 最高适宜年龄（0-10）
    "free": bool,       # 是否免费
    "indoor": bool,     # 是否室内
}
```

### events/YYYY-MM-DD.json 事件条目（完整）
在轻量字段基础上，额外包含：
```python
{
    "title_ja": str,         # 日文原标题
    "venue": str,            # 场馆名称（日文）
    "address": str,          # 详细地址（日文）
    "time_start": str,       # "HH:MM"
    "time_end": str,         # "HH:MM" 或 null
    "price": int,            # 价格（日元），0表示免费
    "summary_zh": str,       # AI生成中文摘要（humanizer-zh处理后）
    "image_url": str,        # 活动图片URL（或 null）
    "source_url": str,       # 原始链接（必须提供）
    "source_name": str,      # "渋谷区公式" / "いこーよ" 等
    "source_type": str,      # "official" / "supplementary"
    "ai_score": float,       # 1.0-5.0（AI推荐评分）
    "ai_tags": list[str],    # ["免费", "室内", "亲子", "雨天OK"]
    "rain_ok": bool,         # 下雨天是否可参加
}
```

---

## §5 禁用库列表

- **禁止**使用 `scrapy`（过重，与本项目轻量原则不符）
- **禁止**使用 `selenium`（用 Playwright 替代）
- **禁止**使用 `pandas`（数据量不需要，增加依赖负担）
- **禁止**使用任何需要数据库的库（SQLite/PostgreSQL 等）

---

## §6 活动类型枚举（前后端统一）

```python
ACTIVITY_TYPES = [
    "outdoor",      # 户外活动（绿色 #4CAF50）
    "arts",         # 手工艺术（紫色 #9C27B0）
    "science",      # 科学体验（蓝色 #2196F3）
    "sports",       # 运动竞技（橙色 #FF9800）
    "culture",      # 文化节庆（粉色 #E91E63）
    "nature",       # 自然体验（青色 #00BCD4）
    "museum",       # 博物馆展览（珊瑚 #FF5722）
    "performance",  # 表演演出（黄色 #FFC107）
]
```

---

## §7 Skill 集成规范

| Skill | 触发时机 | 负责人 |
|---|---|---|
| agent-browser | 写每个区爬虫前验证页面结构；部署后验证前端 | Agent |
| frontend-design | 实现 style.css 和 app.js 时遵循 CSS token 系统 | Agent |
| humanizer-zh | llm_classifier.py 摘要 prompt 内嵌人性化规范 | Agent |
| requesting-code-review | 每个主要模块完成后（后端/前端各一次）| Agent |
| brainstorming | 新功能设计前 | Agent |

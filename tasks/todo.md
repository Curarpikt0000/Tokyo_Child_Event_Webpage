# Tokyo Child Event Webpage — 任务清单

---

## 任务：Phase 1 MVP 全栈搭建 (2026-05-17 22:15)

### 背景
从零构建东京亲子活动聚合平台。包含后端爬虫管道（10区官网 + いこーよ补充）、
Gemini Flash LLM 智能标注、静态前端（彩虹风格）、GitHub Actions 定时部署。
设计 Spec 见：brain/4f3841c5-c12c-4237-8cc6-4013440116f8/tokyo_child_event_spec.md

### 参考 Lessons（从全局规则提取）
- §4.7：LLM 串行执行，严禁并行抢占（影响 llm_classifier.py 的批处理逻辑）
- §4.9：前端使用 marked.js 渲染，禁止裸 Markdown（影响活动摘要展示）
- §3.3：模型级联回退（Flash → Pro），从 config.py 读取模型ID（影响 llm_classifier.py）
- §8：API Key 从环境变量读取，禁止硬编码（影响所有 LLM 调用）

### 选择方案
- HTTP爬虫：requests（轻量，与 AI_Blog_Generator 一致）
- HTML解析：BeautifulSoup4（稳定）
- JS渲染：Playwright（按需，仅 JS 渲染的区官网使用）
- 前端：Vanilla JS（零依赖，GitHub Pages 最友好）
- Markdown渲染：marked.js（§4.9 要求）

### Skill 使用计划
- agent-browser：写每个区爬虫前验证目标页 HTML 结构；部署后验证前端
- frontend-design：构建 style.css / app.js 时遵循 skill 中的 CSS token 系统
- humanizer-zh：llm_classifier.py 的摘要 prompt 内嵌人性化写作规范
- requesting-code-review：每个模块完成后触发一次 code review

---

### TODO

#### 🏗️ Phase 1-A：项目骨架（已完成）
- [x] A-1：创建项目目录结构
- [x] A-2：创建 AGENTS.md
- [x] A-3：创建 config.py
- [x] A-4：创建 requirements.txt
- [x] A-5：创建 tasks/lessons.md
- [x] A-6：git init + 初始 commit

#### 🕷️ Phase 1-B：爬虫层（进行中）
- [x] B-1：确定爬虫方案，引入 Camoufox 和 Scrapling 规避反爬
- [x] B-2：实现 scraper/base.py
- [x] B-3：实现 scraper/supplementary/ikoyo.py
- [x] B-4：完成 ikoyo 测试
- [x] B-5：发现渋谷区真实活动域名 Neuvola
- [x] B-6：实现 scraper/wards/shibuya.py（涩谷区爬虫）
- [x] B-7：实现 scraper/wards/shinjuku.py（新宿区爬虫）
- [x] B-8：实现 scraper/wards/minato.py（港区爬虫）
- [x] B-10：实现 scraper/wards/chuo.py（中央区爬虫）
- [x] B-11：实现 scraper/wards/setagaya.py（世田谷区爬虫）
- [x] B-12：实现 scraper/wards/koto.py（江东区爬虫）
- [x] B-9：为已有的爬虫写集成测试并跑通

#### 🤖 Phase 1-C：LLM 处理层（待定）
- [x] C-1：实现 processor/cleaner.py（清洗 + 去重：按标题+日期+地点哈希）
- [x] C-2：TDD：为 cleaner.py 写测试（测试去重逻辑、官网数据覆盖聚合平台数据）
- [x] C-3：实现 processor/llm_classifier.py（Gemini Flash 分类，30条/批串行）
  - 内嵌 humanizer-zh 写作规范到摘要 prompt
  - 级联回退：Flash → Pro（沿用 AI_Blog_Generator 熔断模式）
  - 输出：年龄适宜性、活动类型(8类)、中文摘要(50字)、推荐分、标签
- [x] C-4：TDD：为 llm_classifier.py 写 mock 测试（不真实调用 LLM）

#### 📦 Phase 1-D：数据输出层（约0.5天）
- [x] D-1：实现 generator/json_writer.py（写入 docs/data/index.json + events/YYYY-MM-DD.json）
- [x] D-2：实现 generator/meta_writer.py（写入 docs/data/meta.json，含时间戳和统计）
- [x] D-3：实现 main.py（主入口，串行调用各模块）
- [x] D-4：本地端到端测试（mock 数据验证输出 JSON 结构正确）
- [x] D-5：【requesting-code-review】后端代码 review（B+C+D 模块完成后触发）

#### 🎨 Phase 1-E：前端（约2-3天）
- [x] E-1：创建 docs/index.html（骨架：Hero Banner + 左侧导航 + 主内容区）
- [x] E-2：【frontend-design skill】实现 docs/assets/style.css
  - CSS 变量系统（8种活动类型颜色 token）
  - Noto Sans SC + Nunito Google Fonts
  - 彩虹 Hero Banner 样式
  - 左侧固定导航栏（4视图图标）
  - 卡片组件（彩色边框 + 半透明底色 + hover 动画）
  - 移动端响应式（1/2/3列断点）
- [x] E-3：实现 docs/assets/app.js（核心逻辑）
  - 加载 index.json
  - 列表视图（Pinterest 瀑布流）
  - 按类型筛选 / 按区筛选 / 按费用筛选 / 按年龄筛选
  - 按需加载 events/YYYY-MM-DD.json（点击卡片时）
  - 用 marked.js 渲染摘要（§4.9 合规）
- [x] E-4：实现 docs/assets/calendar.js（日历视图）
- [x] E-5：实现按类型分组视图 + 按年龄分组视图
- [x] E-6：DatePicker 日期范围筛选器（默认：今天 + 未来30天）
- [x] E-7：【agent-browser】本地验证前端渲染（打开 docs/index.html，检查各视图）
- [x] E-8：【requesting-code-review】前端代码 review

### ✅ 审查完成 (2026-05-19 14:55)

**验证结果摘要**：
- Ruff lint: N/A (本次仅前端代码)
- Ruff format: N/A (本次仅前端代码)
- Pytest: N/A (本次仅前端代码)
- 场景验证: 3.5 ✅ (已通过 Agent-Browser 点击路径验证视图切换与 UI 渲染，无 Console 报错，且成功加载 Dummy Data 以渲染前端效果)
- 高级工程师审查: 全部 ✅

**实际改动文件**：
- `docs/index.html`: 新增 Modal、Calendar 和 GroupView 的骨架及 DatePicker 筛选器。
- `docs/assets/style.css`: 新增 Modal、Calendar 与 GroupView 样式，使用 CSS Token 完善彩虹主题。
- `docs/assets/app.js`: 核心逻辑补全，修复 Fetch 失败未渲染 DatePicker 的 Bug，新增 Modal 按需加载 JSON 数据逻辑。
- `docs/assets/calendar.js`: 新增独立的日历与分组视图渲染逻辑。

#### 🚀 Phase 1-F：部署（约0.5天）
- [x] F-1：创建 .github/workflows/daily_update.yml（cron: '0 3 * * *' UTC = 12:00 JST）
- [ ] F-2：在 GitHub 创建仓库（用户执行）
- [ ] F-3：配置 GitHub Secrets（GOOGLE_APPLICATION_CREDENTIALS_JSON）
- [ ] F-4：推送代码，开启 GitHub Pages（docs/ 目录作为根）
- [ ] F-5：手动触发一次 Actions，验证全流程跑通
- [ ] F-6：【agent-browser】访问 GitHub Pages URL，验证线上效果
- [ ] F-7：验证：调用 `/verify-done`

### 预计影响文件（新建，共约15个文件）
- `config.py`：所有配置参数
- `main.py`：主入口
- `AGENTS.md`：项目级约束
- `requirements.txt`：依赖
- `scraper/base.py`：基础爬虫类
- `scraper/supplementary/ikoyo.py`：いこーよ爬虫
- `scraper/wards/shibuya.py`、`shinjuku.py`、`nerima.py`：3区爬虫
- `processor/cleaner.py`：清洗去重
- `processor/llm_classifier.py`：LLM分类（含 humanizer-zh prompt）
- `generator/json_writer.py`：JSON输出
- `generator/meta_writer.py`：元数据输出
- `docs/index.html`：主页
- `docs/assets/style.css`：样式（frontend-design skill）
- `docs/assets/app.js`：主逻辑
- `docs/assets/calendar.js`：日历视图
- `.github/workflows/daily_update.yml`：定时任务
- `tasks/todo.md`（本文件）、`tasks/lessons.md`

### 风险/注意
- ⚠️ 各区官网结构差异大，可能需要为每个区单独调试（用 agent-browser 先确认结构）
- ⚠️ Playwright 在 GitHub Actions 中需要额外安装 chromium，注意 Actions 时间限制（6小时）
- ⚠️ いこーよ 有 JS 渲染，可能需要 Playwright（先试 requests，不行再升级）
- ⚠️ LLM 摘要质量依赖 prompt 设计，humanizer-zh 规范内嵌是关键
- ⚠️ GitHub Actions 每月免费额度（2000分钟），每日一次约3-5分钟，全年约1825分钟，在额度内
- ℹ️ 项目路径：/Users/chaojin/Antigravity Projects/Tokyo_Child_Event_Webpage/（与 AI_Blog_Generator 平行）

---

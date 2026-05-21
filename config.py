"""
文件功能：项目全局配置文件，统一管理所有可配置参数
实现方式：Python 常量 + 环境变量读取 + 动态模型发现（utils/model_discovery.py）
主要模块：LLM配置、爬虫配置、数据源配置、输出路径配置、get_models() 动态寻址
输入输出：被所有模块 import，无输入，输出配置常量
依赖关系：python-dotenv（环境变量）、os（系统路径）、utils.model_discovery
创建日期：2026-05-17
更新日期：2026-05-18（接入动态模型发现，禁止硬编码模型 ID，依照全局规则 §3.1 §3.2）
"""

import os
from pathlib import Path

# ============================================================
# 路径配置
# ============================================================

# 项目根目录（本文件所在目录）
PROJECT_ROOT = Path(__file__).parent

# 数据输出目录（GitHub Pages 根目录下）
DOCS_DIR = PROJECT_ROOT / "docs"
DATA_DIR = DOCS_DIR / "data"
EVENTS_DIR = DATA_DIR / "events"

# 确保输出目录存在
DATA_DIR.mkdir(parents=True, exist_ok=True)
EVENTS_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# LLM 模型配置（禁止在其他文件硬编码模型 ID，必须从此处读取）
# 依照全局规则 §3.1：动态发现优先，此处为静态兜底配置
# ============================================================

# Vertex AI 配置（主力，使用 ADC 认证，无需 JSON Key）
# 认证方式：gcloud auth application-default login（已配置）
VERTEX_AI_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "wechatgenerator-494007")
VERTEX_AI_LOCATION = os.environ.get("VERTEX_AI_LOCATION", "us-central1")

# AI Studio 兜底（Vertex AI 整体不可用时，依照全局规则 §3.3）
AI_STUDIO_API_KEY = os.environ.get("GEMINI_API_KEY", os.environ.get("GOOGLE_AI_STUDIO_KEY", ""))

# ---- 动态模型发现（依照全局规则 §3.1 §3.2：禁止硬编码模型 ID）----
# 调用 utils/model_discovery.py 在运行时枚举真实可用模型并打分
# 结果缓存在 model_discovery._cache，不会重复调用 API
_models_cache: tuple[str, str] | None = None


def get_models() -> tuple[str, str]:
    """
    功能描述：懒初始化动态模型发现，返回 (primary_model, fallback_model)
    实现逻辑：首次调用时执行 discover_best_models，后续从缓存读取
    返回值：tuple[str, str] - (主力模型ID, 回退模型ID)
    """
    global _models_cache
    if _models_cache is None:
        # 延迟导入，避免循环依赖
        from utils.model_discovery import discover_best_models
        _models_cache = discover_best_models(
            project=VERTEX_AI_PROJECT,
            location=VERTEX_AI_LOCATION,
            api_key=AI_STUDIO_API_KEY,
        )
    return _models_cache


# LLM 批处理配置（依照全局规则 §4.7：严禁并行，必须串行）
LLM_BATCH_SIZE = 30  # 每批最多 30 条活动
LLM_REQUEST_DELAY = 1.0  # 批次间延迟（秒）

# ============================================================
# 爬虫配置
# ============================================================

# 请求间隔（秒），必须 ≥ 2，防止过载目标站点
REQUEST_DELAY = 2.5

# 请求超时（秒）
REQUEST_TIMEOUT = 30

# User-Agent（标明 bot 身份，合规爬取）
USER_AGENT = (
    "TokyoChildEventBot/1.0 "
    "(Educational aggregator for children events; "
    "Contact: your-email@example.com)"
)

# 最大重试次数
MAX_RETRIES = 3

# ============================================================
# 数据时间范围配置
# ============================================================

# 保留过去天数（过去7天的活动仍展示）
DAYS_PAST = 7

# 保留未来天数（未来3个月的活动）
DAYS_FUTURE = 90

# 前端默认展示范围（今天 + 未来30天）
DEFAULT_DISPLAY_DAYS = 30

# ============================================================
# 数据源配置 — Priority 1：区官方网站
# 覆盖10个主要区，按爬取优先级排序
# ============================================================

WARD_SOURCES = {
    "渋谷区": {
        "name_en": "shibuya",
        "base_url": "https://shibuya-city-neuvola.tokyo",
        "events_path": "/event/",
        "scraper": "scraper.wards.shibuya",
        "enabled": True,
        "js_required": True,

    },
    "新宿区": {
        "name_en": "shinjuku",
        "base_url": "https://www.city.shinjuku.lg.jp",
        "events_path": "/kodomo/",
        "scraper": "scraper.wards.shinjuku",
        "enabled": True,
        "js_required": False,
    },
    "練馬区": {
        "name_en": "nerima",
        "base_url": "https://www.city.nerima.tokyo.jp",
        "events_path": "/kosodateshien/",
        "scraper": "scraper.wards.nerima",
        "enabled": False,
        "js_required": False,
    },
    "世田谷区": {
        "name_en": "setagaya",
        "base_url": "https://www.city.setagaya.lg.jp",
        "events_path": "/mokuji/kosodate/",
        "scraper": "scraper.wards.setagaya",
        "enabled": True,
        "js_required": False,
    },
    "港区": {
        "name_en": "minato",
        "base_url": "https://www.city.minato.tokyo.jp",
        "events_path": "/kusei/koho/event/index.html",
        "scraper": "scraper.wards.minato",
        "enabled": True,
        "js_required": True,   # 需要 CamoFox 渲染
    },
    "江東区": {
        "name_en": "koto",
        "base_url": "https://www.city.koto.lg.jp",
        "events_path": "/kosodate/",
        "scraper": "scraper.wards.koto",
        "enabled": True,
        "js_required": False,
    },
    "中央区": {
        "name_en": "chuo",
        "base_url": "https://www.city.chuo.lg.jp",
        "events_path": "/a0022/kosodate/akachan_tengoku/event.html",
        "scraper": "scraper.wards.chuo",
        "enabled": True,
        "js_required": False,
    },
    "墨田区": {
        "name_en": "sumida",
        "base_url": "https://www.city.sumida.lg.jp",
        "events_path": "/kosodate/",
        "scraper": "scraper.wards.sumida",
        "enabled": False,  # Phase 2
        "js_required": False,
    },
    "文京区": {
        "name_en": "bunkyo",
        "base_url": "https://www.city.bunkyo.lg.jp",
        "events_path": "/kosodate/",
        "scraper": "scraper.wards.bunkyo",
        "enabled": False,  # Phase 2
        "js_required": False,
    },
    "台東区": {
        "name_en": "taito",
        "base_url": "https://www.city.taito.lg.jp",
        "events_path": "/kosodate/",
        "scraper": "scraper.wards.taito",
        "enabled": False,  # Phase 2
        "js_required": False,
    },
    "品川区": {
        "name_en": "shinagawa",
        "base_url": "https://www.city.shinagawa.lg.jp",
        "events_path": "/kosodate/",
        "scraper": "scraper.wards.shinagawa",
        "enabled": False,  # Phase 2
        "js_required": False,
    },
}

# ============================================================
# 数据源配置 — Priority 2：补充聚合平台
# ============================================================

SUPPLEMENTARY_SOURCES = {
    "ikoyo": {
        "name": "いこーよ",
        "base_url": "https://iko-yo.net",
        "scraper": "scraper.supplementary.ikoyo",
        "enabled": True,
        "source_type": "supplementary",
    },
    "walkerplus": {
        "name": "ウォーカープラス",
        "base_url": "https://event.walkerplus.com",
        "scraper": "scraper.supplementary.walkerplus",
        "enabled": True,
        "source_type": "supplementary",
    },
    "jalan": {
        "name": "じゃらん",
        "base_url": "https://www.jalan.net",
        "scraper": "scraper.supplementary.jalan",
        "enabled": True,
        "source_type": "supplementary",
    },
    "enjoytokyo": {
        "name": "レッツエンジョイ東京",
        "base_url": "https://www.enjoytokyo.jp",
        "list_path": "/feature/kids/event/",
        "scraper": "scraper.supplementary.enjoytokyo",
        "enabled": True,
        "source_type": "supplementary",
        # 覆盖港区芋浦祭り、Hills Spa、台場等东京全域亲子活动
    },
    "plarail": {
        "name": "プラレール博 in TOKYO",
        "base_url": "https://plarail-tokyo.com",
        "scraper": "scraper.supplementary.plarail",
        "enabled": True,
        "source_type": "supplementary",
        # 年度展覧型，例年 GW 前后在有明GYM-EX開催，2026年已结束。下居来年度公布前返回空列表
    },
}

# ============================================================
# 活动类型枚举（前后端统一，禁止在其他文件重复定义）
# ============================================================

ACTIVITY_TYPES = [
    "outdoor",      # 户外活动
    "arts",         # 手工艺术
    "science",      # 科学体验
    "sports",       # 运动竞技
    "culture",      # 文化节庆
    "nature",       # 自然体验
    "museum",       # 博物馆展览
    "performance",  # 表演演出
]

# 活动类型中文标签（供 LLM prompt 使用）
ACTIVITY_TYPE_LABELS_ZH = {
    "outdoor":     "户外活动",
    "arts":        "手工艺术",
    "science":     "科学体验",
    "sports":      "运动竞技",
    "culture":     "文化节庆",
    "nature":      "自然体验",
    "museum":      "博物馆展览",
    "performance": "表演演出",
}

# ============================================================
# AI 标签池（供 LLM 从中选择，前端筛选使用）
# ============================================================

AI_TAGS_POOL = [
    "免费", "付费", "室内", "户外", "雨天OK",
    "婴幼儿友好", "需提前预约", "无需预约",
    "亲子互动", "体验型", "观赏型",
    "交通便利", "公园附近",
]

# ============================================================
# 年龄段定义（前后端统一）
# ============================================================

AGE_GROUPS = [
    {"key": "baby",   "label": "👶 0-2岁", "min": 0, "max": 2},
    {"key": "toddler","label": "🧒 3-5岁", "min": 3, "max": 5},
    {"key": "child",  "label": "🧑 6-10岁","min": 6, "max": 10},
]

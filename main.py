"""
文件功能：项目主入口，串行调度爬取→清洗→LLM分类→输出全流程
实现方式：按模块顺序调用，异常隔离，日志记录，动态查找继承自 BaseScraper 的类进行实例化。
主要模块：run_pipeline() 主函数
输入输出：无输入；输出 docs/data/ 下的 JSON 文件
依赖关系：config, scraper, processor, generator
创建日期：2026-05-17
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
import importlib

import config
from scraper.base import BaseScraper
from generator.json_writer import JSONWriter
from generator.meta_writer import MetaWriter
from processor.cleaner import Cleaner
from processor.llm_classifier import LLMClassifier

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("main")


def load_scrapers() -> list:
    """
    功能描述：动态加载所有已启用的爬虫模块
    实现逻辑：
        1. 遍历 config.WARD_SOURCES（区官网）与 config.SUPPLEMENTARY_SOURCES（补充来源）
        2. 仅加载 enabled=True 的爬虫
        3. 动态检索模块内继承自 BaseScraper 的具体子类进行实例化
    参数说明：无
    返回值：已实例化的爬虫列表
    """
    scrapers = []

    # 加载区官网爬虫（Priority 1）
    for ward_name, ward_config in config.WARD_SOURCES.items():
        if not ward_config.get("enabled", False):
            continue
        try:
            module = importlib.import_module(ward_config["scraper"])
            scraper_class = None
            # 动态查找继承自 BaseScraper 的具体类
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and issubclass(attr, BaseScraper) and attr is not BaseScraper:
                    scraper_class = attr
                    break
            
            if scraper_class:
                scrapers.append(scraper_class(ward_config))
                logger.info(f"已加载官网爬虫：{ward_name} ({scraper_class.__name__})")
            else:
                logger.warning(f"模块中未找到有效的 BaseScraper 子类: {ward_name}")
        except Exception as e:
            logger.warning(f"官网爬虫加载失败，跳过：{ward_name} — {e}")

    # 加载补充来源爬虫（Priority 2）
    for source_key, source_config in config.SUPPLEMENTARY_SOURCES.items():
        if not source_config.get("enabled", False):
            continue
        try:
            module = importlib.import_module(source_config["scraper"])
            scraper_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and issubclass(attr, BaseScraper) and attr is not BaseScraper:
                    scraper_class = attr
                    break
                    
            if scraper_class:
                scrapers.append(scraper_class(source_config))
                logger.info(f"已加载补充爬虫：{source_config['name']} ({scraper_class.__name__})")
            else:
                logger.warning(f"模块中未找到有效的 BaseScraper 子类: {source_key}")
        except Exception as e:
            logger.warning(f"补充爬虫加载失败，跳过：{source_key} — {e}")

    return scrapers


def run_pipeline() -> None:
    """
    功能描述：执行完整的数据采集→处理→输出管道
    实现逻辑：
        1. 加载所有已启用的爬虫
        2. 串行执行每个爬虫（单个失败不阻断整体）
        3. 合并原始数据，执行清洗和去重
        4. 串行 LLM 分类（30条/批）
        5. 输出 index.json / events/YYYY-MM-DD.json / meta.json
    参数说明：无
    返回值：无
    异常：所有子步骤异常均被捕获并记录，不向上抛出
    """
    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info("Tokyo Child Event Pipeline 启动")
    logger.info(f"开始时间：{start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    # ── 步骤 1：爬取原始数据 ──────────────────────────────
    logger.info("[步骤 1/5] 加载爬虫模块...")
    scrapers = load_scrapers()
    logger.info(f"已启用爬虫数量：{len(scrapers)}")

    all_raw_events = []

    logger.info("[步骤 2/5] 串行执行爬虫...")
    for scraper in scrapers:
        try:
            logger.info(f"  → 爬取：{scraper.name}")
            raw_events = scraper.fetch()
            all_raw_events.extend(raw_events)
            logger.info(f"  ✓ 获取 {len(raw_events)} 条原始记录")
        except Exception as e:
            # 单个爬虫失败不阻断整体（依照 AGENTS.md §2）
            logger.error(f"  ✗ 爬虫失败，已跳过：{scraper.name} — {e}")

    logger.info(f"爬取完成：共 {len(all_raw_events)} 条原始记录")

    if not all_raw_events:
        logger.warning("所有爬虫均无数据，退出")
        return

    # ── 步骤 2：清洗和去重 ───────────────────────────────
    logger.info("[步骤 3/5] 清洗和去重...")
    clean_events = Cleaner.deduplicate(all_raw_events)
    logger.info(f"清洗完成：{len(all_raw_events)} → {len(clean_events)} 条（去重 {len(all_raw_events) - len(clean_events)} 条）")

    # ── 步骤 3：LLM 分类（串行，30条/批）────────────────
    logger.info("[步骤 4/5] LLM 分类（串行批处理）...")
    classifier = LLMClassifier()
    classified_events = classifier.process_all(clean_events)
    logger.info(f"分类完成：{len(classified_events)} 条")

    # ── 步骤 4：输出 JSON 文件 ───────────────────────────
    logger.info("[步骤 5/5] 写出 JSON 文件...")
    writer = JSONWriter()
    writer.write(classified_events)

    meta_writer = MetaWriter()
    meta_writer.write()

    # ── 完成 ─────────────────────────────────────────────
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    logger.info("=" * 60)
    logger.info(f"Pipeline 完成！耗时：{duration:.1f}秒")
    logger.info(f"输出目录：{config.DATA_DIR}")
    logger.info("=" * 60)


if __name__ == "__main__":
    run_pipeline()

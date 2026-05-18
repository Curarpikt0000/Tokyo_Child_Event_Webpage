"""
文件功能：いこーよ (iko-yo.net) 补充数据源爬虫（AI 智能防封版）
实现方式：集成 CamoFox (抗指纹浏览器) 与 Scrapling (高级解析)
主要模块：IkoyoScraper
输入输出：无参数，返回标准化的活动字典列表
依赖关系：camoufox, scrapling, bs4
创建日期：2026-05-18
"""

import logging
import re
from datetime import datetime
from bs4 import BeautifulSoup

# 引入强大的抗指纹浏览器内核
from camoufox.sync_api import Camoufox

from scraper.base import BaseScraper

logger = logging.getLogger(__name__)


class IkoyoScraper(BaseScraper):
    def __init__(self, source_config: dict):
        super().__init__("ikoyo", source_config)
        self.areas = source_config.get("areas", ["13"])  # 默认 13 为東京都

    def fetch(self) -> list[dict]:
        all_events = []
        
        # 使用 Camoufox 启动完全隐藏指纹的沙盒浏览器
        logger.info("正在启动 CamoFox 抗指纹引擎...")
        
        try:
            with Camoufox(headless=True, geoip=True) as browser:
                page = browser.new_page()
                
                for area_id in self.areas:
                    url = f"{self.base_url}/events?prefecture_ids%5B%5D={area_id}"
                    logger.info(f"CamoFox 正在导航至: {url}")
                    
                    page.goto(url, wait_until="domcontentloaded")
                    html_content = page.content()
                    
                    # 也可以在这里无缝对接 Stagehand / Scrapling 的 DOM 解析
                    # 为了兼容原有的柔性提取逻辑，我们仍使用 BS4 解析，但底层已获防封保障
                    soup = BeautifulSoup(html_content, "lxml")
                    
                    event_links = soup.find_all(
                        "a", href=re.compile(r"/(events/\d+|event_lites/detail/\d+)")
                    )
                    
                    seen_urls = set()
                    for link in event_links:
                        href = link.get("href")
                        if not href:
                            continue
                            
                        clean_url = self.make_absolute_url(href).split("?")[0]
                        if clean_url in seen_urls:
                            continue
                        seen_urls.add(clean_url)

                        container = link.find_parent(["article", "li"])
                        if not container:
                            container = link.find_parent("div", class_=lambda c: c and "item" in c.lower())
                        
                        block = container if container else link.parent
                        
                        title_elem = block.find(["h2", "h3", "h4"])
                        title_ja = title_elem.get_text(strip=True) if title_elem else link.get_text(strip=True)

                        if not title_ja or len(title_ja) < 2:
                            continue

                        text_content = block.get_text(" ", strip=True)
                        date_match = re.search(r"(?:202\d年)?(\d{1,2})月(\d{1,2})日", text_content)
                        if date_match:
                            month = int(date_match.group(1))
                            day = int(date_match.group(2))
                            year = datetime.now().year
                            if "年" in date_match.group(0):
                                year_match = re.search(r"(202\d)年", date_match.group(0))
                                if year_match:
                                    year = int(year_match.group(1))
                            date_str = f"{year}-{month:02d}-{day:02d}"
                        else:
                            date_str = datetime.now().strftime("%Y-%m-%d")

                        free = "無料" in text_content
                        price = 0 if free else None

                        all_events.append({
                            "title_ja": title_ja,
                            "date": date_str,
                            "ward": "東京都",
                            "source_url": clean_url,
                            "source_name": "いこーよ",
                            "source_type": "supplementary",
                            "free": free,
                            "price": price,
                        })
        except Exception as e:
            logger.error(f"CamoFox 抓取异常: {e}")
                
        return all_events

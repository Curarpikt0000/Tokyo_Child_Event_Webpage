"""
文件功能：江东区官网 (子育て) 爬虫
实现方式：继承 BaseScraper，使用 requests + BeautifulSoup 抓取并解析 HTML。
主要模块：KotoScraper
输入输出：无参数，返回活动字典列表
依赖关系：bs4, scraper.base
"""

import logging
import re
from datetime import datetime
from bs4 import BeautifulSoup

from scraper.base import BaseScraper

logger = logging.getLogger(__name__)


class KotoScraper(BaseScraper):
    def __init__(self, source_config: dict):
        super().__init__("江東区", source_config)
        self.events_path = source_config.get("events_path", "/kosodate/")

    def fetch(self) -> list[dict]:
        all_events = []
        url = self.make_absolute_url(self.events_path)
        
        try:
            logger.info(f"正在爬取江东区官网: {url}")
            resp = self.get(url)
            if not resp:
                logger.warning(f"无法获取江东区官网页面: {url}")
                return []
                
            resp.encoding = resp.apparent_encoding
            html = resp.text
            soup = BeautifulSoup(html, "lxml")
            
            main_content = soup.find("main") or soup.find(id="main") or soup.find(id="contents") or soup.find("body")
            
            if not main_content:
                return []

            for a in main_content.find_all("a", href=True):
                href = a["href"]
                text = a.get_text(" ", strip=True)
                
                if not text or len(text) < 4:
                    continue
                    
                date_str = datetime.now().strftime("%Y-%m-%d")
                date_match = re.search(r"(\d{1,2})\s*[月/]\s*(\d{1,2})\s*[日]?", text)
                keyword_match = re.search(r"(講座|イベント|教室|体験|会|まつり|サロン|クラブ)", text)
                
                if not date_match and not keyword_match:
                    if len(text) < 10: 
                        continue
                        
                if date_match:
                    year = datetime.now().year
                    month = int(date_match.group(1))
                    day = int(date_match.group(2))
                    if month < datetime.now().month - 3:
                        year += 1
                    date_str = f"{year}-{month:02d}-{day:02d}"
                    
                free = "有料" not in text and "円" not in text
                
                if "申請" in text or "手続き" in text or "制度" in text or "補助" in text:
                    continue
                    
                all_events.append({
                    "title_ja": text,
                    "date": date_str,
                    "ward": "江東区",
                    "source_url": self.make_absolute_url(href),
                    "source_name": "江東区公式",
                    "source_type": "official",
                    "free": free,
                    "price": 0 if free else None,
                })
                
        except Exception as e:
            logger.error(f"江东区爬虫异常: {e}")
            
        seen = set()
        unique_events = []
        for e in all_events:
            if e["source_url"] not in seen:
                seen.add(e["source_url"])
                unique_events.append(e)
                
        return unique_events

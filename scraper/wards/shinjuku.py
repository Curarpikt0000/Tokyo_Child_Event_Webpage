"""
文件功能：新宿区官网 (子育て・教育) 爬虫
实现方式：继承 BaseScraper，使用 requests + BeautifulSoup 抓取并解析 HTML。
主要模块：ShinjukuScraper
输入输出：无参数，返回活动字典列表
依赖关系：bs4, scraper.base
"""

import logging
import re
from datetime import datetime
from bs4 import BeautifulSoup

from scraper.base import BaseScraper

logger = logging.getLogger(__name__)


class ShinjukuScraper(BaseScraper):
    def __init__(self, source_config: dict):
        super().__init__("新宿区", source_config)
        self.events_path = source_config.get("events_path", "/kodomo/")

    def fetch(self) -> list[dict]:
        all_events = []
        url = self.make_absolute_url(self.events_path)
        
        try:
            logger.info(f"正在爬取新宿区官网: {url}")
            resp = self.get(url)
            if not resp:
                logger.warning(f"无法获取新宿区官网页面: {url}")
                return []
                
            resp.encoding = resp.apparent_encoding
            html = resp.text
            soup = BeautifulSoup(html, "lxml")
            
            # 找到包含事件的区域，通常在 #main 或具有 news/event 类名的模块中
            main_content = soup.find("main") or soup.find(id="main") or soup.find("body")
            
            if not main_content:
                return []

            # 遍历所有的内链
            for a in main_content.find_all("a", href=True):
                href = a["href"]
                text = a.get_text(" ", strip=True)
                
                # 过滤掉太短或无效的链接
                if not text or len(text) < 4:
                    continue
                    
                # 尝试从文本中匹配日期，例如 "5月24日" 或 "5/24"
                date_str = datetime.now().strftime("%Y-%m-%d")
                date_match = re.search(r"(\d{1,2})\s*[月/]\s*(\d{1,2})\s*[日]?", text)
                
                # 新宿区往往会有“講座”或“イベント”等关键字，如果既没有日期也没有关键字，可能只是导航链接
                keyword_match = re.search(r"(講座|イベント|教室|体験|会|まつり)", text)
                
                if not date_match and not keyword_match:
                    # 避免抓取大量无关链接
                    if len(text) < 10: 
                        continue
                        
                if date_match:
                    year = datetime.now().year
                    month = int(date_match.group(1))
                    day = int(date_match.group(2))
                    # 简单处理跨年问题，如果月份小于当前月且当前月是12月，可能是明年的活动
                    if month < datetime.now().month - 3:
                        year += 1
                    date_str = f"{year}-{month:02d}-{day:02d}"
                    
                # 大多数官方子育て活动是免费的
                free = "有料" not in text and "円" not in text
                
                # 去掉一些明显不是活动的链接
                if "申請" in text or "手続き" in text or "制度" in text or "窓口" in text:
                    continue
                    
                all_events.append({
                    "title_ja": text,
                    "date": date_str,
                    "ward": "新宿区",
                    "source_url": self.make_absolute_url(href),
                    "source_name": "新宿区公式",
                    "source_type": "official",
                    "free": free,
                    "price": 0 if free else None,
                })
                
        except Exception as e:
            logger.error(f"新宿区爬虫异常: {e}")
            
        # 根据 URL 去重
        seen = set()
        unique_events = []
        for e in all_events:
            if e["source_url"] not in seen:
                seen.add(e["source_url"])
                unique_events.append(e)
                
        return unique_events

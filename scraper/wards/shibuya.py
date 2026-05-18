"""
文件功能：渋谷区官网 (ネウボラ 子育てポータル) 爬虫
实现方式：使用 CamoFox 获取页面，配合 Scrapling 级自适应解析。
主要模块：ShibuyaScraper
输入输出：无参数，返回活动字典列表
依赖关系：camoufox, bs4
"""

import logging
import re
from datetime import datetime
from bs4 import BeautifulSoup
from camoufox.sync_api import Camoufox
from scraper.base import BaseScraper

logger = logging.getLogger(__name__)

class ShibuyaScraper(BaseScraper):
    def __init__(self, source_config: dict):
        super().__init__("渋谷区", source_config)
        self.events_path = source_config.get("events_path", "/event/")

    def fetch(self) -> list[dict]:
        all_events = []
        url = f"{self.base_url}{self.events_path}"
        
        try:
            with Camoufox(headless=True, geoip=True) as browser:
                page = browser.new_page()
                logger.info(f"CamoFox 正在探索渋谷区ネウボラ: {url}")
                page.goto(url, wait_until="domcontentloaded")
                
                # 等待事件列表加载（假定会有 .event, .list, 或 article）
                page.wait_for_timeout(3000) 
                html = page.content()
                
                # 保存 HTML 用于调试分析
                with open("shibuya_dump.html", "w", encoding="utf-8") as f:
                    f.write(html)
                    
                soup = BeautifulSoup(html, "lxml")
                
                # Neuvola 的 event 页面通常有特定的 article 容器，但为了健壮性我们提取所有含有 "/event/" 或 "detail" 的内链
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    text = a.get_text(" ", strip=True)
                    
                    if not text or len(text) < 4:
                        continue
                        
                    # 确定是详情页链接，Neuvola 的活动详情页都是 /?p=12345 的形式
                    if "?p=" not in href:
                        continue
                        
                    # 避免抓到无关内容，检查是否有类似【coしぶや】这样的活动标识
                    if "【" not in text and len(text) < 10:
                        continue
                        
                    # 从标题或文本中提取日期，通常为 "5/24" 等格式
                    date_str = datetime.now().strftime("%Y-%m-%d")
                    date_match = re.search(r"(\d{1,2})/(\d{1,2})", text)
                    if date_match:
                        year = datetime.now().year
                        date_str = f"{year}-{int(date_match.group(1)):02d}-{int(date_match.group(2)):02d}"
                        
                    # 由于它是子育て专网，绝大多数都是免费的
                    free = "有料" not in text
                        
                    all_events.append({
                        "title_ja": text,
                        "date": date_str,
                        "ward": "渋谷区",
                        "source_url": self.make_absolute_url(href),
                        "source_name": "渋谷区子育てネウボラ",
                        "source_type": "official",
                        "free": free,
                        "price": 0 if free else None,
                    })
                        
        except Exception as e:
            logger.error(f"渋谷区爬虫异常: {e}")
            
        # 根据 URL 去重
        seen = set()
        unique_events = []
        for e in all_events:
            if e["source_url"] not in seen:
                seen.add(e["source_url"])
                unique_events.append(e)
                
        return unique_events

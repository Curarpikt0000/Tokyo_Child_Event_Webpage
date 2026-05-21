"""
文件功能：港区官网 (子育て) 爬虫
实现方式：CamoFox 抓取港区イベントカレンダー（动态页），BeautifulSoup 解析
目标页面：https://www.city.minato.tokyo.jp/kusei/koho/event/index.html
涵盖：港区全域活动（含芝浦、三田、六本木、麻布等地区的子育て/文化活动）
依赖关系：camoufox, bs4, scraper.base
"""

import logging
import re
from datetime import datetime
from bs4 import BeautifulSoup
import time
from camoufox.sync_api import Camoufox

from scraper.base import BaseScraper

logger = logging.getLogger(__name__)


class MinatoScraper(BaseScraper):
    def __init__(self, source_config: dict):
        super().__init__("港区", source_config)
        # 港区イベントカレンダー（全区活动，含子育て/文化）
        self.events_path = source_config.get(
            "events_path", "/kusei/koho/event/index.html"
        )

    def fetch(self) -> list[dict]:
        all_events = []
        url = self.make_absolute_url(self.events_path)

        # 1. robots.txt 校验
        if not self.can_fetch(url):
            logger.warning(f"robots.txt 禁止访问，跳过: {url}")
            return []

        try:
            # 2. 限速延迟控制
            self._throttle()

            logger.info(f"CamoFox 正在抓取港区イベントカレンダー: {url}")
            # 3. 将 geoip=True 修改为 geoip=False 以防止 CI 环境网络受限而超时崩溃
            with Camoufox(headless=True, geoip=False) as browser:
                page = browser.new_page()
                page.goto(url, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)
                html = page.content()
                # 4. 更新请求时间戳，以便在后续再次使用请求时准确限速
                self._last_request_time = time.time()

            # 5. 将 HTML 解析放入主 try 块中以获得强隔离保护
            soup = BeautifulSoup(html, "lxml")

            # 港区カレンダーページ：活动列表在 article / li / dl 结构中
            main = (
                soup.find("div", id="contents")
                or soup.find("main")
                or soup.find(id="main")
                or soup.find("body")
            )
            if not main:
                return []

            # 尝试多种活动容器结构
            event_containers = (
                main.find_all("article")
                or main.find_all("li", class_=re.compile(r"event|item|list"))
                or main.find_all("dl")
            )

            if not event_containers:
                # 降级：找所有含链接的父容器
                event_containers = []
                seen_parents = set()
                for a in main.find_all("a", href=True):
                    text = a.get_text(strip=True)
                    parent = a.find_parent(["li", "div", "article", "dl"])
                    if parent and len(text) > 5 and id(parent) not in seen_parents:
                        seen_parents.add(id(parent))
                        event_containers.append(parent)

            logger.info(f"港区: 发现 {len(event_containers)} 个活动容器")

            for container in event_containers:
                try:
                    a = container.find("a", href=True)
                    if not a:
                        continue

                    title = a.get_text(strip=True)
                    if not title or len(title) < 4:
                        continue

                    # 过滤明显的非活动内容
                    if re.search(r"(申請|手続き|制度|補助|ログイン|サイトマップ|プライバシー|利用規約)", title):
                        continue

                    full_text = container.get_text(" ", strip=True)
                    date_str = self._parse_date(full_text)
                    # 6. 如果日期提取失败，丢弃活动而非错挂于今日
                    if not date_str:
                        logger.debug(f"港区: 无法解析日期，跳过活动 - {title}")
                        continue

                    free = "有料" not in full_text and "円" not in full_text
                    href = a["href"]
                    absolute_url = self.make_absolute_url(href)

                    # 只收录港区域内链接
                    if not href.startswith("/") and "city.minato.tokyo.jp" not in href:
                        continue

                    all_events.append({
                        "title_ja": title,
                        "date": date_str,
                        "ward": "港区",
                        "source_url": absolute_url,
                        "source_name": "港区公式",
                        "source_type": "official",
                        "free": free,
                        "price": 0 if free else None,
                    })

                except Exception as e:
                    logger.debug(f"港区单条解析失败: {e}")
                    continue

        except Exception as e:
            logger.error(f"港区爬虫抓取/解析异常: {e}")
            return []

        # URL 去重
        seen = set()
        unique_events = []
        for e in all_events:
            key = e["source_url"].split("?")[0]
            if key not in seen:
                seen.add(key)
                unique_events.append(e)

        logger.info(f"港区: 最终 {len(unique_events)} 条活动")
        return unique_events

    def _parse_date(self, text: str) -> str | None:
        """从日文文本安全提取日期，支持令和纪年"""
        m = re.search(r"(?:令和(\d+)年|(202\d)年)(\d{1,2})月(\d{1,2})日", text)
        if m:
            year = int(m.group(2)) if m.group(2) else 2018 + int(m.group(1))
            return f"{year}-{int(m.group(3)):02d}-{int(m.group(4)):02d}"
        m = re.search(r"(\d{1,2})月(\d{1,2})日", text)
        if m:
            month, day = int(m.group(1)), int(m.group(2))
            year = datetime.now().year
            if month < datetime.now().month - 3:
                year += 1
            return f"{year}-{month:02d}-{day:02d}"
        return None

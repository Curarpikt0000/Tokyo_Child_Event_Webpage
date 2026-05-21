"""
文件功能：レッツエンジョイ東京 (enjoytokyo.jp) 综合亲子活动爬虫
实现方式：CamoFox 获取动态页面，BeautifulSoup 解析
主要模块：EnjoyTokyoScraper
目标页面：https://www.enjoytokyo.jp/list/f-family/
涵盖范围：东京全域亲子/家庭向活动，含港区芝浦祭り、Hills Spa 等
依赖关系：camoufox, bs4, scraper.base
"""

import logging
import re
import time
from datetime import datetime
from bs4 import BeautifulSoup

from camoufox.sync_api import Camoufox
from scraper.base import BaseScraper

logger = logging.getLogger(__name__)


class EnjoyTokyoScraper(BaseScraper):
    def __init__(self, source_config: dict):
        super().__init__("enjoytokyo", source_config)
        self.list_path = source_config.get("list_path", "/list/f-family/")

    def fetch(self) -> list[dict]:
        all_events = []
        url = f"{self.base_url}{self.list_path}"

        # 1. robots.txt 校验
        if not self.can_fetch(url):
            logger.warning(f"robots.txt 禁止访问，跳过: {url}")
            return []

        try:
            # 2. 限速延迟控制
            self._throttle()

            logger.info(f"正在启动 CamoFox 抓取 enjoytokyo: {url}")
            # 3. geoip=False，避免 CI 报错
            with Camoufox(headless=True, geoip=False) as browser:
                page = browser.new_page()
                page.goto(url, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)  # 等待 JS 渲染
                html = page.content()
                # 4. 更新上次请求时间戳
                self._last_request_time = time.time()

            # 5. 异常隔离：将 BeautifulSoup 解析放在主 try-except 块中
            soup = BeautifulSoup(html, "lxml")

            # enjoytokyo 活动列表：每个 article 或 li.eventlist 是一个活动
            event_blocks = (
                soup.select("article.event-list-item")
                or soup.select("li.event-list__item")
                or soup.select("div.event-item")
                or soup.select("article")
            )

            if not event_blocks:
                # 降级：直接找所有含 /event/ 的链接
                event_blocks = []
                for a in soup.find_all("a", href=re.compile(r"/event/\d+")):
                    event_blocks.append(a.find_parent(["article", "li", "div"]) or a)

            logger.info(f"EnjoyTokyo: 发现 {len(event_blocks)} 个活动块")

            for block in event_blocks:
                try:
                    # 标题
                    title_elem = block.find(["h2", "h3", "h4"])
                    if not title_elem:
                        a = block.find("a") if hasattr(block, "find") else block
                        if not a:
                            continue
                        title_elem = a

                    title = title_elem.get_text(strip=True)
                    if not title or len(title) < 3:
                        continue

                    # 链接
                    a_tag = block.find("a", href=True) if hasattr(block, "find") else block
                    if not a_tag or not a_tag.get("href"):
                        continue
                    href = a_tag["href"]
                    detail_url = href if href.startswith("http") else f"{self.base_url}{href}"

                    # 全文用于日期/免费判断
                    block_text = block.get_text(" ", strip=True) if hasattr(block, "get_text") else title

                    # 日期解析
                    date_str = self._parse_date(block_text)
                    # 6. 若解析不出日期，跳过该活动
                    if not date_str:
                        logger.debug(f"EnjoyTokyo: 无法解析日期，跳过 - {title}")
                        continue

                    # 免费判断
                    free = "無料" in block_text or "入場無料" in block_text

                    # 区名推断（从地名关键词）
                    ward = self._guess_ward(block_text)

                    # 图片
                    img = block.find("img") if hasattr(block, "find") else None
                    image_url = None
                    if img and img.get("src"):
                        src = img["src"]
                        if not src.startswith("data:"):
                            image_url = src if src.startswith("http") else f"{self.base_url}{src}"

                    all_events.append({
                        "title_ja": title,
                        "date": date_str,
                        "ward": ward,
                        "source_url": detail_url,
                        "source_name": "レッツエンジョイ東京",
                        "source_type": "supplementary",
                        "free": free,
                        "price": 0 if free else None,
                        "image_url": image_url,
                    })

                except Exception as e:
                    logger.debug(f"解析单条活动失败，跳过: {e}")
                    continue

        except Exception as e:
            logger.error(f"EnjoyTokyo 爬虫抓取/解析异常: {e}")
            return []

        # URL 去重
        seen = set()
        unique = []
        for evt in all_events:
            key = evt["source_url"].split("?")[0]
            if key not in seen:
                seen.add(key)
                unique.append(evt)

        logger.info(f"EnjoyTokyo: 最终获取 {len(unique)} 条活动")
        return unique

    def _parse_date(self, text: str) -> str | None:
        """从日文文本提取日期"""
        # 令和8年5月31日 / 2026年5月31日
        m = re.search(r"(?:令和(\d+)年|(202\d)年)(\d{1,2})月(\d{1,2})日", text)
        if m:
            if m.group(2):
                year = int(m.group(2))
            else:
                year = 2018 + int(m.group(1))
            return f"{year}-{int(m.group(3)):02d}-{int(m.group(4)):02d}"
        # X月X日
        m = re.search(r"(\d{1,2})月(\d{1,2})日", text)
        if m:
            month, day = int(m.group(1)), int(m.group(2))
            year = datetime.now().year
            if month < datetime.now().month - 2:
                year += 1
            return f"{year}-{month:02d}-{day:02d}"
        return None

    def _guess_ward(self, text: str) -> str:
        """从文本中推断所属区"""
        ward_map = {
            "港区": ["港区", "芝浦", "三田", "六本木", "麻布", "白金", "虎ノ門", "赤坂", "台场"],
            "渋谷区": ["渋谷", "代官山", "恵比寿", "代々木"],
            "新宿区": ["新宿", "高田马场", "四谷"],
            "江東区": ["江東区", "有明", "豊洲", "深川", "木場", "東陽"],
            "中央区": ["中央区", "銀座", "築地", "日本橋"],
            "千代田区": ["千代田区", "丸の内", "神保町", "秋葉原"],
            "品川区": ["品川区", "大井", "五反田"],
            "目黒区": ["目黒区", "中目黒", "自由が丘"],
            "世田谷区": ["世田谷区", "三軒茶屋", "下北沢", "二子玉川"],
        }
        for ward, keywords in ward_map.items():
            for kw in keywords:
                if kw in text:
                    return ward
        return "その他"

"""
文件功能：プラレール博 in TOKYO (plarail-tokyo.com) 爬虫
实现方式：requests + BeautifulSoup 抓取 WordPress 静态首页
主要模块：PlarailScraper
目标页面：https://plarail-tokyo.com/
特性：年度展览型专题站，例年 GW 前后在有明 GYM-EX 开催
依赖关系：requests, bs4, scraper.base
"""

import logging
import re
from datetime import datetime
from bs4 import BeautifulSoup

from scraper.base import BaseScraper

logger = logging.getLogger(__name__)


class PlarailScraper(BaseScraper):
    def __init__(self, source_config: dict):
        super().__init__("plarail", source_config)

    def fetch(self) -> list[dict]:
        """
        爬取首页并提取年度展览信息。
        当没有活动信息（展览尚未公布）时返回空列表。
        """
        try:
            logger.info(f"正在检查プラレール博 首页: {self.base_url}")
            resp = self.get(self.base_url)
            if not resp:
                logger.warning("无法访问 plarail-tokyo.com")
                return []

            resp.encoding = resp.apparent_encoding or "utf-8"
            soup = BeautifulSoup(resp.text, "lxml")

            # 提取页面全文用于解析
            full_text = soup.get_text(" ", strip=True)

            # 检查是否有开催期間信息
            # 格式：「2026年5月1日（木）～5月10日（日）」
            date_range = re.search(
                r"(202\d)年\s*(\d{1,2})月\s*(\d{1,2})日[^～〜\-]*[～〜\-]\s*(\d{1,2})月\s*(\d{1,2})日",
                full_text,
            )

            if not date_range:
                # 尝试令和格式
                date_range = re.search(
                    r"令和(\d+)年\s*(\d{1,2})月\s*(\d{1,2})日[^～〜\-]*[～〜\-]\s*(\d{1,2})月\s*(\d{1,2})日",
                    full_text,
                )
                if date_range:
                    year = 2018 + int(date_range.group(1))
                    start_m, start_d = int(date_range.group(2)), int(date_range.group(3))
                    end_m, end_d = int(date_range.group(4)), int(date_range.group(5))
                else:
                    logger.info("プラレール博: 未找到开催期間，本年度可能尚未公布，跳过")
                    return []
            else:
                year = int(date_range.group(1))
                start_m, start_d = int(date_range.group(2)), int(date_range.group(3))
                end_m, end_d = int(date_range.group(4)), int(date_range.group(5))

            start_date = f"{year}-{start_m:02d}-{start_d:02d}"
            end_date = f"{year}-{end_m:02d}-{end_d:02d}"

            # 提取会場
            venue = "有明GYM-EX"  # 默认（历史规律）
            venue_match = re.search(r"会場[：:\s]+([^\s。、\n]{4,30})", full_text)
            if venue_match:
                venue = venue_match.group(1).strip()

            # 提取票价
            price_match = re.search(r"子ども[^円\d]*(\d[\d,]+)円", full_text)
            price = int(price_match.group(1).replace(",", "")) if price_match else None
            free = (price == 0) if price is not None else False

            # 提取活动标题（通常是 h1）
            h1 = soup.find("h1")
            title = h1.get_text(strip=True) if h1 else "プラレール博 in TOKYO"
            if len(title) < 3:
                title = "プラレール博 in TOKYO"

            logger.info(f"プラレール博: 开催期間 {start_date}〜{end_date}, 会場={venue}")

            from datetime import timedelta
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")

            events = []
            curr_dt = start_dt
            while curr_dt <= end_dt:
                events.append({
                    "title_ja": title,
                    "date": curr_dt.strftime("%Y-%m-%d"),
                    "date_start": start_date,
                    "date_end": end_date,
                    "ward": "江東区",   # 有明 GYM-EX 位于江東区有明
                    "venue": venue,
                    "source_url": self.base_url,
                    "source_name": "プラレール博公式",
                    "source_type": "supplementary",
                    "free": free,
                    "price": price,
                    "image_url": self._extract_og_image(soup),
                })
                curr_dt += timedelta(days=1)

            logger.info(f"プラレール博: 成功展开为 {len(events)} 天的日历事件")
            return events

        except Exception as e:
            logger.error(f"プラレール博爬虫异常: {e}")
            return []

    def _extract_og_image(self, soup: BeautifulSoup) -> str | None:
        """从 og:image meta 标签提取封面图"""
        og = soup.find("meta", property="og:image")
        if og and og.get("content"):
            return og["content"]
        # 降级：找第一张内容图
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if src and not src.startswith("data:") and "logo" not in src.lower():
                return self.make_absolute_url(src)
        return None

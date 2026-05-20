"""
文件功能：ウォーカープラス (Walkerplus) 补充数据源爬虫
实现方式：继承 BaseScraper，使用 requests + BeautifulSoup 抓取并解析 HTML
主要模块：WalkerplusScraper
输入输出：返回标准化的活动字典列表
依赖关系：scraper.base, bs4, requests, re, config
创建日期：2026-05-20
"""

import logging
import re
from datetime import datetime
from bs4 import BeautifulSoup

from scraper.base import BaseScraper

logger = logging.getLogger(__name__)


class WalkerplusScraper(BaseScraper):
    def __init__(self, source_config: dict) -> None:
        """
        初始化 Walkerplus 爬虫
        """
        super().__init__("walkerplus", source_config)

    def fetch(self) -> list[dict]:
        """
        爬取 Walkerplus 上的东京活动列表
        """
        all_events = []
        # Walkerplus 东京都事件列表 URL
        url = f"{self.base_url}/event_list/ar0313/"
        logger.info(f"正在爬取 Walkerplus 列表: {url}")

        html_content = None
        try:
            resp = self.get(url)
            if resp:
                html_content = resp.content
                logger.info("已成功通过 requests 获取 Walkerplus 页面")
        except Exception as req_err:
            logger.warning(f"Requests 抓取 Walkerplus 页面发生错误: {req_err}，准备降级为 CamoFox...")

        if not html_content:
            logger.info("启动 CamoFox 引擎抓取 Walkerplus...")
            try:
                from camoufox.sync_api import Camoufox
                with Camoufox(headless=True, geoip=True) as browser:
                    page = browser.new_page()
                    page.goto(url, wait_until="domcontentloaded")
                    html_content = page.content()
                    logger.info("已成功通过 CamoFox 获取 Walkerplus 页面内容")
            except Exception as cam_err:
                logger.error(f"CamoFox 最终抓取 Walkerplus 页面也失败: {cam_err}")
                return all_events

        soup = BeautifulSoup(html_content, "lxml")
        items = soup.find_all("div", class_="m-mainlist-item")
        logger.info(f"解析到 {len(items)} 个活动卡片")

        for item in items:
            try:
                # 1. 提取日文标题 (title_ja)
                ttl_tag = item.find("span", class_="m-mainlist-item__ttl")
                if not ttl_tag:
                    continue
                title_ja = ttl_tag.get_text(strip=True)

                # 2. 提取详情 URL (source_url)
                link_tag = item.find("a", href=True)
                if not link_tag:
                    continue
                source_url = self.make_absolute_url(link_tag["href"])

                # 3. 提取活动日期 (date)
                date_str = datetime.now().strftime("%Y-%m-%d")
                period_tag = item.find("p", class_="m-mainlist-item-event__period")
                if period_tag:
                    period_text = period_tag.get_text(" ", strip=True)
                    # 匹配 "2026年4月4日"
                    date_match = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", period_text)
                    if date_match:
                        date_str = f"{date_match.group(1)}-{int(date_match.group(2)):02d}-{int(date_match.group(3)):02d}"
                    else:
                        # 匹配 "4月4日" (补全当前年份)
                        date_match_short = re.search(r"(\d{1,2})月(\d{1,2})日", period_text)
                        if date_match_short:
                            year = datetime.now().year
                            date_str = f"{year}-{int(date_match_short.group(1)):02d}-{int(date_match_short.group(2)):02d}"

                # 4. 提取区名 (ward)
                ward = "東京都"
                map_p = item.find("p", class_="m-mainlist-item__map")
                if map_p:
                    map_links = map_p.find_all("a")
                    if len(map_links) >= 2:
                        # 第二个链接一般是具体的区名，如 "墨田区"
                        ward_candidate = map_links[1].get_text(strip=True)
                        if ward_candidate.endswith(("区", "市", "町", "村")):
                            ward = ward_candidate

                # 5. 提取场馆 (venue)
                venue = ""
                place_p = item.find("p", class_="m-mainlist-item-event__place")
                if place_p:
                    place_link = place_p.find("a")
                    if place_link:
                        venue = place_link.get_text(strip=True)

                # 6. 费用与免费 (free, price)
                text_content = item.get_text(" ", strip=True)
                free = "無料" in text_content or "入場無料" in text_content
                price = 0 if free else None

                # 7. 提取图片 (image_url)
                image_url = None
                img_tag = item.find("img")
                if img_tag:
                    image_url = img_tag.get("src") or img_tag.get("data-src")
                    if image_url and image_url.startswith("//"):
                        image_url = "https:" + image_url

                all_events.append({
                    "title_ja": title_ja,
                    "date": date_str,
                    "ward": ward,
                    "source_url": source_url,
                    "source_name": "ウォーカープラス",
                    "source_type": "supplementary",
                    "venue": venue,
                    "free": free,
                    "price": price,
                    "image_url": image_url,
                })
            except Exception as e:
                logger.warning(f"解析 Walkerplus 单个活动项出错: {e}")
                continue

        logger.info(f"Walkerplus 爬取完成，共提取 {len(all_events)} 条活动")
        return all_events

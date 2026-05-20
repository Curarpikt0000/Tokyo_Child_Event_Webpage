"""
文件功能：じゃらん (Jalan.net) 补充数据源爬虫
实现方式：继承 BaseScraper，使用 requests + BeautifulSoup 抓取并解析 HTML（支持 cp932 解码），在 403 等异常情况下自动降级为使用 Camoufox 抗指纹浏览器抓取。
主要模块：JalanScraper
输入输出：返回标准化的活动字典列表
依赖关系：scraper.base, bs4, requests, re, config, camoufox (降级依赖)
创建日期：2026-05-20
"""

import logging
import re
from datetime import datetime
from bs4 import BeautifulSoup

from scraper.base import BaseScraper
import config

logger = logging.getLogger(__name__)


class JalanScraper(BaseScraper):
    def __init__(self, source_config: dict) -> None:
        """
        初始化 Jalan 爬虫
        """
        super().__init__("jalan", source_config)

    def fetch(self) -> list[dict]:
        """
        爬取 Jalan 上的东京玩乐体验列表
        """
        all_events = []
        # Jalan 东京都游玩/体验活动列表 URL (130000 代表东京都)
        url = f"{self.base_url}/activity/130000/"
        logger.info(f"正在爬取 Jalan.net 列表: {url}")

        html_content = None

        # ── 阶段 1：首选普通 Requests 抓取 ────────────────────
        headers = {
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
            "Referer": "https://www.jalan.net/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        }

        try:
            resp = self.get(url, headers=headers)
            if resp:
                # Jalan.net 的网页声明编码是 Shift_JIS/Windows-31J，必须用 cp932 解码，防日文乱码
                try:
                    html_content = resp.content.decode("cp932", errors="ignore")
                    logger.info("已成功通过 requests (cp932 解码) 获取 Jalan 页面")
                except Exception as dec_err:
                    logger.warning(f"cp932 解码发生异常，回退到 requests.text: {dec_err}")
                    html_content = resp.text
        except Exception as req_err:
            logger.warning(f"Requests 抓取 Jalan 发生错误: {req_err}，准备降级为 CamoFox 引擎...")

        # ── 阶段 2：Requests 失败或被阻拦时，降级使用 CamoFox 浏览器 ─────────
        if not html_content:
            logger.info("启动 CamoFox 抗指纹引擎抓取 Jalan...")
            try:
                from camoufox.sync_api import Camoufox
                with Camoufox(headless=True, geoip=True) as browser:
                    page = browser.new_page()
                    # 仿照真实浏览器，加入延时
                    page.goto(url, wait_until="domcontentloaded")
                    html_content = page.content()
                    logger.info("已成功通过 CamoFox 获取 Jalan 页面内容")
            except Exception as cam_err:
                logger.error(f"CamoFox 降级抓取也最终失败: {cam_err}")
                return all_events

        # ── 阶段 3：解析 HTML 页面 ───────────────────────────
        try:
            soup = BeautifulSoup(html_content, "lxml")
            ul = soup.find("ul", class_="cassetteList-list")
            if not ul:
                logger.warning("未能在页面中找到 cassetteList-list 活动容器列表")
                return all_events

            children = ul.find_all(recursive=False)
            logger.info(f"查找到 {len(children)} 个列表直接子节点")

            current_venue = ""
            current_ward = "東京都"

            for child in children:
                if child.name != "li":
                    continue

                classes = child.get("class", [])

                # 1. 场馆卡片 (没有 class 属性的 <li>)
                if not classes:
                    # 提取场馆名称
                    tit_tag = child.find("a", class_="sptList-tit")
                    if tit_tag:
                        current_venue = tit_tag.get_text(strip=True)

                    # 提取大类与粗分区
                    cat_p = child.find("p", class_="item-categories")
                    if cat_p:
                        cat_text = cat_p.get_text(strip=True)
                        # 基于大区分类做简单的日文区名映射（以支持数据标准）
                        if "新宿" in cat_text:
                            current_ward = "新宿区"
                        elif "渋谷" in cat_text:
                            current_ward = "渋谷区"
                        elif "上野" in cat_text or "浅草" in cat_text:
                            current_ward = "台東区"
                        elif "お台場" in cat_text or "豊洲" in cat_text:
                            current_ward = "江東区"
                        elif "銀座" in cat_text or "日本橋" in cat_text:
                            current_ward = "中央区"
                        elif "池袋" in cat_text:
                            current_ward = "豊島区"
                        elif "品川" in cat_text:
                            current_ward = "品川区"
                        elif "墨田" in cat_text or "スカイツリー" in cat_text:
                            current_ward = "墨田区"
                        else:
                            current_ward = "東京都"
                    continue

                # 2. 计划卡片 (class 包含 "item-relation-planlist")
                if "item-relation-planlist" in classes:
                    sub_items = child.find_all("li", class_="item")
                    for sub_item in sub_items:
                        try:
                            # 提取活动标题 (title_ja)
                            title_tag = sub_item.find("a", class_="planlist-tit")
                            if not title_tag:
                                continue
                            title_ja = title_tag.get_text(strip=True)

                            # 提取链接 (source_url)
                            href = title_tag.get("href", "")
                            source_url = self.make_absolute_url(href)

                            # 价格提取 (price, free)
                            price = None
                            free = False
                            price_dd = sub_item.find("dd", class_="relation-planlist-price")
                            if price_dd:
                                price_text = price_dd.get_text(strip=True)
                                price_match = re.search(r"([\d,]+)円", price_text)
                                if price_match:
                                    price = int(price_match.group(1).replace(",", ""))
                                if "無料" in price_text or (price is not None and price == 0):
                                    free = True
                                    price = 0

                            # 图片提取 (image_url)
                            image_url = None
                            img_tag = sub_item.find("img")
                            if img_tag:
                                # 懒加载通常把真实路径放在 data-src 里
                                image_url = img_tag.get("data-src") or img_tag.get("src")
                                if image_url and image_url.startswith("//"):
                                    image_url = "https:" + image_url

                            # 日期 (date)：游玩项目多为长期可预约，默认为抓取当天日期，后续清洗去重
                            date_str = datetime.now().strftime("%Y-%m-%d")

                            all_events.append({
                                "title_ja": title_ja,
                                "date": date_str,
                                "ward": current_ward,
                                "source_url": source_url,
                                "source_name": "じゃらん",
                                "source_type": "supplementary",
                                "venue": current_venue,
                                "free": free,
                                "price": price,
                                "image_url": image_url,
                            })
                        except Exception as parse_err:
                            logger.warning(f"解析 Jalan 子计划项目出错: {parse_err}")
                            continue

        except Exception as e:
            logger.error(f"解析 Jalan 页面总容器出错: {e}")

        logger.info(f"Jalan.net 爬取完成，共提取 {len(all_events)} 条活动")
        return all_events

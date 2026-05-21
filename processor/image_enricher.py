"""
文件功能：为缺失封面图的活动自动补充图片 URL
实现方式：对每个没有 image_url 的活动，抓取 source_url 页面的 og:image 元标签。
         使用持久化 JSON 缓存避免重复请求，遵守 2 秒请求间隔。
主要模块：ImageEnricher
输入输出：接收活动列表，更新 image_url 字段后返回
依赖关系：requests, BeautifulSoup4, config
"""

import json
import logging
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

import config

logger = logging.getLogger(__name__)

# 图片缓存文件路径
IMAGE_CACHE_FILE = config.DATA_DIR / "image_cache.json"


class ImageEnricher:
    def __init__(self):
        self.cache = self._load_cache()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": config.USER_AGENT,
            "Accept-Language": "ja,en;q=0.9",
        })
        self._last_request_time = 0.0

    def _load_cache(self) -> dict:
        """加载持久化图片 URL 缓存（key: source_url, value: image_url or ""）"""
        if IMAGE_CACHE_FILE.exists():
            try:
                with open(IMAGE_CACHE_FILE, "r", encoding="utf-8") as f:
                    cache = json.load(f)
                    logger.info(f"[图片] 加载图片缓存：{len(cache)} 条")
                    return cache
            except Exception as e:
                logger.warning(f"[图片] 缓存加载失败，将重新创建：{e}")
        return {}

    def _save_cache(self) -> None:
        """将缓存持久化到磁盘"""
        try:
            IMAGE_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(IMAGE_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"[图片] 缓存保存失败：{e}")

    def _throttle(self) -> None:
        """遵守 ≥2 秒的请求间隔"""
        elapsed = time.time() - self._last_request_time
        delay = getattr(config, "REQUEST_DELAY", 2.0)
        if elapsed < delay:
            time.sleep(delay - elapsed)

    def _fetch_og_image(self, url: str) -> str:
        """
        访问指定 URL，提取 og:image 元标签内容。
        若无 og:image，尝试 twitter:image 或页面首张大图。
        返回图片 URL 字符串，失败返回空字符串。
        """
        self._throttle()
        try:
            resp = self.session.get(url, timeout=10, allow_redirects=True)
            self._last_request_time = time.time()
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # 优先级 1：og:image
            og = soup.find("meta", property="og:image")
            if og and og.get("content"):
                img = og["content"].strip()
                if img.startswith("http"):
                    return img
                return urljoin(url, img)

            # 优先级 2：twitter:image
            tw = soup.find("meta", attrs={"name": "twitter:image"})
            if tw and tw.get("content"):
                img = tw["content"].strip()
                if img.startswith("http"):
                    return img
                return urljoin(url, img)

            # 优先级 3：页面首张宽度 >= 200 的 <img>
            for img_tag in soup.find_all("img"):
                src = img_tag.get("src", "")
                width = img_tag.get("width", "")
                try:
                    if int(width) >= 200 and src:
                        return src if src.startswith("http") else urljoin(url, src)
                except (ValueError, TypeError):
                    pass

        except Exception as e:
            logger.debug(f"[图片] 请求失败 {url}：{e}")
            self._last_request_time = time.time()

        return ""

    def enrich(self, events: list[dict]) -> list[dict]:
        """
        主入口：遍历活动列表，为缺少 image_url 的活动补充图片 URL。
        使用缓存避免重复请求，仅发起必要的网络请求。
        """
        needs_fetch = [
            e for e in events
            if not e.get("image_url") and e.get("source_url")
        ]
        logger.info(f"[图片] 需要补充图片的活动：{len(needs_fetch)} / {len(events)} 条")

        newly_fetched = 0
        cache_hit = 0

        for event in needs_fetch:
            url = event["source_url"]

            # 命中缓存（包括已知为空的记录，避免重复请求）
            if url in self.cache:
                cached_img = self.cache[url]
                if cached_img:
                    event["image_url"] = cached_img
                cache_hit += 1
                continue

            # 新请求
            img_url = self._fetch_og_image(url)
            self.cache[url] = img_url  # 缓存（无论成功与否）
            newly_fetched += 1

            if img_url:
                event["image_url"] = img_url
                logger.debug(f"[图片] 已获取：{event.get('title_zh', url)} → {img_url[:60]}...")
            else:
                logger.debug(f"[图片] 未找到图片：{url}")

        # 每次新请求后保存缓存
        if newly_fetched > 0:
            self._save_cache()

        filled = sum(1 for e in events if e.get("image_url"))
        logger.info(
            f"[图片] 补充完成：缓存命中 {cache_hit}，新请求 {newly_fetched}，"
            f"最终有图 {filled}/{len(events)} 条"
        )
        return events

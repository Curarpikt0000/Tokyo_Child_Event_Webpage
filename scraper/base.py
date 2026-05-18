"""
文件功能：基础爬虫类，所有具体爬虫必须继承此类
实现方式：抽象基类，封装 robots.txt 检查、请求限速、重试逻辑
主要模块：BaseScraper 抽象类
输入输出：接收站点配置；返回标准化的原始活动字典列表
依赖关系：requests, urllib.robotparser, config
创建日期：2026-05-17
"""

import logging
import time
import urllib.robotparser
from abc import ABC, abstractmethod
from typing import Any
from urllib.parse import urljoin, urlparse

import requests

import config

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """
    所有爬虫的基础类，提供：
    - robots.txt 自动检查（合规爬取）
    - 请求间隔控制（≥2秒）
    - 自动重试（最多3次）
    - 统一的 User-Agent
    - 标准化的原始数据格式
    """

    def __init__(self, name: str, source_config: dict) -> None:
        """
        功能描述：初始化爬虫基类
        参数说明：
            name: 数据源名称（如"渋谷区"或"ikoyo"）
            source_config: 来自 config.py 的数据源配置字典
        """
        self.name = name
        self.source_config = source_config
        self.base_url = source_config["base_url"]
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": config.USER_AGENT})
        self._rp = None  # robots.txt 解析器（懒加载）
        self._last_request_time = 0.0

    # ── robots.txt 合规检查 ──────────────────────────────

    def _load_robots(self) -> None:
        """
        功能描述：加载并解析目标站点的 robots.txt
        实现逻辑：使用标准库 urllib.robotparser 解析
        参数说明：无
        返回值：无
        异常：加载失败时记录警告，允许爬取（宽松策略）
        """
        if self._rp is not None:
            return
        robots_url = urljoin(self.base_url, "/robots.txt")
        self._rp = urllib.robotparser.RobotFileParser()
        self._rp.set_url(robots_url)
        try:
            self._rp.read()
            logger.debug(f"已加载 robots.txt：{robots_url}")
        except Exception as e:
            logger.warning(f"robots.txt 加载失败，默认允许爬取：{robots_url} — {e}")
            self._rp = None

    def can_fetch(self, url: str) -> bool:
        """
        功能描述：检查指定 URL 是否允许爬取
        参数说明：
            url: 要检查的目标 URL
        返回值：True 表示允许，False 表示禁止
        """
        self._load_robots()
        if self._rp is None:
            return True  # 无法读取 robots.txt 时宽松处理
        return self._rp.can_fetch(config.USER_AGENT, url)

    # ── 限速 HTTP 请求 ───────────────────────────────────

    def _throttle(self) -> None:
        """
        功能描述：确保请求间隔 ≥ config.REQUEST_DELAY 秒
        实现逻辑：计算距上次请求的时间差，不足时 sleep
        """
        elapsed = time.time() - self._last_request_time
        if elapsed < config.REQUEST_DELAY:
            time.sleep(config.REQUEST_DELAY - elapsed)

    def get(self, url: str, **kwargs: Any) -> requests.Response | None:
        """
        功能描述：执行限速 + 重试的 GET 请求
        实现逻辑：
            1. 检查 robots.txt 是否允许
            2. 等待限速间隔
            3. 最多重试 MAX_RETRIES 次
            4. 记录最后请求时间
        参数说明：
            url: 目标 URL
            **kwargs: 透传给 requests.get()
        返回值：Response 对象，失败返回 None
        异常：所有网络异常均被捕获并记录
        """
        # 合规检查
        if not self.can_fetch(url):
            logger.warning(f"robots.txt 禁止访问，跳过：{url}")
            return None

        for attempt in range(1, config.MAX_RETRIES + 1):
            try:
                self._throttle()
                resp = self.session.get(
                    url,
                    timeout=config.REQUEST_TIMEOUT,
                    **kwargs,
                )
                self._last_request_time = time.time()
                resp.raise_for_status()
                logger.debug(f"GET {url} → {resp.status_code}")
                return resp
            except requests.HTTPError as e:
                logger.warning(f"HTTP 错误（尝试 {attempt}/{config.MAX_RETRIES}）：{url} — {e}")
            except requests.RequestException as e:
                logger.warning(f"请求失败（尝试 {attempt}/{config.MAX_RETRIES}）：{url} — {e}")

            if attempt < config.MAX_RETRIES:
                time.sleep(config.REQUEST_DELAY * attempt)  # 指数退避

        logger.error(f"请求最终失败，已放弃：{url}")
        return None

    # ── 抽象接口 ─────────────────────────────────────────

    @abstractmethod
    def fetch(self) -> list[dict]:
        """
        功能描述：爬取目标页面，返回标准化的原始活动数据列表
        实现逻辑：由子类实现，负责页面解析和字段提取
        参数说明：无
        返回值：原始活动字典列表，每条字典至少包含以下字段：
            - title_ja: str（日文标题，必填）
            - date: str（"YYYY-MM-DD"，必填）
            - ward: str（区名，日文，必填）
            - source_url: str（原始链接，必填）
            - source_name: str（来源名称）
            - source_type: str（"official" 或 "supplementary"）
            - venue: str（可选）
            - address: str（可选）
            - time_start: str（可选，"HH:MM"）
            - time_end: str（可选，"HH:MM"）
            - free: bool（可选，默认 False）
            - price: int（可选，日元）
            - image_url: str（可选）
        异常：应将异常向上抛出，由 main.py 的错误隔离逻辑处理
        """
        raise NotImplementedError

    # ── 辅助工具 ─────────────────────────────────────────

    def make_absolute_url(self, path: str) -> str:
        """
        功能描述：将相对路径转换为完整 URL
        参数说明：
            path: 相对或绝对路径
        返回值：完整 URL 字符串
        """
        if path.startswith("http"):
            return path
        return urljoin(self.base_url, path)

    def make_event_id(self, date: str, index: int) -> str:
        """
        功能描述：生成唯一的活动 ID
        参数说明：
            date: "YYYY-MM-DD"
            index: 当日序号（0-based）
        返回值：格式为 "evt_YYYYMMDD_NNN" 的字符串
        """
        date_compact = date.replace("-", "")
        return f"evt_{date_compact}_{index:03d}"

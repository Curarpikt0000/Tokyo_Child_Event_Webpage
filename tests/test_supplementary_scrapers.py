"""
文件功能：测试 WalkerplusScraper 和 JalanScraper 的数据抓取和解析
实现方式：使用 unittest.mock，通过 Mock 页面 HTML 的方式在离线状态下验证提取数据的 Schema 合规性与选择器正确性。
主要模块：TestSupplementaryScrapers
依赖关系：unittest, unittest.mock, config, scraper.supplementary.walkerplus, scraper.supplementary.jalan
创建日期：2026-05-20
"""

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

import config
from scraper.supplementary.walkerplus import WalkerplusScraper
from scraper.supplementary.jalan import JalanScraper

# ── Mock 页面数据 ───────────────────────────────────────

MOCK_WALKERPLUS_HTML = """
<div class="m-mainlist-item">
 <a href="/event/ar0313e462812/">
  <span class="m-mainlist-item__ttl">
   台湾祭 in 東京スカイツリータウン2026ー台南ランタン祭ー
  </span>
 </a>
 <p class="m-mainlist-item-event__period">
  <span class="m-mainlist-item-event__open">
   開催中
  </span>
  2026年4月4日(土)～5月31日(日)
 </p>
 <div class="m-mainlist-item__link">
  <a class="m-mainlist-item__txt" href="/event/ar0313e462812/">
   台湾の夜市グルメを楽しめる
  </a>
  <p class="m-mainlist-item__map">
   <a class="m-mainlist-item__maplink" href="/event_list/ar0313/">
    東京都
   </a>
   <a class="m-mainlist-item__maplink" href="/event_list/ar0313107/sumida/">
    墨田区
   </a>
  </p>
  <p class="m-mainlist-item-event__place">
   <a class="m-mainlist-item-event__placelink" href="/spot/ar0313s80116/">
    東京スカイツリータウン(R)
   </a>
  </p>
  <ul class="m-mainlist-item__tags">
   <li class="m-mainlist-item__tagsitem">
    <span class="m-mainlist-item__tagsitemlink is-tag_disable">
     入場無料
    </span>
   </li>
  </ul>
 </div>
 <img src="https://example.com/test.jpg" />
</div>
"""

MOCK_JALAN_HTML = """
<ul class="cassetteList-list">
 <li>
  <div class="item-listContents">
   <div class="item-info">
    <p class="item-name">
     <a class="sptList-tit" href="//www.jalan.net/kankou/spt_guide000000216175/activity_plan/?showplan=ichiran_planall">
      KOKO HOTEL新宿四谷 レストランBistroW
     </a>
    </p>
    <p class="item-categories">
     東京 ＞ 新宿・中野・阿佐ヶ谷・吉祥寺
    </p>
   </div>
  </div>
 </li>
 <li class="item-relation-planlist">
  <ul class="planList">
   <li class="item">
    <img data-src="https://cdn.activityboard.jp/KR01085987/pictures/l00004E6B2/P00027F688.jpg"/>
    <dl>
     <dt>
      <a class="planlist-tit" href="//www.jalan.net/kankou/spt_guide000000216175/activity/l00004E6B2/?showplan=ichiran">
       BistroＷのランチ♪【選べるメインディッシュ】
      </a>
     </dt>
     <dd class="relation-planlist-price">
      <span>
       1,650円～
      </span>
     </dd>
    </dl>
   </li>
  </ul>
 </li>
</ul>
"""


class TestSupplementaryScrapers(unittest.TestCase):
    @patch("scraper.base.BaseScraper.get")
    def test_walkerplus_scraper(self, mock_get) -> None:
        """
        验证 WalkerplusScraper 解析逻辑与数据提取正确性（离线 Mock）
        """
        # 设置 Mock 响应
        mock_resp = MagicMock()
        mock_resp.content = MOCK_WALKERPLUS_HTML.encode("utf-8")
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp

        cfg = config.SUPPLEMENTARY_SOURCES.get("walkerplus")
        self.assertIsNotNone(cfg)

        scraper = WalkerplusScraper(cfg)
        events = scraper.fetch()

        self.assertEqual(len(events), 1)
        first_event = events[0]

        # 验证提取值
        self.assertEqual(first_event["title_ja"], "台湾祭 in 東京スカイツリータウン2026ー台南ランタン祭ー")
        self.assertEqual(first_event["source_url"], "https://event.walkerplus.com/event/ar0313e462812/")
        self.assertEqual(first_event["date"], "2026-04-04")
        self.assertEqual(first_event["ward"], "墨田区")
        self.assertEqual(first_event["venue"], "東京スカイツリータウン(R)")
        self.assertEqual(first_event["source_name"], "ウォーカープラス")
        self.assertEqual(first_event["source_type"], "supplementary")
        self.assertTrue(first_event["free"])
        self.assertEqual(first_event["price"], 0)
        self.assertEqual(first_event["image_url"], "https://example.com/test.jpg")

    @patch("scraper.base.BaseScraper.get")
    def test_jalan_scraper(self, mock_get) -> None:
        """
        验证 JalanScraper 解析逻辑与数据提取正确性（离线 Mock）
        """
        # 设置 Mock 响应
        mock_resp = MagicMock()
        # Jalan.net 的网页声明编码是 Shift_JIS/Windows-31J，模拟 cp932 编码字节
        mock_resp.content = MOCK_JALAN_HTML.encode("cp932")
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp

        cfg = config.SUPPLEMENTARY_SOURCES.get("jalan")
        self.assertIsNotNone(cfg)

        scraper = JalanScraper(cfg)
        events = scraper.fetch()

        self.assertEqual(len(events), 1)
        first_event = events[0]

        # 验证提取值
        self.assertEqual(first_event["title_ja"], "BistroＷのランチ♪【選べるメインディッシュ】")
        self.assertEqual(first_event["source_url"], "https://www.jalan.net/kankou/spt_guide000000216175/activity/l00004E6B2/?showplan=ichiran")
        
        # Jalan 爬虫默认将日期定为当前日期
        today_str = datetime.now().strftime("%Y-%m-%d")
        self.assertEqual(first_event["date"], today_str)
        
        self.assertEqual(first_event["ward"], "新宿区")  # 应该通过 categories 里的 "新宿" 匹配到新宿区
        self.assertEqual(first_event["venue"], "KOKO HOTEL新宿四谷 レストランBistroW")
        self.assertEqual(first_event["source_name"], "じゃらん")
        self.assertEqual(first_event["source_type"], "supplementary")
        self.assertFalse(first_event["free"])
        self.assertEqual(first_event["price"], 1650)
        self.assertEqual(first_event["image_url"], "https://cdn.activityboard.jp/KR01085987/pictures/l00004E6B2/P00027F688.jpg")


if __name__ == "__main__":
    unittest.main()

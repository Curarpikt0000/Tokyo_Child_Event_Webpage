import unittest
from unittest.mock import patch, MagicMock
import os
import json
import shutil
from pathlib import Path

import config
import main

class TestMainPipeline(unittest.TestCase):
    def setUp(self):
        # 创建临时输出文件夹
        self.temp_dir = Path("/Users/chaojin/Antigravity Projects/Tokyo_Child_Event_Webpage/tests/temp_docs")
        self.temp_data_dir = self.temp_dir / "data"
        self.temp_events_dir = self.temp_data_dir / "events"
        
        self.temp_events_dir.mkdir(parents=True, exist_ok=True)
        
        # 备份原有 config 字段
        self.orig_data_dir = config.DATA_DIR
        self.orig_events_dir = config.EVENTS_DIR
        
        config.DATA_DIR = self.temp_data_dir
        config.EVENTS_DIR = self.temp_events_dir

    def tearDown(self):
        # 还原 config
        config.DATA_DIR = self.orig_data_dir
        config.EVENTS_DIR = self.orig_events_dir
        
        # 删除临时输出文件夹
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @patch("main.load_scrapers")
    @patch("processor.llm_classifier.LLMClassifier.process_all")
    def test_pipeline_integration(self, mock_process_all, mock_load_scrapers):
        """测试主流程端到端：从 Scraper 获取数据到写出 JSON"""
        
        # Mock 爬虫
        mock_scraper = MagicMock()
        mock_scraper.name = "渋谷区"
        mock_scraper.fetch.return_value = [
            {
                "title_ja": "渋谷区親子イベント",
                "date": "2026-06-01",
                "ward": "渋谷区",
                "source_name": "渋谷区Neuvola",
                "source_type": "official",
                "free": True
            }
        ]
        mock_load_scrapers.return_value = [mock_scraper]
        
        # Mock LLM 返回
        mock_process_all.return_value = [
            {
                "title_ja": "渋谷区親子イベント",
                "title_zh": "涩谷区亲子活动",
                "date": "2026-06-01",
                "ward": "渋谷区",
                "source_name": "渋谷区Neuvola",
                "source_type": "official",
                "free": True,
                "age_min": 0,
                "age_max": 5,
                "type": "outdoor",
                "score_reasoning": "四维总分",
                "ai_score": 85,
                "ai_tags": ["免费", "户外"],
                "summary_zh": "适合小朋友的室外活动。",
                "rain_ok": True
            }
        ]
        
        # 执行管道
        main.run_pipeline()
        
        # 验证是否成功生成了 docs/data/index.json
        index_file = self.temp_data_dir / "index.json"
        self.assertTrue(index_file.exists())
        
        with open(index_file, "r", encoding="utf-8") as f:
            index_data = json.load(f)
        self.assertEqual(len(index_data), 1)
        self.assertEqual(index_data[0]["title_zh"], "涩谷区亲子活动")
        self.assertEqual(index_data[0]["ward"], "渋谷区")
        
        # 验证每日事件文件是否生成
        event_day_file = self.temp_events_dir / "2026-06-01.json"
        self.assertTrue(event_day_file.exists())
        
        with open(event_day_file, "r", encoding="utf-8") as f:
            day_data = json.load(f)
        self.assertEqual(len(day_data), 1)
        self.assertEqual(day_data[0]["id"], "evt_20260601_000")
        self.assertEqual(day_data[0]["ai_score"], 85)
        
        # 验证 meta.json 是否生成
        meta_file = self.temp_data_dir / "meta.json"
        self.assertTrue(meta_file.exists())
        
        with open(meta_file, "r", encoding="utf-8") as f:
            meta_data = json.load(f)
        self.assertEqual(meta_data["total_events"], 1)
        self.assertEqual(meta_data["statistics"]["by_ward"]["渋谷区"], 1)

if __name__ == "__main__":
    unittest.main()

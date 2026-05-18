import unittest
from processor.cleaner import Cleaner

class TestCleaner(unittest.TestCase):
    def test_deduplication_basic(self):
        """测试基础的去重功能：相同标题、日期和区的活动应被合并"""
        events = [
            {
                "title_ja": "親子で楽しむ工作教室",
                "date": "2026-06-01",
                "ward": "新宿区",
                "source_type": "supplementary",
                "source_name": "ikoyo"
            },
            {
                "title_ja": "親子で楽しむ工作教室",
                "date": "2026-06-01",
                "ward": "新宿区",
                "source_type": "supplementary",
                "source_name": "walkerplus"
            }
        ]
        
        result = Cleaner.deduplicate(events)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["source_name"], "ikoyo") # 保留先进入的

    def test_official_priority(self):
        """测试优先级覆盖：官方来源应覆盖其他聚合来源"""
        events = [
            {
                "title_ja": "夏祭り",
                "date": "2026-08-15",
                "ward": "渋谷区",
                "source_type": "supplementary",
                "source_name": "ikoyo"
            },
            {
                "title_ja": "夏祭り",
                "date": "2026-08-15",
                "ward": "渋谷区",
                "source_type": "official",
                "source_name": "shibuya-city-neuvola"
            }
        ]
        
        result = Cleaner.deduplicate(events)
        self.assertEqual(len(result), 1)
        # 应该被 official 的覆盖
        self.assertEqual(result[0]["source_type"], "official")
        self.assertEqual(result[0]["source_name"], "shibuya-city-neuvola")

    def test_punctuation_ignore(self):
        """测试去重时的标点忽略机制"""
        events = [
            {
                "title_ja": "【無料】親子体操教室！",
                "date": "2026-07-10",
                "ward": "港区"
            },
            {
                "title_ja": "無料 親子体操教室",
                "date": "2026-07-10",
                "ward": "港区"
            }
        ]
        
        result = Cleaner.deduplicate(events)
        self.assertEqual(len(result), 1)

if __name__ == "__main__":
    unittest.main()

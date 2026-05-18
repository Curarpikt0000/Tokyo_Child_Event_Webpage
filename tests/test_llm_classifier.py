import unittest
from unittest.mock import patch, MagicMock
from processor.llm_classifier import LLMClassifier, EventClassification

class TestLLMClassifier(unittest.TestCase):
    
    @patch("processor.llm_classifier.genai.Client")
    @patch("processor.llm_classifier.config.get_models")
    def setUp(self, mock_get_models, mock_client):
        # 模拟 config 返回的模型
        mock_get_models.return_value = ("gemini-1.5-flash", "gemini-1.5-pro")
        
        # 模拟 Vertex 客户端
        self.mock_vertex_client = MagicMock()
        mock_client.return_value = self.mock_vertex_client
        
        self.classifier = LLMClassifier()

    def test_process_batch_success(self):
        """测试 LLM 成功返回时的解析与合并逻辑"""
        events = [
            {
                "title_ja": "親子で楽しむ工作教室",
                "date": "2026-06-01",
                "ward": "新宿区",
                "source_name": "新宿区公式"
            }
        ]
        
        # 模拟 LLM 的响应
        mock_response = MagicMock()
        mock_response.parsed = EventClassification(
            title_zh="港区亲子手工课",
            age_min=3,
            age_max=8,
            type="arts",
            score_reasoning="教育:15 + 趣味:20 + 稀缺:10 + 友好:25 = 70",
            ai_score=70,
            ai_tags=["免费", "室内", "亲子互动"],
            summary_zh="和孩子一起做手工的亲子教室，非常有意思哦。",
            rain_ok=True
        )
        self.classifier.vertex_client.models.generate_content.return_value = mock_response
        
        # 为了加速测试，mock掉 time.sleep
        with patch("processor.llm_classifier.time.sleep"):
            results = self.classifier.process_batch(events)
            
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["ai_score"], 70)
        self.assertEqual(results[0]["title_zh"], "港区亲子手工课")
        self.assertEqual(results[0]["type"], "arts")
        self.assertEqual(results[0]["title_ja"], "親子で楽しむ工作教室") # 原有字段保留

    def test_process_batch_fallback(self):
        """测试所有模型调用失败时的兜底逻辑"""
        events = [
            {
                "title_ja": "未知のイベント",
                "date": "2026-06-01"
            }
        ]
        
        # 模拟 API 抛出异常
        self.classifier.vertex_client.models.generate_content.side_effect = Exception("API 报错")
        self.classifier.studio_client = None # 模拟没有配置 AI Studio 兜底
        
        with patch("processor.llm_classifier.time.sleep"):
            results = self.classifier.process_batch(events)
            
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["ai_score"], 60) # 兜底分数
        self.assertEqual(results[0]["title_zh"], "未知のイベント")
        self.assertEqual(results[0]["type"], "outdoor") # 兜底类型
        self.assertTrue("处理失败" in results[0]["score_reasoning"])

if __name__ == "__main__":
    unittest.main()

"""
文件功能：调用 LLM 对活动进行分类、评分、摘要（基于 Gemini Flash / Pro）
实现方式：使用 google-genai SDK 结合 Pydantic 强制格式化输出，实施级联回退（Vertex -> AI Studio）
主要模块：LLMClassifier
输入输出：接收清洗后的事件列表，分批处理，返回打好标签的完整列表
依赖关系：google.genai, pydantic, config
"""

import json
import logging
import time
from typing import List
from pathlib import Path

from pydantic import BaseModel, Field
from google import genai
from google.genai import types

import config

logger = logging.getLogger(__name__)

# 定义 LLM 输出的数据结构
class EventClassification(BaseModel):
    title_zh: str = Field(description="活动中文标题（简洁直白，如 涩谷区亲子手工艺课，20字以内）")
    age_min: int = Field(description="最低适宜年龄（0-10）")
    age_max: int = Field(description="最高适宜年龄（0-10）")
    type: str = Field(description="活动类型。只能从以下选择：outdoor, arts, science, sports, culture, nature, museum, performance")
    score_reasoning: str = Field(description="评分推理过程：基于教育、趣味、稀缺、友好四个维度进行分析。")
    ai_score: int = Field(description="最终总分（1-100分）。四个维度满分各25分相加。")
    ai_tags: list[str] = Field(description="活动标签，如免费、室内、无需预约、亲子互动等，最多选4个")
    summary_zh: str = Field(description="中文简短摘要（50字以内），口语化，像当地妈妈的分享。")
    rain_ok: bool = Field(description="下雨天是否可参加")
    date_start: str = Field(description="活动的举办开始日期，必须是 YYYY-MM-DD 格式。若未提及，默认为该活动的抓取日期。")
    date_end: str = Field(description="活动的举办结束日期，必须是 YYYY-MM-DD 格式。如果活动仅在一日发生，则与 date_start 相同。")
    event_period: str = Field(description="人类可读的活动时间段，如 '5月20日-6月15日 10:00-12:00'。必须从原文抽取。")

def load_existing_annotations(events_dir: Path) -> dict:
    """扫描 events 目录下的所有 YYYY-MM-DD.json，加载已有的 AI 标注结果"""
    cache = {}
    if not events_dir.exists():
        return cache
        
    for json_file in events_dir.glob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                events = json.load(f)
                if not isinstance(events, list):
                    continue
                for e in events:
                    url = e.get("source_url")
                    # 必须保证有 source_url 且已被 AI 处理过
                    if url and e.get("summary_zh") and e.get("summary_zh") != "无可用摘要":
                        cache[url] = {
                            "title_zh": e.get("title_zh"),
                            "age_min": e.get("age_min"),
                            "age_max": e.get("age_max"),
                            "type": e.get("type"),
                            "score_reasoning": e.get("score_reasoning", ""),
                            "ai_score": e.get("ai_score"),
                            "ai_tags": e.get("ai_tags", []),
                            "summary_zh": e.get("summary_zh"),
                            "rain_ok": e.get("rain_ok", False),
                            "indoor": e.get("indoor", False),
                            "date_start": e.get("date_start", e.get("date")),
                            "date_end": e.get("date_end", e.get("date")),
                            "event_period": e.get("event_period", e.get("date")),
                        }
        except Exception as err:
            logger.warning(f"读取历史数据文件 {json_file} 失败: {err}")
            
    logger.info(f"成功从历史数据中加载了 {len(cache)} 条已标注的活动缓存")
    return cache


class LLMClassifier:
    def __init__(self):
        self.primary_model, self.fallback_model = config.get_models()
        # 初始化 Vertex 客户端 (主力)
        try:
            self.vertex_client = genai.Client(
                vertexai=True, 
                project=config.VERTEX_AI_PROJECT, 
                location=config.VERTEX_AI_LOCATION
            )
            logger.info("Vertex AI 客户端初始化成功")
        except Exception as e:
            logger.warning(f"Vertex AI 初始化失败，将全部使用 AI Studio 回退: {e}")
            self.vertex_client = None

        # 初始化 AI Studio 客户端 (兜底)
        if config.AI_STUDIO_API_KEY:
            self.studio_client = genai.Client(api_key=config.AI_STUDIO_API_KEY)
        else:
            self.studio_client = None
            
        # 加载历史缓存
        try:
            self.cache = load_existing_annotations(Path(config.EVENTS_DIR))
        except Exception as e:
            logger.warning(f"加载 AI 历史缓存失败: {e}")
            self.cache = {}

    def _build_prompt(self, event: dict) -> str:
        """构建包含打分逻辑和时间提取的 Prompt"""
        return f"""
请扮演一位居住在东京多年的资深幼教兼两娃妈妈，为这个儿童活动进行分类和打分。

活动信息:
- 标题: {event.get('title_ja')}
- 来源: {event.get('source_name')}
- 举办区: {event.get('ward')}
- 默认抓取日期: {event.get('date')}

【时间提取规则】
1. 从日文标题和正文里分析活动的真实举办开始日期与结束日期，转换为 'YYYY-MM-DD' 格式，填入 `date_start` 和 `date_end`。结合活动年份上下文（默认为今年 2026 年）。如果原文中没有提及区间而只是一个单日，则两个字段都填默认抓取日期 {event.get('date')}。
2. 提炼出一个简短、可读的活动时间范围文本放在 `event_period` 中，如“5月20日(周三)-6月15日(周一) 10:00-12:00”或“5月20日 13:00”。若实在没有时间范围，可以直接将默认抓取日期 {event.get('date')} 填入作为保底。

【评分规则 (1-100分)】请严格按以下四个维度（各25分）进行累加：
1. 教育与启发 (0-25分): 是否能学知识/锻炼技能。
2. 趣味与互动 (0-25分): 孩子是否能动手、是否沉浸。
3. 稀缺与独特 (0-25分): 是否是一年一度/名额极少/特别体验。
4. 父母友好度 (0-25分): 基础10分，免费(+5)，室内(+5)，免预约(+5)。

【文案规范 (humanizer-zh)】
1. 翻译活动标题为中文放在 `title_zh` 中，务必通顺口语化，20字以内。
2. 摘要必须在50字以内，像一个妈妈发朋友圈分享，简练、直接、有温度。
3. 绝对不要使用：此外、至关重要、充满活力、深入探讨、提供无缝体验等 AI 常用翻译腔词汇。
4. 用具体细节替代空洞描述（如"免费入场"代替"经济实惠"）。
"""

    def process_batch(self, batch: list[dict]) -> list[dict]:
        """处理一批数据（串行调用 LLM）"""
        results = []
        for event in batch:
            url = event.get("source_url")
            # 优先从已有的缓存数据复用标注结果
            if url and url in self.cache:
                for k, v in self.cache[url].items():
                    if k == "image_url" and not v and event.get("image_url"):
                        continue
                    event[k] = v
                logger.info(f"  → [缓存命中] 复用历史 AI 标注: {event.get('title_ja') or event.get('title_zh')}")
                results.append(event)
                continue
                
            prompt = self._build_prompt(event)
            parsed_result = self._call_llm_with_fallback(prompt)
            
            if parsed_result:
                # 将 LLM 输出合并到 event
                event.update(parsed_result.model_dump())
            else:
                # 兜底默认值
                logger.warning(f"处理失败，使用默认值: {event.get('title_ja')}")
                event.update({
                    "title_zh": event.get("title_ja", "儿童活动"),
                    "age_min": 0, "age_max": 10, "type": "outdoor",
                    "score_reasoning": "处理失败，自动给予基础分",
                    "ai_score": 60, "ai_tags": [],
                    "summary_zh": "无可用摘要", "rain_ok": False,
                    "date_start": event.get("date"),
                    "date_end": event.get("date"),
                    "event_period": event.get("date")
                })
            results.append(event)
            # 依照规则，串行延迟
            time.sleep(config.LLM_REQUEST_DELAY)
            
        return results

    def _call_llm_with_fallback(self, prompt: str) -> EventClassification | None:
        """级联调用逻辑：Vertex Flash -> Vertex Pro -> AI Studio"""
        schema = EventClassification
        
        # 尝试 Vertex Flash
        if self.vertex_client and self.primary_model:
            try:
                res = self.vertex_client.models.generate_content(
                    model=self.primary_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=schema,
                    )
                )
                return res.parsed
            except Exception as e:
                logger.warning(f"主模型 ({self.primary_model}) 失败: {e}，尝试 fallback")

        # 尝试 Vertex Pro
        if self.vertex_client and self.fallback_model:
            try:
                res = self.vertex_client.models.generate_content(
                    model=self.fallback_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=schema,
                    )
                )
                return res.parsed
            except Exception as e:
                logger.warning(f"备用模型 ({self.fallback_model}) 失败: {e}，尝试 AI Studio")

        # 尝试 AI Studio
        if self.studio_client and self.primary_model:
            try:
                res = self.studio_client.models.generate_content(
                    model=self.primary_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=schema,
                    )
                )
                return res.parsed
            except Exception as e:
                logger.error(f"所有 LLM 通道均失败 (最后错误: {e})")
                return None

    def process_all(self, events: list[dict]) -> list[dict]:
        """批处理入口"""
        logger.info(f"开始 LLM 标注，总条数: {len(events)}")
        processed = []
        batch_size = config.LLM_BATCH_SIZE
        
        for i in range(0, len(events), batch_size):
            batch = events[i:i+batch_size]
            logger.info(f"处理批次 {i//batch_size + 1}, 大小 {len(batch)}")
            processed.extend(self.process_batch(batch))
            
        return processed

"""
文件功能：数据清洗与去重
实现方式：基于 (标题, 日期, 区) 生成唯一哈希进行去重。如果发生冲突，官方数据覆盖补充来源数据。
主要模块：Cleaner
输入输出：接收多个数据源汇总的原始列表，输出去重后的列表
依赖关系：hashlib, datetime
"""

import hashlib
import logging
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

class Cleaner:
    @staticmethod
    def _clean_title(title: str) -> str:
        """
        清洗日文标题以提高比对准确率
        """
        title = title.lower()
        # 移除常见修饰符、标点及分类词
        for word in ["【", "】", "[", "]", "（", "）", "(", ")", "特別", "イベント", "開催", "親子", "教室", "講座", "体験"]:
            title = title.replace(word, "")
        return "".join(c for c in title if c.isalnum())

    @staticmethod
    def _is_similar(title1: str, title2: str) -> bool:
        """
        判断两个标题在清洗后是否具有 80% 以上的相似度
        """
        t1 = Cleaner._clean_title(title1)
        t2 = Cleaner._clean_title(title2)
        if not t1 or not t2:
            return False
        return SequenceMatcher(None, t1, t2).ratio() >= 0.8

    @staticmethod
    def deduplicate(events: list[dict]) -> list[dict]:
        """
        功能描述：跨源去重逻辑
        规则：
        1. 针对同一天的活动，检查是否有 source_url 相同，或标题相似度 >= 80% 的事件。
        2. 如果判定为相同活动，官方来源 (official) 优先级高于聚合平台 (supplementary)。
        """
        logger.info(f"清洗前总数量: {len(events)}")
        
        # 按日期分组
        events_by_date = {}
        for event in events:
            date = event.get("date")
            title = event.get("title_ja")
            if not date or not title:
                continue
            events_by_date.setdefault(date, []).append(event)
            
        result = []
        for date_str, day_events in sorted(events_by_date.items()):
            unique_day_events = []
            for ev in day_events:
                duplicate_found = False
                for idx, existing in enumerate(unique_day_events):
                    # 检查 1: 原始 URL 精确一致
                    same_url = (ev.get("source_url") and ev.get("source_url") == existing.get("source_url"))
                    # 检查 2: 标题相似度 >= 80%
                    similar_title = Cleaner._is_similar(ev.get("title_ja", ""), existing.get("title_ja", ""))
                    
                    if same_url or similar_title:
                        duplicate_found = True
                        # 覆盖判定：official 优先于 supplementary
                        existing_type = existing.get("source_type", "supplementary")
                        new_type = ev.get("source_type", "supplementary")
                        
                        if new_type == "official" and existing_type != "official":
                            logger.debug(f"去重覆盖: 官方数据 [{ev['title_ja']}] 覆盖 {existing['source_name']}")
                            unique_day_events[idx] = ev
                        break
                if not duplicate_found:
                    unique_day_events.append(ev)
            result.extend(unique_day_events)
            
        logger.info(f"清洗去重后总数量: {len(result)}")
        return result


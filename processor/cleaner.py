"""
文件功能：数据清洗与去重
实现方式：基于 (标题, 日期, 区) 生成唯一哈希进行去重。如果发生冲突，官方数据覆盖补充来源数据。
主要模块：Cleaner
输入输出：接收多个数据源汇总的原始列表，输出去重后的列表
依赖关系：hashlib, datetime
"""

import hashlib
import logging

logger = logging.getLogger(__name__)

class Cleaner:
    @staticmethod
    def _generate_hash(event: dict) -> str:
        """
        生成事件唯一标识，用于跨源去重
        基于：日期 + 区 + 清理后的日文标题
        """
        date = event.get("date", "")
        ward = event.get("ward", "")
        title = event.get("title_ja", "").strip().lower()
        
        # 去掉常见标点和空格以提高匹配率
        title = "".join(c for c in title if c.isalnum())
        
        raw_str = f"{date}_{ward}_{title}"
        return hashlib.md5(raw_str.encode("utf-8")).hexdigest()

    @staticmethod
    def deduplicate(events: list[dict]) -> list[dict]:
        """
        功能描述：跨源去重逻辑
        规则：官方来源 (official) 优先级高于聚合平台 (supplementary)
        """
        dedup_map = {}
        logger.info(f"清洗前总数量: {len(events)}")
        
        for event in events:
            # 基础过滤：跳过没有日期或标题的无效数据
            if not event.get("date") or not event.get("title_ja"):
                continue
                
            event_hash = Cleaner._generate_hash(event)
            
            if event_hash in dedup_map:
                existing = dedup_map[event_hash]
                # 优先级判定：official > supplementary
                existing_type = existing.get("source_type", "supplementary")
                new_type = event.get("source_type", "supplementary")
                
                if new_type == "official" and existing_type != "official":
                    logger.debug(f"去重覆盖: 官方数据 [{event['title_ja']}] 覆盖 {existing['source_name']}")
                    dedup_map[event_hash] = event
            else:
                dedup_map[event_hash] = event
                
        result = list(dedup_map.values())
        logger.info(f"清洗去重后总数量: {len(result)}")
        return result

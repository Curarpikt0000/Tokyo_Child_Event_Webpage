"""
文件功能：数据输出逻辑，按格式生成 index.json 与每日事件文件 YYYY-MM-DD.json
实现方式：基于 datetime 做日期区间过滤，按日分组写出详细 JSON 文件，同时压缩主 index.json 的体积。
主要模块：JSONWriter
输入输出：接收 LLM 标注后的完整活动列表，在 docs/data/ 目录下写出对应静态数据
依赖关系：json, os, datetime, config
"""

import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import config

logger = logging.getLogger(__name__)

class JSONWriter:
    def __init__(self):
        self.data_dir = config.DATA_DIR
        self.events_dir = config.EVENTS_DIR

    def _filter_by_date_range(self, events: list[dict]) -> list[dict]:
        """过滤保留符合时间窗口的事件 (过去 DAYS_PAST 天到未来 DAYS_FUTURE 天)"""
        today = datetime.now().date()
        start_date = today - timedelta(days=config.DAYS_PAST)
        end_date = today + timedelta(days=config.DAYS_FUTURE)
        
        filtered = []
        for e in events:
            date_str = e.get("date")
            if not date_str:
                continue
            try:
                e_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                if start_date <= e_date <= end_date:
                    filtered.append(e)
            except ValueError:
                logger.warning(f"日期格式无效，跳过: {date_str}")
                
        logger.info(f"日期过滤：从 {len(events)} 条中保留了 {len(filtered)} 条有效活动")
        return filtered

    def write(self, events: list[dict]) -> None:
        """核心写出入口"""
        # 1. 过滤合适日期范围
        valid_events = self._filter_by_date_range(events)
        
        # 2. 为每一个事件生成唯一 ID (按日期分组，分配自增序列)
        by_date = defaultdict(list)
        for e in valid_events:
            by_date[e["date"]].append(e)
            
        # 排序并分配 ID
        final_events = []
        for date_str, day_events in sorted(by_date.items()):
            for idx, event in enumerate(day_events):
                # evt_YYYYMMDD_NNN
                date_compact = date_str.replace("-", "")
                event_id = f"evt_{date_compact}_{idx:03d}"
                event["id"] = event_id
                final_events.append(event)

        # 3. 写出每日详细文件
        grouped_by_date = defaultdict(list)
        for e in final_events:
            grouped_by_date[e["date"]].append(e)
            
        # 先清空或写入新的 YYYY-MM-DD.json
        for date_str, day_events in grouped_by_date.items():
            file_path = self.events_dir / f"{date_str}.json"
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(day_events, f, ensure_ascii=False, indent=2)
                logger.debug(f"写出每日事件文件: {file_path}")
            except Exception as e:
                logger.error(f"写出每日文件失败 {date_str}: {e}")

        # 4. 写出压缩的 index.json (轻量索引)
        index_list = []
        for e in final_events:
            index_list.append({
                "id": e["id"],
                "date": e["date"],
                "title_zh": e.get("title_zh", e.get("title_ja", "亲子活动")[:20]),
                "type": e.get("type", "outdoor"),
                "ward": e.get("ward", ""),
                "age_min": e.get("age_min", 0),
                "age_max": e.get("age_max", 10),
                "free": e.get("free", True),
                "indoor": not e.get("rain_ok", True) # 依照 AGENTS.md 映射，或者直接映射 rain_ok -> indoor
            })
            
        index_path = self.data_dir / "index.json"
        try:
            with open(index_path, "w", encoding="utf-8") as f:
                json.dump(index_list, f, ensure_ascii=False, indent=2)
            logger.info(f"写出轻量索引成功: {index_path}，包含 {len(index_list)} 条记录")
        except Exception as e:
            logger.error(f"写出轻量索引失败: {e}")

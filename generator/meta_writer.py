"""
文件功能：写出 meta.json 包含统计信息和时间戳
实现方式：分析 index.json 统计区、活动类型以及时间，写出轻量级元数据。
主要模块：MetaWriter
输入输出：无输入参数，根据 DATA_DIR/index.json 生成 meta.json
依赖关系：json, datetime, config
"""

import json
import logging
from collections import Counter
from datetime import datetime

import config

logger = logging.getLogger(__name__)

class MetaWriter:
    def __init__(self):
        self.data_dir = config.DATA_DIR

    def write(self) -> None:
        """读取 index.json，生成统计信息元数据，写出到 meta.json"""
        index_path = self.data_dir / "index.json"
        meta_path = self.data_dir / "meta.json"
        
        if not index_path.exists():
            logger.warning(f"由于 index.json 不存在，无法生成 meta.json")
            return
            
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                events = json.load(f)
                
            total_count = len(events)
            
            # 统计各区数量
            ward_counts = dict(Counter(e.get("ward", "未知") for e in events))
            
            # 统计各类型数量
            type_counts = dict(Counter(e.get("type", "outdoor") for e in events))
            
            meta_data = {
                "last_updated": datetime.now().isoformat(),
                "total_events": total_count,
                "statistics": {
                    "by_ward": ward_counts,
                    "by_type": type_counts
                }
            }
            
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta_data, f, ensure_ascii=False, indent=2)
            logger.info(f"写出元数据成功: {meta_path}")
            
        except Exception as e:
            logger.error(f"写出元数据失败: {e}")

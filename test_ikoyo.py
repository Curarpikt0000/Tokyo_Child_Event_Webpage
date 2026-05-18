"""用于测试 いこーよ 爬虫"""
import sys
sys.path.insert(0, '/Users/chaojin/Antigravity Projects/Tokyo_Child_Event_Webpage')

import config
from scraper.supplementary.ikoyo import IkoyoScraper

if __name__ == "__main__":
    print("开始测试 いこーよ 爬虫...")
    # 从 config.py 获取数据源配置
    source_config = config.SUPPLEMENTARY_SOURCES.get("ikoyo")
    
    if not source_config:
        print("未在 config.py 中找到 ikoyo 配置！")
        sys.exit(1)
        
    scraper = IkoyoScraper(source_config)
    events = scraper.fetch()
    
    print(f"\n✅ 成功抓取到 {len(events)} 条活动数据！")
    if events:
        print("\n前 3 条数据预览：")
        for i, ev in enumerate(events[:3], 1):
            print(f"{i}. [{ev['date']}] {ev['title_ja']}")
            print(f"   来源: {ev['source_url']}")
            print(f"   免费: {ev['free']}, 价格: {ev['price']}")
            print("-" * 40)

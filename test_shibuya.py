"""用于测试 渋谷区 爬虫"""
import sys
sys.path.insert(0, '/Users/chaojin/Antigravity Projects/Tokyo_Child_Event_Webpage')

import config
from scraper.wards.shibuya import ShibuyaScraper

if __name__ == "__main__":
    print("开始测试 渋谷区 爬虫...")
    # 从 config.py 获取数据源配置
    source_config = config.WARD_SOURCES.get("渋谷区")
    
    if not source_config:
        print("未在 config.py 中找到 渋谷区 配置！")
        sys.exit(1)
        
    scraper = ShibuyaScraper(source_config)
    events = scraper.fetch()
    
    print(f"\n✅ 成功抓取到 {len(events)} 条去重后的活动/新闻数据！")
    if events:
        print("\n前 5 条数据预览：")
        for i, ev in enumerate(events[:5], 1):
            print(f"{i}. [{ev['date']}] {ev['title_ja']}")
            print(f"   来源: {ev['source_url']}")
            print(f"   免费: {ev['free']}, 价格: {ev['price']}")
            print("-" * 40)
    else:
        print("没有抓到数据。HTML 已保存至 shibuya_dump.html 供分析。")

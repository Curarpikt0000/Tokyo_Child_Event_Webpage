"""用于测试 model_discovery 模块的快速脚本"""
import sys
sys.path.insert(0, '/Users/chaojin/Antigravity Projects/Tokyo_Child_Event_Webpage')

from utils.model_discovery import discover_best_models

primary, fallback = discover_best_models(
    project='wechatgenerator-494007',
    location='us-central1',
    api_key='AIzaSyAVGvlE0se8uBdzU_sVh_nlj1kzDl2QGRc'
)
print(f"主力模型: {primary}")
print(f"回退模型: {fallback}")

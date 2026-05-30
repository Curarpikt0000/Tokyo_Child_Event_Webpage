"""用于测试 model_discovery 模块的快速脚本"""
import os
import sys
sys.path.insert(0, '/Users/chaojin/Antigravity Projects/Tokyo_Child_Event_Webpage')

from utils.model_discovery import discover_best_models

api_key = os.environ.get("GEMINI_API_KEY", "")

primary, fallback = discover_best_models(
    project='wechatgenerator-494007',
    location='us-central1',
    api_key=api_key
)
print(f"主力模型: {primary}")
print(f"回退模型: {fallback}")

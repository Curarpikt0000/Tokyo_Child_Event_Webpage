"""
文件功能：动态模型寻址与测活系统（适配 google-genai 新 SDK）
实现方式：通过 client.models.list() 枚举实际可用模型，权重打分后返回最优 Pro 和 Flash 模型
主要模块：discover_best_models（主入口）、_score_model（打分逻辑）
输入输出：接收 project/location/api_key，返回 (primary_model, fallback_model) 元组
依赖关系：google-genai（新统一 SDK，同时支持 Vertex AI 和 AI Studio）
创建日期：2026-05-18
移植自：AI_Blog_Generator/utils/model_discovery.py（升级至新 SDK）
"""

from google import genai


# ============================================================
# 模型名称缓存（避免重复调用 list_models）
# ============================================================
_cache: dict = {}


def _score_model(name: str) -> int:
    """
    功能描述：对模型名称进行特征权重打分，分数越高越优先使用
    实现逻辑：按版本号升权，pro > flash；排除 preview/exp/tts/image 等特殊用途型号
    参数说明：name (str) - 模型名称（小写）
    返回值：int - 打分结果，-1 表示不可用于通用文本生成
    """
    # 过滤掉非文本生成模型
    for skip in ("embedding", "tts", "image", "audio", "vision", "computer-use"):
        if skip in name:
            return -1

    score = 0

    # 版本号权重（越新越高）
    if "gemini-3.1" in name:
        score += 6000
    elif "gemini-3" in name:
        score += 5000
    elif "gemini-2.5" in name:
        score += 4000
    elif "gemini-2.0" in name:
        score += 3000
    elif "gemini-1.5" in name:
        score += 2000
    elif "gemini-1.0" in name:
        score += 500

    # 类型权重
    if "pro" in name:
        score += 800
    elif "flash" in name:
        score += 300

    # 扣分项：不稳定版本
    if "preview" in name or "exp" in name:
        score -= 10000  # 极大扣分，避免选到未上线的内测版（Vertex 中常有未开放的占位模型导致 404）
    if "lite" in name:
        score -= 200  # lite 版本轻量级，排在 flash 后
    if "8b" in name:
        score -= 300

    return score


def _extract_short_name(full_name: str) -> str:
    """
    功能描述：从完整模型路径中提取短名称
    实现逻辑：去掉 'publishers/google/models/' 和 'models/' 前缀
    参数说明：full_name (str) - 如 'publishers/google/models/gemini-2.5-flash'
    返回值：str - 如 'gemini-2.5-flash'
    """
    name = full_name
    for prefix in ("publishers/google/models/", "models/"):
        name = name.replace(prefix, "")
    return name


def discover_best_models(
    project: str,
    location: str,
    api_key: str = "",
) -> tuple[str, str]:
    """
    功能描述：动态发现当前账户下最优的 Pro 级模型（主力）和 Flash 级模型（回退）
    实现逻辑：
        1. 优先使用 Vertex AI（project + ADC 认证）枚举可用模型
        2. Vertex AI 不可用时，降级到 AI Studio（api_key）
        3. 对所有可用模型打分，分别选出最优 Pro 和最优 Flash
        4. 结果缓存，避免重复调用
    参数说明：
        project (str): GCP 项目 ID
        location (str): Vertex AI 区域（如 us-central1）
        api_key (str): AI Studio API Key（Vertex AI 不可用时的兜底）
    返回值：
        tuple[str, str]: (primary_model, fallback_model)
            primary_model - 最优 Pro 或最强 Flash（用于主力分类任务）
            fallback_model - 最快 Flash（用于 429/500 降级）
    异常：
        所有 API 报错均被捕获，退回预设兜底常量
    """
    cache_key = f"vertex:{project}:{location}"
    if cache_key in _cache:
        return _cache[cache_key]

    # 默认兜底（绝对保底）
    default_primary = "gemini-2.5-flash"
    default_fallback = "gemini-2.0-flash"

    # ---- 第一优先级：Vertex AI ----
    if project and location:
        try:
            client = genai.Client(vertexai=True, project=project, location=location)
            models = list(client.models.list())

            best_pro_score = -1
            best_pro_name = None
            best_flash_score = -1
            best_flash_name = None

            for m in models:
                short_name = _extract_short_name(m.name)
                name_lower = short_name.lower()
                score = _score_model(name_lower)
                if score < 0:
                    continue

                # 区分 Pro 和 Flash 两个赛道
                if "pro" in name_lower and score > best_pro_score:
                    best_pro_score = score
                    best_pro_name = short_name
                elif "flash" in name_lower and "pro" not in name_lower and score > best_flash_score:
                    best_flash_score = score
                    best_flash_name = short_name

            primary = best_pro_name or best_flash_name or default_primary
            fallback = best_flash_name or default_fallback

            # Flash 稳定性保障：如果 primary 是 preview，fallback 选稳定版
            if "preview" in fallback.lower():
                # 再找一个非 preview 的 flash
                for m in models:
                    short = _extract_short_name(m.name)
                    if "flash" in short.lower() and "preview" not in short.lower() and "pro" not in short.lower():
                        fallback = short
                        break

            print(f"[模型发现] Vertex AI ✅ 主力: {primary} | 回退: {fallback}")
            _cache[cache_key] = (primary, fallback)
            return primary, fallback

        except Exception as e:
            print(f"[模型发现] Vertex AI 枚举失败 ({e})，尝试 AI Studio 兜底")

    # ---- 第二优先级：AI Studio 兜底 ----
    if api_key:
        try:
            client = genai.Client(api_key=api_key)
            models = list(client.models.list())

            best_pro_score = -1
            best_pro_name = None
            best_flash_score = -1
            best_flash_name = None

            for m in models:
                short_name = _extract_short_name(m.name)
                name_lower = short_name.lower()
                score = _score_model(name_lower)
                if score < 0:
                    continue

                if "pro" in name_lower and score > best_pro_score:
                    best_pro_score = score
                    best_pro_name = short_name
                elif "flash" in name_lower and "pro" not in name_lower and score > best_flash_score:
                    best_flash_score = score
                    best_flash_name = short_name

            primary = best_pro_name or best_flash_name or default_primary
            fallback = best_flash_name or default_fallback

            print(f"[模型发现] AI Studio ✅ 主力: {primary} | 回退: {fallback}")
            _cache[cache_key] = (primary, fallback)
            return primary, fallback

        except Exception as e:
            print(f"[模型发现] AI Studio 枚举失败 ({e})，启用硬编码兜底")

    # ---- 最终兜底 ----
    print(f"[模型发现] 所有链路失败，使用硬编码兜底: {default_primary} / {default_fallback}")
    result = (default_primary, default_fallback)
    _cache[cache_key] = result
    return result

import asyncio
from typing import Optional
from langdetect import detect, DetectorFactory
from langdetect.lang_detect_exception import LangDetectException
import structlog

logger = structlog.get_logger()

# 设置随机种子以获得一致的结果
DetectorFactory.seed = 0

# 语言代码映射
LANGUAGE_MAPPING = {
    'zh-cn': 'zh',
    'zh-tw': 'zh',
    'en': 'en',
    'ja': 'ja',
    'ko': 'ko',
    'fr': 'fr',
    'de': 'de',
    'es': 'es',
    'it': 'it',
    'pt': 'pt',
    'ru': 'ru',
    'ar': 'ar',
    'th': 'th',
    'vi': 'vi',
    'id': 'id',
    'ms': 'ms',
    'hi': 'hi',
    'tr': 'tr',
    'pl': 'pl',
    'nl': 'nl',
    'sv': 'sv',
    'da': 'da',
    'no': 'no',
    'fi': 'fi',
    'cs': 'cs',
    'hu': 'hu',
    'ro': 'ro',
    'bg': 'bg',
    'hr': 'hr',
    'sk': 'sk',
    'sl': 'sl',
    'et': 'et',
    'lv': 'lv',
    'lt': 'lt',
    'uk': 'uk',
    'be': 'be',
    'mk': 'mk',
    'sq': 'sq',
    'sr': 'sr',
    'bs': 'bs',
    'mt': 'mt',
    'is': 'is',
    'ga': 'ga',
    'cy': 'cy',
    'eu': 'eu',
    'ca': 'ca',
    'gl': 'gl',
    'he': 'he',
    'fa': 'fa',
    'ur': 'ur',
    'bn': 'bn',
    'ta': 'ta',
    'te': 'te',
    'ml': 'ml',
    'kn': 'kn',
    'gu': 'gu',
    'pa': 'pa',
    'ne': 'ne',
    'si': 'si',
    'my': 'my',
    'km': 'km',
    'lo': 'lo',
    'ka': 'ka',
    'am': 'am',
    'sw': 'sw',
    'zu': 'zu',
    'af': 'af',
    'xh': 'xh'
}

async def detect_language(text: str) -> str:
    """
    检测文本语言
    
    Args:
        text: 要检测的文本
        
    Returns:
        检测到的语言代码，如果检测失败返回'en'
    """
    if not text or not text.strip():
        return 'en'
    
    try:
        # 在线程池中运行语言检测以避免阻塞
        loop = asyncio.get_event_loop()
        detected_lang = await loop.run_in_executor(None, detect, text.strip())
        
        # 映射到标准语言代码
        mapped_lang = LANGUAGE_MAPPING.get(detected_lang, detected_lang)
        
        logger.info(
            "Language detected",
            text_preview=text[:50],
            detected_language=detected_lang,
            mapped_language=mapped_lang
        )
        
        return mapped_lang
        
    except LangDetectException as e:
        logger.warning(
            "Language detection failed",
            text_preview=text[:50],
            error=str(e)
        )
        return 'en'  # 默认返回英语
    except Exception as e:
        logger.error(
            "Unexpected error in language detection",
            text_preview=text[:50],
            error=str(e)
        )
        return 'en'

def is_supported_language(lang_code: str) -> bool:
    """
    检查语言代码是否受支持
    
    Args:
        lang_code: 语言代码
        
    Returns:
        是否受支持
    """
    from app.core.config import settings
    return lang_code in settings.SUPPORTED_LANGUAGES

def get_language_name(lang_code: str) -> str:
    """
    获取语言名称
    
    Args:
        lang_code: 语言代码
        
    Returns:
        语言名称
    """
    from app.core.config import settings
    return settings.SUPPORTED_LANGUAGES.get(lang_code, lang_code)

async def detect_language_with_confidence(text: str) -> tuple[str, float]:
    """
    检测语言并返回置信度
    
    Args:
        text: 要检测的文本
        
    Returns:
        (语言代码, 置信度)
    """
    if not text or not text.strip():
        return 'en', 0.0
    
    try:
        from langdetect import detect_langs
        
        loop = asyncio.get_event_loop()
        lang_probs = await loop.run_in_executor(None, detect_langs, text.strip())
        
        if lang_probs:
            best_lang = lang_probs[0]
            mapped_lang = LANGUAGE_MAPPING.get(best_lang.lang, best_lang.lang)
            return mapped_lang, best_lang.prob
        else:
            return 'en', 0.0
            
    except Exception as e:
        logger.error(
            "Language detection with confidence failed",
            text_preview=text[:50],
            error=str(e)
        )
        return 'en', 0.0

def preprocess_text_for_detection(text: str) -> str:
    """
    预处理文本以提高语言检测准确性
    
    Args:
        text: 原始文本
        
    Returns:
        预处理后的文本
    """
    if not text:
        return text
    
    # 移除多余的空白字符
    text = ' '.join(text.split())
    
    # 如果文本太短，尝试保留更多内容
    if len(text) < 20:
        return text
    
    # 如果文本太长，截取前500个字符进行检测
    if len(text) > 500:
        text = text[:500]
    
    return text
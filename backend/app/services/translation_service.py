import asyncio
import hashlib
import json
import time
from typing import Dict, List, Optional, Tuple
from abc import ABC, abstractmethod
import openai
import anthropic
import httpx
from google.cloud import translate_v2 as translate
import structlog

from app.core.config import settings
from app.core.database import get_redis
from app.utils.language_detector import detect_language
from app.utils.text_analyzer import analyze_text_quality

logger = structlog.get_logger()

class TranslationEngine(ABC):
    """翻译引擎抽象基类"""
    
    def __init__(self, name: str):
        self.name = name
        self.redis_client = get_redis()
    
    @abstractmethod
    async def translate(
        self, 
        text: str, 
        source_lang: str, 
        target_lang: str, 
        **kwargs
    ) -> Dict:
        """翻译文本"""
        pass
    
    def _get_cache_key(self, text: str, source_lang: str, target_lang: str, **kwargs) -> str:
        """生成缓存键"""
        content = f"{text}:{source_lang}:{target_lang}:{self.name}:{json.dumps(kwargs, sort_keys=True)}"
        return f"translation:{hashlib.md5(content.encode()).hexdigest()}"
    
    async def _get_cached_translation(self, cache_key: str) -> Optional[Dict]:
        """获取缓存的翻译结果"""
        try:
            cached = self.redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning("Failed to get cached translation", error=str(e))
        return None
    
    async def _cache_translation(self, cache_key: str, result: Dict):
        """缓存翻译结果"""
        try:
            self.redis_client.setex(
                cache_key, 
                settings.TRANSLATION_CACHE_TTL, 
                json.dumps(result)
            )
        except Exception as e:
            logger.warning("Failed to cache translation", error=str(e))

class OpenAITranslationEngine(TranslationEngine):
    """OpenAI翻译引擎"""
    
    def __init__(self):
        super().__init__("openai")
        if settings.OPENAI_API_KEY:
            openai.api_key = settings.OPENAI_API_KEY
    
    async def translate(
        self, 
        text: str, 
        source_lang: str, 
        target_lang: str, 
        model: str = "gpt-3.5-turbo",
        style: str = "natural",
        **kwargs
    ) -> Dict:
        """使用OpenAI进行翻译"""
        start_time = time.time()
        
        # 检查缓存
        cache_key = self._get_cache_key(text, source_lang, target_lang, model=model, style=style)
        cached_result = await self._get_cached_translation(cache_key)
        if cached_result:
            return cached_result
        
        try:
            # 构建提示词
            source_lang_name = settings.SUPPORTED_LANGUAGES.get(source_lang, source_lang)
            target_lang_name = settings.SUPPORTED_LANGUAGES.get(target_lang, target_lang)
            
            style_prompts = {
                "natural": "自然流畅",
                "formal": "正式严谨",
                "casual": "轻松随意",
                "technical": "专业技术",
                "literary": "文学优美"
            }
            
            style_desc = style_prompts.get(style, "自然流畅")
            
            prompt = f"""请将以下{source_lang_name}文本翻译成{target_lang_name}，要求翻译{style_desc}、准确达意：

{text}

请只返回翻译结果，不要包含其他内容。"""
            
            # 调用OpenAI API
            response = await openai.ChatCompletion.acreate(
                model=model,
                messages=[
                    {"role": "system", "content": "你是一个专业的翻译助手，能够提供高质量的多语言翻译服务。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=len(text) * 3  # 预估翻译后长度
            )
            
            translated_text = response.choices[0].message.content.strip()
            processing_time = time.time() - start_time
            
            # 分析翻译质量
            quality_score = await analyze_text_quality(text, translated_text, source_lang, target_lang)
            
            result = {
                "engine": self.name,
                "model": model,
                "translated_text": translated_text,
                "source_language": source_lang,
                "target_language": target_lang,
                "quality_score": quality_score,
                "confidence_score": 0.9,  # OpenAI通常有较高置信度
                "processing_time": processing_time,
                "word_count": len(text.split()),
                "character_count": len(text),
                "metadata": {
                    "style": style,
                    "usage": response.usage._asdict() if response.usage else None
                }
            }
            
            # 缓存结果
            await self._cache_translation(cache_key, result)
            
            return result
            
        except Exception as e:
            logger.error("OpenAI translation failed", error=str(e), text=text[:100])
            raise Exception(f"OpenAI翻译失败: {str(e)}")

class AnthropicTranslationEngine(TranslationEngine):
    """Anthropic Claude翻译引擎"""
    
    def __init__(self):
        super().__init__("anthropic")
        if settings.ANTHROPIC_API_KEY:
            self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    
    async def translate(
        self, 
        text: str, 
        source_lang: str, 
        target_lang: str, 
        model: str = "claude-3-haiku-20240307",
        style: str = "natural",
        **kwargs
    ) -> Dict:
        """使用Claude进行翻译"""
        start_time = time.time()
        
        # 检查缓存
        cache_key = self._get_cache_key(text, source_lang, target_lang, model=model, style=style)
        cached_result = await self._get_cached_translation(cache_key)
        if cached_result:
            return cached_result
        
        try:
            source_lang_name = settings.SUPPORTED_LANGUAGES.get(source_lang, source_lang)
            target_lang_name = settings.SUPPORTED_LANGUAGES.get(target_lang, target_lang)
            
            style_prompts = {
                "natural": "自然流畅",
                "formal": "正式严谨", 
                "casual": "轻松随意",
                "technical": "专业技术",
                "literary": "文学优美"
            }
            
            style_desc = style_prompts.get(style, "自然流畅")
            
            prompt = f"""请将以下{source_lang_name}文本翻译成{target_lang_name}，要求翻译{style_desc}、准确达意：

{text}

请只返回翻译结果，不要包含其他内容。"""
            
            # 调用Claude API
            message = await self.client.messages.create(
                model=model,
                max_tokens=len(text) * 3,
                temperature=0.3,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            translated_text = message.content[0].text.strip()
            processing_time = time.time() - start_time
            
            # 分析翻译质量
            quality_score = await analyze_text_quality(text, translated_text, source_lang, target_lang)
            
            result = {
                "engine": self.name,
                "model": model,
                "translated_text": translated_text,
                "source_language": source_lang,
                "target_language": target_lang,
                "quality_score": quality_score,
                "confidence_score": 0.88,
                "processing_time": processing_time,
                "word_count": len(text.split()),
                "character_count": len(text),
                "metadata": {
                    "style": style,
                    "usage": {
                        "input_tokens": message.usage.input_tokens,
                        "output_tokens": message.usage.output_tokens
                    }
                }
            }
            
            # 缓存结果
            await self._cache_translation(cache_key, result)
            
            return result
            
        except Exception as e:
            logger.error("Anthropic translation failed", error=str(e), text=text[:100])
            raise Exception(f"Claude翻译失败: {str(e)}")

class GoogleTranslationEngine(TranslationEngine):
    """Google翻译引擎"""
    
    def __init__(self):
        super().__init__("google")
        if settings.GOOGLE_API_KEY:
            self.client = translate.Client(api_key=settings.GOOGLE_API_KEY)
    
    async def translate(
        self, 
        text: str, 
        source_lang: str, 
        target_lang: str, 
        **kwargs
    ) -> Dict:
        """使用Google Translate进行翻译"""
        start_time = time.time()
        
        # 检查缓存
        cache_key = self._get_cache_key(text, source_lang, target_lang)
        cached_result = await self._get_cached_translation(cache_key)
        if cached_result:
            return cached_result
        
        try:
            # Google Translate API调用
            result = self.client.translate(
                text,
                source_language=source_lang if source_lang != "auto" else None,
                target_language=target_lang
            )
            
            translated_text = result['translatedText']
            detected_lang = result.get('detectedSourceLanguage', source_lang)
            processing_time = time.time() - start_time
            
            # 分析翻译质量
            quality_score = await analyze_text_quality(text, translated_text, detected_lang, target_lang)
            
            translation_result = {
                "engine": self.name,
                "model": "translate-v3",
                "translated_text": translated_text,
                "source_language": detected_lang,
                "target_language": target_lang,
                "quality_score": quality_score,
                "confidence_score": 0.85,
                "processing_time": processing_time,
                "word_count": len(text.split()),
                "character_count": len(text),
                "metadata": {
                    "detected_language": detected_lang
                }
            }
            
            # 缓存结果
            await self._cache_translation(cache_key, translation_result)
            
            return translation_result
            
        except Exception as e:
            logger.error("Google translation failed", error=str(e), text=text[:100])
            raise Exception(f"Google翻译失败: {str(e)}")

class BaiduTranslationEngine(TranslationEngine):
    """百度翻译引擎"""
    
    def __init__(self):
        super().__init__("baidu")
        self.app_id = settings.BAIDU_APP_ID
        self.secret_key = settings.BAIDU_SECRET_KEY
    
    async def translate(
        self, 
        text: str, 
        source_lang: str, 
        target_lang: str, 
        **kwargs
    ) -> Dict:
        """使用百度翻译进行翻译"""
        start_time = time.time()
        
        # 检查缓存
        cache_key = self._get_cache_key(text, source_lang, target_lang)
        cached_result = await self._get_cached_translation(cache_key)
        if cached_result:
            return cached_result
        
        try:
            import random
            import hashlib
            
            # 百度翻译API参数
            salt = str(random.randint(32768, 65536))
            sign_str = f"{self.app_id}{text}{salt}{self.secret_key}"
            sign = hashlib.md5(sign_str.encode()).hexdigest()
            
            params = {
                'q': text,
                'from': source_lang,
                'to': target_lang,
                'appid': self.app_id,
                'salt': salt,
                'sign': sign
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    'https://fanyi-api.baidu.com/api/trans/vip/translate',
                    data=params
                )
                result = response.json()
            
            if 'trans_result' in result:
                translated_text = result['trans_result'][0]['dst']
                processing_time = time.time() - start_time
                
                # 分析翻译质量
                quality_score = await analyze_text_quality(text, translated_text, source_lang, target_lang)
                
                translation_result = {
                    "engine": self.name,
                    "model": "baidu-translate",
                    "translated_text": translated_text,
                    "source_language": source_lang,
                    "target_language": target_lang,
                    "quality_score": quality_score,
                    "confidence_score": 0.82,
                    "processing_time": processing_time,
                    "word_count": len(text.split()),
                    "character_count": len(text),
                    "metadata": {}
                }
                
                # 缓存结果
                await self._cache_translation(cache_key, translation_result)
                
                return translation_result
            else:
                raise Exception(f"百度翻译API错误: {result}")
                
        except Exception as e:
            logger.error("Baidu translation failed", error=str(e), text=text[:100])
            raise Exception(f"百度翻译失败: {str(e)}")

class TranslationService:
    """翻译服务管理器"""
    
    def __init__(self):
        self.engines = {}
        self._initialize_engines()
    
    def _initialize_engines(self):
        """初始化翻译引擎"""
        if settings.OPENAI_API_KEY:
            self.engines["openai"] = OpenAITranslationEngine()
        
        if settings.ANTHROPIC_API_KEY:
            self.engines["anthropic"] = AnthropicTranslationEngine()
        
        if settings.GOOGLE_API_KEY:
            self.engines["google"] = GoogleTranslationEngine()
        
        if settings.BAIDU_APP_ID and settings.BAIDU_SECRET_KEY:
            self.engines["baidu"] = BaiduTranslationEngine()
    
    async def translate(
        self,
        text: str,
        source_lang: str = "auto",
        target_lang: str = "zh",
        engine: str = "openai",
        **kwargs
    ) -> Dict:
        """单引擎翻译"""
        if not text.strip():
            raise ValueError("翻译文本不能为空")
        
        if len(text) > settings.MAX_TRANSLATION_LENGTH:
            raise ValueError(f"文本长度超过限制({settings.MAX_TRANSLATION_LENGTH}字符)")
        
        # 自动检测语言
        if source_lang == "auto":
            source_lang = await detect_language(text)
        
        # 检查引擎是否可用
        if engine not in self.engines:
            available_engines = list(self.engines.keys())
            if not available_engines:
                raise Exception("没有可用的翻译引擎")
            engine = available_engines[0]  # 使用第一个可用引擎
        
        return await self.engines[engine].translate(text, source_lang, target_lang, **kwargs)
    
    async def compare_translations(
        self,
        text: str,
        source_lang: str = "auto",
        target_lang: str = "zh",
        engines: Optional[List[str]] = None
    ) -> Dict:
        """多引擎翻译对比"""
        if engines is None:
            engines = list(self.engines.keys())
        
        # 自动检测语言
        if source_lang == "auto":
            source_lang = await detect_language(text)
        
        # 并发翻译
        tasks = []
        for engine in engines:
            if engine in self.engines:
                task = self.engines[engine].translate(text, source_lang, target_lang)
                tasks.append((engine, task))
        
        results = {}
        errors = {}
        
        # 执行并发翻译
        for engine, task in tasks:
            try:
                result = await task
                results[engine] = result
            except Exception as e:
                errors[engine] = str(e)
                logger.error(f"Translation failed for engine {engine}", error=str(e))
        
        return {
            "source_text": text,
            "source_language": source_lang,
            "target_language": target_lang,
            "results": results,
            "errors": errors,
            "best_translation": self._select_best_translation(results)
        }
    
    def _select_best_translation(self, results: Dict) -> Optional[Dict]:
        """选择最佳翻译结果"""
        if not results:
            return None
        
        # 根据质量分数选择最佳翻译
        best_result = None
        best_score = 0
        
        for engine, result in results.items():
            score = result.get("quality_score", 0)
            if score > best_score:
                best_score = score
                best_result = result
        
        return best_result
    
    def get_available_engines(self) -> List[str]:
        """获取可用的翻译引擎列表"""
        return list(self.engines.keys())
    
    def get_supported_languages(self) -> Dict[str, str]:
        """获取支持的语言列表"""
        return settings.SUPPORTED_LANGUAGES

# 创建全局翻译服务实例
translation_service = TranslationService()
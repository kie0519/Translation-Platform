from pydantic_settings import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    # 应用基础配置
    APP_NAME: str = "AI Translation Platform"
    DEBUG: bool = True
    VERSION: str = "1.0.0"
    
    # 数据库配置
    DATABASE_URL: str = "postgresql://postgres:postgres123@localhost:5432/translation_db"
    REDIS_URL: str = "redis://localhost:6379"
    
    # JWT配置
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS配置
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:12000",
        "https://work-1-qkpesnnpgroyxhdn.prod-runtime.all-hands.dev",
        "https://work-2-qkpesnnpgroyxhdn.prod-runtime.all-hands.dev"
    ]
    
    # AI API密钥
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    BAIDU_APP_ID: Optional[str] = None
    BAIDU_SECRET_KEY: Optional[str] = None
    YOUDAO_APP_KEY: Optional[str] = None
    YOUDAO_APP_SECRET: Optional[str] = None
    TENCENT_SECRET_ID: Optional[str] = None
    TENCENT_SECRET_KEY: Optional[str] = None
    
    # 翻译配置
    MAX_TRANSLATION_LENGTH: int = 10000
    RATE_LIMIT_PER_MINUTE: int = 100
    DEFAULT_SOURCE_LANGUAGE: str = "auto"
    DEFAULT_TARGET_LANGUAGE: str = "zh"
    
    # 文件上传配置
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_FILE_TYPES: List[str] = ["txt", "docx", "pdf", "srt"]
    UPLOAD_DIR: str = "static/uploads"
    
    # 缓存配置
    CACHE_TTL: int = 3600  # 1小时
    TRANSLATION_CACHE_TTL: int = 86400  # 24小时
    
    # 支持的语言列表
    SUPPORTED_LANGUAGES: dict = {
        "auto": "自动检测",
        "zh": "中文",
        "en": "英语",
        "ja": "日语",
        "ko": "韩语",
        "fr": "法语",
        "de": "德语",
        "es": "西班牙语",
        "it": "意大利语",
        "pt": "葡萄牙语",
        "ru": "俄语",
        "ar": "阿拉伯语",
        "th": "泰语",
        "vi": "越南语",
        "id": "印尼语",
        "ms": "马来语",
        "hi": "印地语",
        "tr": "土耳其语",
        "pl": "波兰语",
        "nl": "荷兰语",
        "sv": "瑞典语",
        "da": "丹麦语",
        "no": "挪威语",
        "fi": "芬兰语",
        "cs": "捷克语",
        "hu": "匈牙利语",
        "ro": "罗马尼亚语",
        "bg": "保加利亚语",
        "hr": "克罗地亚语",
        "sk": "斯洛伐克语",
        "sl": "斯洛文尼亚语",
        "et": "爱沙尼亚语",
        "lv": "拉脱维亚语",
        "lt": "立陶宛语",
        "uk": "乌克兰语",
        "be": "白俄罗斯语",
        "mk": "马其顿语",
        "sq": "阿尔巴尼亚语",
        "sr": "塞尔维亚语",
        "bs": "波斯尼亚语",
        "mt": "马耳他语",
        "is": "冰岛语",
        "ga": "爱尔兰语",
        "cy": "威尔士语",
        "eu": "巴斯克语",
        "ca": "加泰罗尼亚语",
        "gl": "加利西亚语",
        "he": "希伯来语",
        "fa": "波斯语",
        "ur": "乌尔都语",
        "bn": "孟加拉语",
        "ta": "泰米尔语",
        "te": "泰卢固语",
        "ml": "马拉雅拉姆语",
        "kn": "卡纳达语",
        "gu": "古吉拉特语",
        "pa": "旁遮普语",
        "ne": "尼泊尔语",
        "si": "僧伽罗语",
        "my": "缅甸语",
        "km": "高棉语",
        "lo": "老挝语",
        "ka": "格鲁吉亚语",
        "am": "阿姆哈拉语",
        "sw": "斯瓦希里语",
        "zu": "祖鲁语",
        "af": "南非荷兰语",
        "xh": "科萨语"
    }
    
    # 翻译引擎配置
    TRANSLATION_ENGINES: dict = {
        "openai": {
            "name": "OpenAI GPT",
            "enabled": True,
            "models": ["gpt-4", "gpt-3.5-turbo"],
            "default_model": "gpt-3.5-turbo"
        },
        "anthropic": {
            "name": "Claude",
            "enabled": True,
            "models": ["claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
            "default_model": "claude-3-haiku-20240307"
        },
        "google": {
            "name": "Google Translate",
            "enabled": True,
            "models": ["translate-v3"],
            "default_model": "translate-v3"
        },
        "baidu": {
            "name": "百度翻译",
            "enabled": True,
            "models": ["baidu-translate"],
            "default_model": "baidu-translate"
        }
    }

    class Config:
        env_file = ".env"
        case_sensitive = True

# 创建设置实例
settings = Settings()

# 确保上传目录存在
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
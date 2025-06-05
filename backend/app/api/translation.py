from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
import structlog

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.translation import Translation, TranslationComparison
from app.services.translation_service import translation_service
from app.utils.language_detector import detect_language
from app.utils.text_analyzer import extract_keywords, calculate_readability_score

logger = structlog.get_logger()
router = APIRouter()

# Pydantic模型
class TranslationRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000, description="要翻译的文本")
    source_language: str = Field(default="auto", description="源语言代码")
    target_language: str = Field(default="zh", description="目标语言代码")
    engine: str = Field(default="openai", description="翻译引擎")
    model: Optional[str] = Field(default=None, description="具体模型名称")
    style: str = Field(default="natural", description="翻译风格")
    save_to_history: bool = Field(default=True, description="是否保存到历史记录")

class CompareTranslationRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000, description="要翻译的文本")
    source_language: str = Field(default="auto", description="源语言代码")
    target_language: str = Field(default="zh", description="目标语言代码")
    engines: Optional[List[str]] = Field(default=None, description="要对比的翻译引擎列表")
    save_to_history: bool = Field(default=True, description="是否保存到历史记录")

class TranslationResponse(BaseModel):
    id: Optional[int] = None
    source_text: str
    translated_text: str
    source_language: str
    target_language: str
    engine: str
    model: Optional[str] = None
    quality_score: Optional[float] = None
    confidence_score: Optional[float] = None
    processing_time: float
    word_count: int
    character_count: int
    keywords: Optional[List[str]] = None
    readability: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None

class CompareTranslationResponse(BaseModel):
    source_text: str
    source_language: str
    target_language: str
    results: Dict[str, TranslationResponse]
    errors: Dict[str, str]
    best_translation: Optional[TranslationResponse] = None
    comparison_id: Optional[int] = None

@router.post("/translate", response_model=TranslationResponse)
async def translate_text(
    request: TranslationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_active_user)
):
    """
    翻译文本
    """
    try:
        # 执行翻译
        result = await translation_service.translate(
            text=request.text,
            source_lang=request.source_language,
            target_lang=request.target_language,
            engine=request.engine,
            model=request.model,
            style=request.style
        )
        
        # 提取关键词
        keywords = extract_keywords(request.text)
        
        # 计算可读性
        readability = calculate_readability_score(
            result["translated_text"], 
            request.target_language
        )
        
        # 保存到数据库
        translation_record = None
        if request.save_to_history and current_user:
            translation_record = Translation(
                user_id=current_user.id,
                source_text=request.text,
                translated_text=result["translated_text"],
                source_language=result["source_language"],
                target_language=result["target_language"],
                engine=result["engine"],
                model=result.get("model"),
                quality_score=result.get("quality_score"),
                confidence_score=result.get("confidence_score"),
                word_count=result["word_count"],
                character_count=result["character_count"],
                processing_time=result["processing_time"],
                translation_options={
                    "style": request.style,
                    "keywords": keywords,
                    "readability": readability
                }
            )
            db.add(translation_record)
            db.commit()
            db.refresh(translation_record)
            
            # 更新用户统计
            current_user.translation_count += 1
            current_user.words_translated += result["word_count"]
            db.commit()
        
        return TranslationResponse(
            id=translation_record.id if translation_record else None,
            source_text=request.text,
            translated_text=result["translated_text"],
            source_language=result["source_language"],
            target_language=result["target_language"],
            engine=result["engine"],
            model=result.get("model"),
            quality_score=result.get("quality_score"),
            confidence_score=result.get("confidence_score"),
            processing_time=result["processing_time"],
            word_count=result["word_count"],
            character_count=result["character_count"],
            keywords=keywords,
            readability=readability,
            created_at=translation_record.created_at.isoformat() if translation_record else None
        )
        
    except Exception as e:
        logger.error("Translation failed", error=str(e), user_id=current_user.id if current_user else None)
        raise HTTPException(status_code=500, detail=f"翻译失败: {str(e)}")

@router.post("/compare", response_model=CompareTranslationResponse)
async def compare_translations(
    request: CompareTranslationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_active_user)
):
    """
    对比多个翻译引擎的结果
    """
    try:
        # 执行对比翻译
        comparison_result = await translation_service.compare_translations(
            text=request.text,
            source_lang=request.source_language,
            target_lang=request.target_language,
            engines=request.engines
        )
        
        # 转换结果格式
        results = {}
        for engine, result in comparison_result["results"].items():
            keywords = extract_keywords(request.text)
            readability = calculate_readability_score(
                result["translated_text"], 
                request.target_language
            )
            
            results[engine] = TranslationResponse(
                source_text=request.text,
                translated_text=result["translated_text"],
                source_language=result["source_language"],
                target_language=result["target_language"],
                engine=result["engine"],
                model=result.get("model"),
                quality_score=result.get("quality_score"),
                confidence_score=result.get("confidence_score"),
                processing_time=result["processing_time"],
                word_count=result["word_count"],
                character_count=result["character_count"],
                keywords=keywords,
                readability=readability
            )
        
        # 最佳翻译结果
        best_translation = None
        if comparison_result["best_translation"]:
            best_result = comparison_result["best_translation"]
            best_translation = TranslationResponse(
                source_text=request.text,
                translated_text=best_result["translated_text"],
                source_language=best_result["source_language"],
                target_language=best_result["target_language"],
                engine=best_result["engine"],
                model=best_result.get("model"),
                quality_score=best_result.get("quality_score"),
                confidence_score=best_result.get("confidence_score"),
                processing_time=best_result["processing_time"],
                word_count=best_result["word_count"],
                character_count=best_result["character_count"]
            )
        
        # 保存对比记录
        comparison_record = None
        if request.save_to_history and current_user:
            comparison_record = TranslationComparison(
                user_id=current_user.id,
                source_text=request.text,
                source_language=comparison_result["source_language"],
                target_language=comparison_result["target_language"],
                translations=comparison_result["results"]
            )
            db.add(comparison_record)
            db.commit()
            db.refresh(comparison_record)
        
        return CompareTranslationResponse(
            source_text=request.text,
            source_language=comparison_result["source_language"],
            target_language=comparison_result["target_language"],
            results=results,
            errors=comparison_result["errors"],
            best_translation=best_translation,
            comparison_id=comparison_record.id if comparison_record else None
        )
        
    except Exception as e:
        logger.error("Translation comparison failed", error=str(e), user_id=current_user.id if current_user else None)
        raise HTTPException(status_code=500, detail=f"翻译对比失败: {str(e)}")

@router.get("/engines")
async def get_available_engines():
    """
    获取可用的翻译引擎列表
    """
    engines = translation_service.get_available_engines()
    from app.core.config import settings
    
    engine_info = []
    for engine in engines:
        if engine in settings.TRANSLATION_ENGINES:
            engine_config = settings.TRANSLATION_ENGINES[engine]
            engine_info.append({
                "id": engine,
                "name": engine_config["name"],
                "enabled": engine_config["enabled"],
                "models": engine_config["models"],
                "default_model": engine_config["default_model"]
            })
    
    return {
        "engines": engine_info,
        "total": len(engine_info)
    }

@router.get("/languages")
async def get_supported_languages():
    """
    获取支持的语言列表
    """
    languages = translation_service.get_supported_languages()
    
    return {
        "languages": [
            {"code": code, "name": name}
            for code, name in languages.items()
        ],
        "total": len(languages)
    }

@router.post("/detect-language")
async def detect_text_language(text: str):
    """
    检测文本语言
    """
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="文本不能为空")
    
    try:
        detected_lang = await detect_language(text)
        from app.core.config import settings
        
        return {
            "detected_language": detected_lang,
            "language_name": settings.SUPPORTED_LANGUAGES.get(detected_lang, detected_lang),
            "confidence": 0.9  # 简化的置信度
        }
        
    except Exception as e:
        logger.error("Language detection failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"语言检测失败: {str(e)}")

@router.get("/stats")
async def get_translation_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取用户翻译统计信息
    """
    try:
        # 总翻译次数
        total_translations = db.query(Translation).filter(
            Translation.user_id == current_user.id
        ).count()
        
        # 本月翻译次数
        from datetime import datetime, timedelta
        month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_translations = db.query(Translation).filter(
            Translation.user_id == current_user.id,
            Translation.created_at >= month_start
        ).count()
        
        # 最常用的语言对
        from sqlalchemy import func
        popular_language_pairs = db.query(
            Translation.source_language,
            Translation.target_language,
            func.count(Translation.id).label('count')
        ).filter(
            Translation.user_id == current_user.id
        ).group_by(
            Translation.source_language,
            Translation.target_language
        ).order_by(func.count(Translation.id).desc()).limit(5).all()
        
        # 最常用的引擎
        popular_engines = db.query(
            Translation.engine,
            func.count(Translation.id).label('count')
        ).filter(
            Translation.user_id == current_user.id
        ).group_by(Translation.engine).order_by(func.count(Translation.id).desc()).limit(5).all()
        
        return {
            "total_translations": total_translations,
            "monthly_translations": monthly_translations,
            "total_words": current_user.words_translated,
            "popular_language_pairs": [
                {
                    "source_language": pair.source_language,
                    "target_language": pair.target_language,
                    "count": pair.count
                }
                for pair in popular_language_pairs
            ],
            "popular_engines": [
                {
                    "engine": engine.engine,
                    "count": engine.count
                }
                for engine in popular_engines
            ]
        }
        
    except Exception as e:
        logger.error("Failed to get translation stats", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail="获取统计信息失败")
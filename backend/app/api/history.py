from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List, Optional
from datetime import datetime, timedelta
import structlog

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.translation import Translation, TranslationComparison

logger = structlog.get_logger()
router = APIRouter()

# Pydantic模型
class TranslationHistoryItem(BaseModel):
    id: int
    source_text: str
    translated_text: str
    source_language: str
    target_language: str
    engine: str
    model: Optional[str] = None
    quality_score: Optional[float] = None
    confidence_score: Optional[float] = None
    word_count: int
    character_count: int
    processing_time: float
    user_rating: Optional[int] = None
    is_favorite: bool
    created_at: str

class TranslationHistoryResponse(BaseModel):
    translations: List[TranslationHistoryItem]
    total: int
    page: int
    page_size: int

class FavoriteToggleRequest(BaseModel):
    is_favorite: bool

class RatingRequest(BaseModel):
    rating: int  # 1-5星
    feedback: Optional[str] = None

class HistoryStats(BaseModel):
    total_translations: int
    total_words: int
    total_characters: int
    avg_quality_score: Optional[float] = None
    most_used_engine: Optional[str] = None
    most_translated_language_pair: Optional[dict] = None
    translations_this_month: int
    translations_today: int

@router.get("/", response_model=TranslationHistoryResponse)
async def get_translation_history(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    source_language: Optional[str] = Query(None, description="源语言过滤"),
    target_language: Optional[str] = Query(None, description="目标语言过滤"),
    engine: Optional[str] = Query(None, description="翻译引擎过滤"),
    favorites_only: bool = Query(False, description="仅显示收藏"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取翻译历史记录
    """
    try:
        # 构建查询
        query = db.query(Translation).filter(Translation.user_id == current_user.id)
        
        # 应用过滤条件
        if source_language:
            query = query.filter(Translation.source_language == source_language)
        
        if target_language:
            query = query.filter(Translation.target_language == target_language)
        
        if engine:
            query = query.filter(Translation.engine == engine)
        
        if favorites_only:
            query = query.filter(Translation.is_favorite == True)
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (Translation.source_text.ilike(search_term)) |
                (Translation.translated_text.ilike(search_term))
            )
        
        # 获取总数
        total = query.count()
        
        # 分页和排序
        translations = query.order_by(desc(Translation.created_at)).offset(
            (page - 1) * page_size
        ).limit(page_size).all()
        
        # 转换为响应格式
        translation_items = [
            TranslationHistoryItem(
                id=t.id,
                source_text=t.source_text,
                translated_text=t.translated_text,
                source_language=t.source_language,
                target_language=t.target_language,
                engine=t.engine,
                model=t.model,
                quality_score=t.quality_score,
                confidence_score=t.confidence_score,
                word_count=t.word_count,
                character_count=t.character_count,
                processing_time=t.processing_time,
                user_rating=t.user_rating,
                is_favorite=t.is_favorite,
                created_at=t.created_at.isoformat()
            )
            for t in translations
        ]
        
        return TranslationHistoryResponse(
            translations=translation_items,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error("Failed to get translation history", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail="获取翻译历史失败")

@router.get("/stats", response_model=HistoryStats)
async def get_history_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取翻译历史统计信息
    """
    try:
        # 基础统计
        total_translations = db.query(Translation).filter(
            Translation.user_id == current_user.id
        ).count()
        
        # 总词数和字符数
        word_char_stats = db.query(
            func.sum(Translation.word_count).label('total_words'),
            func.sum(Translation.character_count).label('total_characters'),
            func.avg(Translation.quality_score).label('avg_quality')
        ).filter(Translation.user_id == current_user.id).first()
        
        total_words = word_char_stats.total_words or 0
        total_characters = word_char_stats.total_characters or 0
        avg_quality_score = float(word_char_stats.avg_quality) if word_char_stats.avg_quality else None
        
        # 最常用的引擎
        most_used_engine_result = db.query(
            Translation.engine,
            func.count(Translation.id).label('count')
        ).filter(
            Translation.user_id == current_user.id
        ).group_by(Translation.engine).order_by(desc('count')).first()
        
        most_used_engine = most_used_engine_result.engine if most_used_engine_result else None
        
        # 最常翻译的语言对
        most_translated_pair_result = db.query(
            Translation.source_language,
            Translation.target_language,
            func.count(Translation.id).label('count')
        ).filter(
            Translation.user_id == current_user.id
        ).group_by(
            Translation.source_language,
            Translation.target_language
        ).order_by(desc('count')).first()
        
        most_translated_language_pair = None
        if most_translated_pair_result:
            most_translated_language_pair = {
                "source_language": most_translated_pair_result.source_language,
                "target_language": most_translated_pair_result.target_language,
                "count": most_translated_pair_result.count
            }
        
        # 本月翻译数
        month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        translations_this_month = db.query(Translation).filter(
            Translation.user_id == current_user.id,
            Translation.created_at >= month_start
        ).count()
        
        # 今日翻译数
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        translations_today = db.query(Translation).filter(
            Translation.user_id == current_user.id,
            Translation.created_at >= today_start
        ).count()
        
        return HistoryStats(
            total_translations=total_translations,
            total_words=total_words,
            total_characters=total_characters,
            avg_quality_score=avg_quality_score,
            most_used_engine=most_used_engine,
            most_translated_language_pair=most_translated_language_pair,
            translations_this_month=translations_this_month,
            translations_today=translations_today
        )
        
    except Exception as e:
        logger.error("Failed to get history stats", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail="获取统计信息失败")

@router.post("/{translation_id}/favorite")
async def toggle_favorite(
    translation_id: int,
    request: FavoriteToggleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    切换翻译收藏状态
    """
    try:
        translation = db.query(Translation).filter(
            Translation.id == translation_id,
            Translation.user_id == current_user.id
        ).first()
        
        if not translation:
            raise HTTPException(status_code=404, detail="翻译记录不存在")
        
        translation.is_favorite = request.is_favorite
        db.commit()
        
        action = "添加到收藏" if request.is_favorite else "取消收藏"
        logger.info(f"Translation {action}", user_id=current_user.id, translation_id=translation_id)
        
        return {"message": f"翻译已{action}", "is_favorite": request.is_favorite}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to toggle favorite", error=str(e), user_id=current_user.id, translation_id=translation_id)
        raise HTTPException(status_code=500, detail="操作失败")

@router.post("/{translation_id}/rating")
async def rate_translation(
    translation_id: int,
    request: RatingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    为翻译评分
    """
    try:
        if not 1 <= request.rating <= 5:
            raise HTTPException(status_code=400, detail="评分必须在1-5之间")
        
        translation = db.query(Translation).filter(
            Translation.id == translation_id,
            Translation.user_id == current_user.id
        ).first()
        
        if not translation:
            raise HTTPException(status_code=404, detail="翻译记录不存在")
        
        translation.user_rating = request.rating
        if request.feedback:
            translation.user_feedback = request.feedback
        
        db.commit()
        
        logger.info("Translation rated", user_id=current_user.id, translation_id=translation_id, rating=request.rating)
        
        return {"message": "评分成功", "rating": request.rating}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to rate translation", error=str(e), user_id=current_user.id, translation_id=translation_id)
        raise HTTPException(status_code=500, detail="评分失败")

@router.delete("/{translation_id}")
async def delete_translation(
    translation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    删除翻译记录
    """
    try:
        translation = db.query(Translation).filter(
            Translation.id == translation_id,
            Translation.user_id == current_user.id
        ).first()
        
        if not translation:
            raise HTTPException(status_code=404, detail="翻译记录不存在")
        
        db.delete(translation)
        db.commit()
        
        logger.info("Translation deleted", user_id=current_user.id, translation_id=translation_id)
        
        return {"message": "翻译记录删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete translation", error=str(e), user_id=current_user.id, translation_id=translation_id)
        raise HTTPException(status_code=500, detail="删除失败")

@router.delete("/")
async def clear_history(
    confirm: bool = Query(False, description="确认清空历史"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    清空翻译历史
    """
    try:
        if not confirm:
            raise HTTPException(status_code=400, detail="请确认清空历史操作")
        
        # 删除所有翻译记录
        deleted_count = db.query(Translation).filter(
            Translation.user_id == current_user.id
        ).delete()
        
        # 重置用户统计
        current_user.translation_count = 0
        current_user.words_translated = 0
        
        db.commit()
        
        logger.info("Translation history cleared", user_id=current_user.id, deleted_count=deleted_count)
        
        return {"message": f"已清空 {deleted_count} 条翻译记录"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to clear history", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail="清空历史失败")

@router.get("/export")
async def export_history(
    format: str = Query("json", description="导出格式: json, csv"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    导出翻译历史
    """
    try:
        translations = db.query(Translation).filter(
            Translation.user_id == current_user.id
        ).order_by(desc(Translation.created_at)).all()
        
        if format.lower() == "csv":
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # 写入标题行
            writer.writerow([
                "ID", "源文本", "翻译文本", "源语言", "目标语言", "翻译引擎",
                "质量分数", "置信度", "词数", "字符数", "处理时间", "用户评分", "创建时间"
            ])
            
            # 写入数据行
            for t in translations:
                writer.writerow([
                    t.id, t.source_text, t.translated_text, t.source_language,
                    t.target_language, t.engine, t.quality_score, t.confidence_score,
                    t.word_count, t.character_count, t.processing_time,
                    t.user_rating, t.created_at.isoformat()
                ])
            
            from fastapi.responses import StreamingResponse
            
            output.seek(0)
            return StreamingResponse(
                io.BytesIO(output.getvalue().encode()),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=translation_history.csv"}
            )
        
        else:  # JSON格式
            data = [
                {
                    "id": t.id,
                    "source_text": t.source_text,
                    "translated_text": t.translated_text,
                    "source_language": t.source_language,
                    "target_language": t.target_language,
                    "engine": t.engine,
                    "model": t.model,
                    "quality_score": t.quality_score,
                    "confidence_score": t.confidence_score,
                    "word_count": t.word_count,
                    "character_count": t.character_count,
                    "processing_time": t.processing_time,
                    "user_rating": t.user_rating,
                    "is_favorite": t.is_favorite,
                    "created_at": t.created_at.isoformat()
                }
                for t in translations
            ]
            
            from fastapi.responses import JSONResponse
            
            return JSONResponse(
                content=data,
                headers={"Content-Disposition": "attachment; filename=translation_history.json"}
            )
        
    except Exception as e:
        logger.error("Failed to export history", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail="导出失败")
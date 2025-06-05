from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from typing import Optional
import structlog

from app.core.database import get_db
from app.core.security import get_current_active_user, get_password_hash, verify_password
from app.models.user import User

logger = structlog.get_logger()
router = APIRouter()

# Pydantic模型
class UserProfile(BaseModel):
    username: str
    email: str
    full_name: str
    avatar_url: Optional[str] = None
    is_verified: bool
    is_premium: bool
    translation_count: int
    words_translated: int
    preferred_source_lang: str
    preferred_target_lang: str
    preferred_engine: str
    created_at: str
    last_login: Optional[str] = None

class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=100)
    avatar_url: Optional[str] = Field(None, max_length=500)
    preferred_source_lang: Optional[str] = Field(None, max_length=10)
    preferred_target_lang: Optional[str] = Field(None, max_length=10)
    preferred_engine: Optional[str] = Field(None, max_length=50)

class PasswordChange(BaseModel):
    current_password: str = Field(..., description="当前密码")
    new_password: str = Field(..., min_length=6, max_length=100, description="新密码")

class UserSettings(BaseModel):
    auto_detect_language: bool = True
    save_translation_history: bool = True
    show_quality_scores: bool = True
    default_translation_style: str = "natural"
    email_notifications: bool = True
    theme: str = "light"  # light, dark, auto

@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    """
    获取当前用户资料
    """
    return UserProfile(
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name or "",
        avatar_url=current_user.avatar_url,
        is_verified=current_user.is_verified,
        is_premium=current_user.is_premium,
        translation_count=current_user.translation_count,
        words_translated=current_user.words_translated,
        preferred_source_lang=current_user.preferred_source_lang,
        preferred_target_lang=current_user.preferred_target_lang,
        preferred_engine=current_user.preferred_engine,
        created_at=current_user.created_at.isoformat(),
        last_login=current_user.last_login.isoformat() if current_user.last_login else None
    )

@router.put("/me", response_model=UserProfile)
async def update_current_user_profile(
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    更新当前用户资料
    """
    try:
        # 更新用户信息
        if user_update.full_name is not None:
            current_user.full_name = user_update.full_name
        
        if user_update.avatar_url is not None:
            current_user.avatar_url = user_update.avatar_url
        
        if user_update.preferred_source_lang is not None:
            # 验证语言代码
            from app.core.config import settings
            if user_update.preferred_source_lang not in settings.SUPPORTED_LANGUAGES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="不支持的源语言"
                )
            current_user.preferred_source_lang = user_update.preferred_source_lang
        
        if user_update.preferred_target_lang is not None:
            from app.core.config import settings
            if user_update.preferred_target_lang not in settings.SUPPORTED_LANGUAGES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="不支持的目标语言"
                )
            current_user.preferred_target_lang = user_update.preferred_target_lang
        
        if user_update.preferred_engine is not None:
            from app.services.translation_service import translation_service
            available_engines = translation_service.get_available_engines()
            if user_update.preferred_engine not in available_engines:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="不支持的翻译引擎"
                )
            current_user.preferred_engine = user_update.preferred_engine
        
        db.commit()
        db.refresh(current_user)
        
        logger.info("User profile updated", user_id=current_user.id)
        
        return UserProfile(
            username=current_user.username,
            email=current_user.email,
            full_name=current_user.full_name or "",
            avatar_url=current_user.avatar_url,
            is_verified=current_user.is_verified,
            is_premium=current_user.is_premium,
            translation_count=current_user.translation_count,
            words_translated=current_user.words_translated,
            preferred_source_lang=current_user.preferred_source_lang,
            preferred_target_lang=current_user.preferred_target_lang,
            preferred_engine=current_user.preferred_engine,
            created_at=current_user.created_at.isoformat(),
            last_login=current_user.last_login.isoformat() if current_user.last_login else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update user profile", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新用户资料失败"
        )

@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    修改密码
    """
    try:
        # 验证当前密码
        if not verify_password(password_data.current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="当前密码错误"
            )
        
        # 检查新密码是否与当前密码相同
        if verify_password(password_data.new_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="新密码不能与当前密码相同"
            )
        
        # 更新密码
        current_user.hashed_password = get_password_hash(password_data.new_password)
        db.commit()
        
        logger.info("Password changed successfully", user_id=current_user.id)
        
        return {"message": "密码修改成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to change password", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="密码修改失败"
        )

@router.get("/settings", response_model=UserSettings)
async def get_user_settings(
    current_user: User = Depends(get_current_active_user)
):
    """
    获取用户设置
    """
    settings = current_user.settings or {}
    
    return UserSettings(
        auto_detect_language=settings.get("auto_detect_language", True),
        save_translation_history=settings.get("save_translation_history", True),
        show_quality_scores=settings.get("show_quality_scores", True),
        default_translation_style=settings.get("default_translation_style", "natural"),
        email_notifications=settings.get("email_notifications", True),
        theme=settings.get("theme", "light")
    )

@router.put("/settings", response_model=UserSettings)
async def update_user_settings(
    settings_update: UserSettings,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    更新用户设置
    """
    try:
        # 更新设置
        current_user.settings = {
            "auto_detect_language": settings_update.auto_detect_language,
            "save_translation_history": settings_update.save_translation_history,
            "show_quality_scores": settings_update.show_quality_scores,
            "default_translation_style": settings_update.default_translation_style,
            "email_notifications": settings_update.email_notifications,
            "theme": settings_update.theme
        }
        
        db.commit()
        
        logger.info("User settings updated", user_id=current_user.id)
        
        return settings_update
        
    except Exception as e:
        logger.error("Failed to update user settings", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新用户设置失败"
        )

@router.delete("/me")
async def delete_current_user_account(
    password: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    删除当前用户账户
    """
    try:
        # 验证密码
        if not verify_password(password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="密码错误"
            )
        
        # 软删除：将用户标记为非活跃
        current_user.is_active = False
        current_user.email = f"deleted_{current_user.id}@deleted.com"
        current_user.username = f"deleted_{current_user.id}"
        
        db.commit()
        
        logger.info("User account deleted", user_id=current_user.id)
        
        return {"message": "账户删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete user account", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="账户删除失败"
        )
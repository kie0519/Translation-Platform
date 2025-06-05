from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import uuid
import aiofiles
import structlog

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.config import settings
from app.models.user import User
from app.models.file import File as FileModel
from app.services.file_service import file_service

logger = structlog.get_logger()
router = APIRouter()

# Pydantic模型
class FileUploadResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_size: int
    file_type: str
    translation_status: str
    created_at: str

class FileTranslationRequest(BaseModel):
    source_language: str = "auto"
    target_language: str = "zh"
    translation_engine: str = "openai"

class FileListResponse(BaseModel):
    files: List[FileUploadResponse]
    total: int
    page: int
    page_size: int

@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    上传文件
    """
    try:
        # 检查文件大小
        if file.size > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"文件大小超过限制 ({settings.MAX_FILE_SIZE / 1024 / 1024:.1f}MB)"
            )
        
        # 检查文件类型
        file_extension = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
        if file_extension not in settings.ALLOWED_FILE_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型。支持的类型: {', '.join(settings.ALLOWED_FILE_TYPES)}"
            )
        
        # 生成唯一文件名
        file_id = str(uuid.uuid4())
        filename = f"{file_id}.{file_extension}"
        file_path = os.path.join(settings.UPLOAD_DIR, filename)
        
        # 保存文件
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # 创建文件记录
        file_record = FileModel(
            user_id=current_user.id,
            filename=filename,
            original_filename=file.filename,
            file_path=file_path,
            file_size=file.size,
            file_type=file_extension,
            mime_type=file.content_type,
            translation_status="uploaded"
        )
        
        db.add(file_record)
        db.commit()
        db.refresh(file_record)
        
        logger.info(
            "File uploaded successfully",
            user_id=current_user.id,
            file_id=file_record.id,
            filename=file.filename,
            file_size=file.size
        )
        
        return FileUploadResponse(
            id=file_record.id,
            filename=file_record.filename,
            original_filename=file_record.original_filename,
            file_size=file_record.file_size,
            file_type=file_record.file_type,
            translation_status=file_record.translation_status,
            created_at=file_record.created_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("File upload failed", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail="文件上传失败")

@router.post("/{file_id}/translate")
async def translate_file(
    file_id: int,
    translation_request: FileTranslationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    翻译文件
    """
    try:
        # 获取文件记录
        file_record = db.query(FileModel).filter(
            FileModel.id == file_id,
            FileModel.user_id == current_user.id
        ).first()
        
        if not file_record:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        if file_record.translation_status == "processing":
            raise HTTPException(status_code=400, detail="文件正在翻译中")
        
        # 更新翻译配置
        file_record.source_language = translation_request.source_language
        file_record.target_language = translation_request.target_language
        file_record.translation_engine = translation_request.translation_engine
        file_record.translation_status = "processing"
        file_record.translation_progress = 0
        
        db.commit()
        
        # 添加后台翻译任务
        background_tasks.add_task(
            file_service.translate_file_async,
            file_record.id,
            db
        )
        
        logger.info(
            "File translation started",
            user_id=current_user.id,
            file_id=file_id,
            source_lang=translation_request.source_language,
            target_lang=translation_request.target_language,
            engine=translation_request.translation_engine
        )
        
        return {"message": "文件翻译已开始", "file_id": file_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to start file translation", error=str(e), user_id=current_user.id, file_id=file_id)
        raise HTTPException(status_code=500, detail="启动文件翻译失败")

@router.get("/{file_id}/status")
async def get_file_translation_status(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取文件翻译状态
    """
    try:
        file_record = db.query(FileModel).filter(
            FileModel.id == file_id,
            FileModel.user_id == current_user.id
        ).first()
        
        if not file_record:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        return {
            "file_id": file_id,
            "status": file_record.translation_status,
            "progress": file_record.translation_progress,
            "error_message": file_record.error_message,
            "completed_at": file_record.completed_at.isoformat() if file_record.completed_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get file status", error=str(e), user_id=current_user.id, file_id=file_id)
        raise HTTPException(status_code=500, detail="获取文件状态失败")

@router.get("/{file_id}/download")
async def download_translated_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    下载翻译后的文件
    """
    try:
        file_record = db.query(FileModel).filter(
            FileModel.id == file_id,
            FileModel.user_id == current_user.id
        ).first()
        
        if not file_record:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        if file_record.translation_status != "completed":
            raise HTTPException(status_code=400, detail="文件翻译未完成")
        
        if not file_record.translated_file_path or not os.path.exists(file_record.translated_file_path):
            raise HTTPException(status_code=404, detail="翻译文件不存在")
        
        from fastapi.responses import FileResponse
        
        return FileResponse(
            path=file_record.translated_file_path,
            filename=f"translated_{file_record.original_filename}",
            media_type='application/octet-stream'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to download file", error=str(e), user_id=current_user.id, file_id=file_id)
        raise HTTPException(status_code=500, detail="文件下载失败")

@router.get("/", response_model=FileListResponse)
async def list_user_files(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取用户文件列表
    """
    try:
        # 构建查询
        query = db.query(FileModel).filter(FileModel.user_id == current_user.id)
        
        if status:
            query = query.filter(FileModel.translation_status == status)
        
        # 分页
        total = query.count()
        files = query.order_by(FileModel.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size).all()
        
        file_list = [
            FileUploadResponse(
                id=file.id,
                filename=file.filename,
                original_filename=file.original_filename,
                file_size=file.file_size,
                file_type=file.file_type,
                translation_status=file.translation_status,
                created_at=file.created_at.isoformat()
            )
            for file in files
        ]
        
        return FileListResponse(
            files=file_list,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error("Failed to list user files", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail="获取文件列表失败")

@router.delete("/{file_id}")
async def delete_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    删除文件
    """
    try:
        file_record = db.query(FileModel).filter(
            FileModel.id == file_id,
            FileModel.user_id == current_user.id
        ).first()
        
        if not file_record:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 删除物理文件
        if os.path.exists(file_record.file_path):
            os.remove(file_record.file_path)
        
        if file_record.translated_file_path and os.path.exists(file_record.translated_file_path):
            os.remove(file_record.translated_file_path)
        
        # 删除数据库记录
        db.delete(file_record)
        db.commit()
        
        logger.info("File deleted successfully", user_id=current_user.id, file_id=file_id)
        
        return {"message": "文件删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete file", error=str(e), user_id=current_user.id, file_id=file_id)
        raise HTTPException(status_code=500, detail="文件删除失败")
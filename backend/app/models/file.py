from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, BigInteger
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class File(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    
    # 用户关联
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # 文件信息
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(BigInteger, nullable=False)  # 文件大小（字节）
    file_type = Column(String(50), nullable=False)  # txt, docx, pdf, srt
    mime_type = Column(String(100))
    
    # 文件内容
    extracted_text = Column(Text)  # 从文件中提取的文本
    
    # 翻译状态
    translation_status = Column(String(20), default="pending")  # pending, processing, completed, failed
    translation_progress = Column(Integer, default=0)  # 0-100
    
    # 翻译配置
    source_language = Column(String(10))
    target_language = Column(String(10))
    translation_engine = Column(String(50))
    
    # 翻译结果
    translated_content = Column(Text)
    translated_file_path = Column(String(500))  # 翻译后的文件路径
    
    # 处理信息
    processing_log = Column(JSON)  # 处理日志
    error_message = Column(Text)
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True))
    
    # 关系
    user = relationship("User", back_populates="files")
    
    def __repr__(self):
        return f"<File(id={self.id}, filename='{self.filename}', status='{self.translation_status}')>"

class FileChunk(Base):
    """文件分块表 - 用于大文件的分块处理"""
    __tablename__ = "file_chunks"

    id = Column(Integer, primary_key=True, index=True)
    
    # 文件关联
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False)
    
    # 分块信息
    chunk_index = Column(Integer, nullable=False)  # 分块索引
    chunk_text = Column(Text, nullable=False)  # 分块文本
    translated_text = Column(Text)  # 翻译后的文本
    
    # 处理状态
    status = Column(String(20), default="pending")  # pending, processing, completed, failed
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    file = relationship("File")
    
    def __repr__(self):
        return f"<FileChunk(id={self.id}, file_id={self.file_id}, chunk_index={self.chunk_index})>"
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class Translation(Base):
    __tablename__ = "translations"

    id = Column(Integer, primary_key=True, index=True)
    
    # 用户关联
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # 翻译内容
    source_text = Column(Text, nullable=False)
    translated_text = Column(Text, nullable=False)
    source_language = Column(String(10), nullable=False)
    target_language = Column(String(10), nullable=False)
    
    # 翻译引擎信息
    engine = Column(String(50), nullable=False)  # openai, anthropic, google, baidu
    model = Column(String(100))  # 具体模型名称
    
    # 翻译质量评估
    quality_score = Column(Float)  # 0-100分
    confidence_score = Column(Float)  # 0-1置信度
    
    # 翻译元数据
    word_count = Column(Integer)
    character_count = Column(Integer)
    processing_time = Column(Float)  # 处理时间（秒）
    
    # 用户反馈
    user_rating = Column(Integer)  # 1-5星评分
    user_feedback = Column(Text)
    is_favorite = Column(Boolean, default=False)
    
    # 翻译选项
    translation_options = Column(JSON)  # 存储翻译时的选项配置
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    user = relationship("User", back_populates="translations")
    
    def __repr__(self):
        return f"<Translation(id={self.id}, engine='{self.engine}', source_lang='{self.source_language}', target_lang='{self.target_language}')>"

class TranslationComparison(Base):
    """翻译对比表 - 存储多个引擎的翻译结果对比"""
    __tablename__ = "translation_comparisons"

    id = Column(Integer, primary_key=True, index=True)
    
    # 用户关联
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # 源文本
    source_text = Column(Text, nullable=False)
    source_language = Column(String(10), nullable=False)
    target_language = Column(String(10), nullable=False)
    
    # 多个翻译结果
    translations = Column(JSON)  # 存储多个引擎的翻译结果
    
    # 用户选择的最佳翻译
    selected_translation_id = Column(Integer, ForeignKey("translations.id"))
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    user = relationship("User")
    selected_translation = relationship("Translation")
    
    def __repr__(self):
        return f"<TranslationComparison(id={self.id}, source_lang='{self.source_language}', target_lang='{self.target_language}')>"
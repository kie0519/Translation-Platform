import asyncio
import re
from typing import Dict, List, Optional
import textstat
import structlog

logger = structlog.get_logger()

async def analyze_text_quality(
    source_text: str,
    translated_text: str,
    source_lang: str,
    target_lang: str
) -> float:
    """
    分析翻译质量
    
    Args:
        source_text: 源文本
        translated_text: 翻译文本
        source_lang: 源语言
        target_lang: 目标语言
        
    Returns:
        质量分数 (0-100)
    """
    try:
        score = 0.0
        
        # 1. 长度合理性检查 (20分)
        length_score = _analyze_length_ratio(source_text, translated_text, source_lang, target_lang)
        score += length_score * 0.2
        
        # 2. 完整性检查 (25分)
        completeness_score = _analyze_completeness(source_text, translated_text)
        score += completeness_score * 0.25
        
        # 3. 流畅性检查 (25分)
        fluency_score = await _analyze_fluency(translated_text, target_lang)
        score += fluency_score * 0.25
        
        # 4. 格式保持检查 (15分)
        format_score = _analyze_format_preservation(source_text, translated_text)
        score += format_score * 0.15
        
        # 5. 特殊字符处理检查 (15分)
        special_char_score = _analyze_special_characters(source_text, translated_text)
        score += special_char_score * 0.15
        
        return min(100.0, max(0.0, score))
        
    except Exception as e:
        logger.error("Text quality analysis failed", error=str(e))
        return 75.0  # 默认分数

def _analyze_length_ratio(source_text: str, translated_text: str, source_lang: str, target_lang: str) -> float:
    """分析长度比例合理性"""
    if not source_text or not translated_text:
        return 0.0
    
    source_len = len(source_text)
    translated_len = len(translated_text)
    
    if source_len == 0:
        return 0.0
    
    ratio = translated_len / source_len
    
    # 不同语言对的合理长度比例范围
    expected_ratios = {
        ('en', 'zh'): (0.4, 0.8),  # 英文到中文通常会变短
        ('zh', 'en'): (1.2, 2.5),  # 中文到英文通常会变长
        ('ja', 'zh'): (0.6, 1.2),  # 日文到中文
        ('ko', 'zh'): (0.6, 1.2),  # 韩文到中文
        ('fr', 'en'): (0.8, 1.3),  # 法文到英文
        ('de', 'en'): (0.7, 1.2),  # 德文到英文
    }
    
    # 获取期望比例范围
    min_ratio, max_ratio = expected_ratios.get((source_lang, target_lang), (0.5, 2.0))
    
    if min_ratio <= ratio <= max_ratio:
        return 100.0
    elif ratio < min_ratio:
        # 翻译过短
        return max(0.0, 100.0 * (ratio / min_ratio))
    else:
        # 翻译过长
        return max(0.0, 100.0 * (max_ratio / ratio))

def _analyze_completeness(source_text: str, translated_text: str) -> float:
    """分析翻译完整性"""
    if not source_text or not translated_text:
        return 0.0
    
    score = 100.0
    
    # 检查是否有明显的截断
    if translated_text.endswith('...') or translated_text.endswith('…'):
        score -= 30.0
    
    # 检查是否包含未翻译的原文
    if len(source_text) > 20:
        # 检查是否有大段原文未翻译
        source_words = set(source_text.lower().split())
        translated_words = set(translated_text.lower().split())
        
        # 如果翻译中包含太多原文词汇（可能未翻译）
        overlap = len(source_words.intersection(translated_words))
        if overlap > len(source_words) * 0.7:  # 70%以上重叠可能表示未翻译
            score -= 40.0
    
    # 检查是否为空或过短
    if len(translated_text.strip()) < len(source_text.strip()) * 0.1:
        score -= 50.0
    
    return max(0.0, score)

async def _analyze_fluency(text: str, language: str) -> float:
    """分析文本流畅性"""
    if not text:
        return 0.0
    
    try:
        score = 100.0
        
        # 1. 检查重复词汇
        words = text.split()
        if len(words) > 1:
            unique_words = set(words)
            repetition_ratio = len(words) / len(unique_words)
            if repetition_ratio > 2.0:  # 重复率过高
                score -= 20.0
        
        # 2. 检查句子结构
        sentences = re.split(r'[.!?。！？]', text)
        if sentences:
            avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
            
            # 句子过长或过短都影响流畅性
            if avg_sentence_length < 3:
                score -= 15.0
            elif avg_sentence_length > 50:
                score -= 10.0
        
        # 3. 检查标点符号使用
        punct_count = len(re.findall(r'[.!?。！？,，;；:：]', text))
        word_count = len(text.split())
        if word_count > 0:
            punct_ratio = punct_count / word_count
            if punct_ratio > 0.3:  # 标点过多
                score -= 10.0
            elif punct_ratio < 0.05 and word_count > 10:  # 标点过少
                score -= 15.0
        
        # 4. 检查是否有明显的语法错误标志
        error_patterns = [
            r'\s+[.!?。！？]',  # 标点前有空格
            r'[.!?。！？]{3,}',  # 连续标点
            r'\b\w\b\s+\b\w\b\s+\b\w\b',  # 连续单字符词
        ]
        
        for pattern in error_patterns:
            if re.search(pattern, text):
                score -= 5.0
        
        return max(0.0, score)
        
    except Exception as e:
        logger.error("Fluency analysis failed", error=str(e))
        return 75.0

def _analyze_format_preservation(source_text: str, translated_text: str) -> float:
    """分析格式保持情况"""
    if not source_text or not translated_text:
        return 0.0
    
    score = 100.0
    
    # 检查换行符保持
    source_lines = source_text.count('\n')
    translated_lines = translated_text.count('\n')
    if source_lines > 0:
        line_diff = abs(source_lines - translated_lines) / source_lines
        if line_diff > 0.5:
            score -= 20.0
    
    # 检查特殊格式标记
    format_markers = [
        r'\*\*.*?\*\*',  # 粗体
        r'\*.*?\*',      # 斜体
        r'`.*?`',        # 代码
        r'\[.*?\]',      # 链接文本
        r'\(.*?\)',      # 括号内容
    ]
    
    for marker in format_markers:
        source_matches = len(re.findall(marker, source_text))
        translated_matches = len(re.findall(marker, translated_text))
        
        if source_matches > 0:
            preservation_ratio = translated_matches / source_matches
            if preservation_ratio < 0.8:
                score -= 10.0
    
    return max(0.0, score)

def _analyze_special_characters(source_text: str, translated_text: str) -> float:
    """分析特殊字符处理"""
    if not source_text or not translated_text:
        return 0.0
    
    score = 100.0
    
    # 检查数字保持
    source_numbers = re.findall(r'\d+(?:\.\d+)?', source_text)
    translated_numbers = re.findall(r'\d+(?:\.\d+)?', translated_text)
    
    if source_numbers:
        number_preservation = len(set(source_numbers).intersection(set(translated_numbers))) / len(set(source_numbers))
        if number_preservation < 0.8:
            score -= 20.0
    
    # 检查URL保持
    url_pattern = r'https?://[^\s]+'
    source_urls = re.findall(url_pattern, source_text)
    translated_urls = re.findall(url_pattern, translated_text)
    
    if source_urls:
        url_preservation = len(set(source_urls).intersection(set(translated_urls))) / len(set(source_urls))
        if url_preservation < 0.9:
            score -= 15.0
    
    # 检查邮箱保持
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    source_emails = re.findall(email_pattern, source_text)
    translated_emails = re.findall(email_pattern, translated_text)
    
    if source_emails:
        email_preservation = len(set(source_emails).intersection(set(translated_emails))) / len(set(source_emails))
        if email_preservation < 0.9:
            score -= 15.0
    
    return max(0.0, score)

def calculate_readability_score(text: str, language: str = 'en') -> Dict[str, float]:
    """
    计算文本可读性分数
    
    Args:
        text: 要分析的文本
        language: 文本语言
        
    Returns:
        包含各种可读性指标的字典
    """
    if not text:
        return {}
    
    try:
        if language == 'en':
            return {
                'flesch_reading_ease': textstat.flesch_reading_ease(text),
                'flesch_kincaid_grade': textstat.flesch_kincaid_grade(text),
                'gunning_fog': textstat.gunning_fog(text),
                'automated_readability_index': textstat.automated_readability_index(text),
                'coleman_liau_index': textstat.coleman_liau_index(text),
                'linsear_write_formula': textstat.linsear_write_formula(text),
                'dale_chall_readability_score': textstat.dale_chall_readability_score(text)
            }
        else:
            # 对于非英语文本，使用基础指标
            sentences = len(re.split(r'[.!?。！？]', text))
            words = len(text.split())
            characters = len(text)
            
            if sentences > 0 and words > 0:
                avg_sentence_length = words / sentences
                avg_word_length = characters / words
                
                return {
                    'avg_sentence_length': avg_sentence_length,
                    'avg_word_length': avg_word_length,
                    'sentence_count': sentences,
                    'word_count': words,
                    'character_count': characters
                }
            
        return {}
        
    except Exception as e:
        logger.error("Readability analysis failed", error=str(e))
        return {}

def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """
    提取文本关键词
    
    Args:
        text: 要分析的文本
        max_keywords: 最大关键词数量
        
    Returns:
        关键词列表
    """
    if not text:
        return []
    
    try:
        # 简单的关键词提取（基于词频）
        words = re.findall(r'\b\w+\b', text.lower())
        
        # 过滤停用词（简化版）
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those',
            '的', '了', '在', '是', '我', '你', '他', '她', '它', '们', '和', '与', '或', '但', '如果', '因为'
        }
        
        # 计算词频
        word_freq = {}
        for word in words:
            if len(word) > 2 and word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # 按频率排序并返回前N个
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:max_keywords]]
        
    except Exception as e:
        logger.error("Keyword extraction failed", error=str(e))
        return []
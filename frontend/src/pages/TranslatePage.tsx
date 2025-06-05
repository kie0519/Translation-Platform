import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  ArrowsRightLeftIcon,
  SpeakerWaveIcon,
  ClipboardDocumentIcon,
  HeartIcon,
  StarIcon,
} from '@heroicons/react/24/outline';
import { HeartIcon as HeartSolidIcon } from '@heroicons/react/24/solid';
import { useQuery } from '@tanstack/react-query';
import { translationService, TranslationRequest } from '@/services/translationService';
import LoadingSpinner from '@/components/LoadingSpinner';
import toast from 'react-hot-toast';

const TranslatePage: React.FC = () => {
  const [sourceText, setSourceText] = useState('');
  const [translatedText, setTranslatedText] = useState('');
  const [sourceLang, setSourceLang] = useState('auto');
  const [targetLang, setTargetLang] = useState('zh');
  const [selectedEngine, setSelectedEngine] = useState('openai');
  const [translationStyle, setTranslationStyle] = useState('natural');
  const [isTranslating, setIsTranslating] = useState(false);
  const [currentTranslation, setCurrentTranslation] = useState<any>(null);

  // 获取支持的语言
  const { data: languagesData } = useQuery({
    queryKey: ['languages'],
    queryFn: () => translationService.getSupportedLanguages(),
  });

  // 获取可用的翻译引擎
  const { data: enginesData } = useQuery({
    queryKey: ['engines'],
    queryFn: () => translationService.getAvailableEngines(),
  });

  const languages = languagesData?.languages || [];
  const engines = enginesData?.engines || [];

  const translationStyles = [
    { value: 'natural', label: '自然流畅' },
    { value: 'formal', label: '正式严谨' },
    { value: 'casual', label: '轻松随意' },
    { value: 'technical', label: '专业技术' },
    { value: 'literary', label: '文学优美' },
  ];

  const handleTranslate = async () => {
    if (!sourceText.trim()) {
      toast.error('请输入要翻译的文本');
      return;
    }

    setIsTranslating(true);
    try {
      const request: TranslationRequest = {
        text: sourceText,
        source_language: sourceLang,
        target_language: targetLang,
        engine: selectedEngine,
        style: translationStyle,
        save_to_history: true,
      };

      const result = await translationService.translate(request);
      setTranslatedText(result.translated_text);
      setCurrentTranslation(result);
      toast.success('翻译完成！');
    } catch (error: any) {
      toast.error(error.message || '翻译失败');
    } finally {
      setIsTranslating(false);
    }
  };

  const handleSwapLanguages = () => {
    if (sourceLang === 'auto') {
      toast.error('自动检测语言无法交换');
      return;
    }
    
    setSourceLang(targetLang);
    setTargetLang(sourceLang);
    setSourceText(translatedText);
    setTranslatedText(sourceText);
  };

  const handleCopyText = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success('已复制到剪贴板');
  };

  const handleSpeakText = (text: string, lang: string) => {
    if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = lang === 'zh' ? 'zh-CN' : lang;
      speechSynthesis.speak(utterance);
    } else {
      toast.error('您的浏览器不支持语音播放');
    }
  };

  return (
    <div className="max-w-6xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        {/* 页面标题 */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">智能翻译</h1>
          <p className="text-gray-600">
            基于多个大语言模型的高质量翻译服务，支持100+语言对翻译
          </p>
        </div>

        {/* 翻译设置 */}
        <div className="card mb-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                源语言
              </label>
              <select
                value={sourceLang}
                onChange={(e) => setSourceLang(e.target.value)}
                className="input"
              >
                <option value="auto">自动检测</option>
                {languages.map((lang) => (
                  <option key={lang.code} value={lang.code}>
                    {lang.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                目标语言
              </label>
              <select
                value={targetLang}
                onChange={(e) => setTargetLang(e.target.value)}
                className="input"
              >
                {languages.map((lang) => (
                  <option key={lang.code} value={lang.code}>
                    {lang.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                翻译引擎
              </label>
              <select
                value={selectedEngine}
                onChange={(e) => setSelectedEngine(e.target.value)}
                className="input"
              >
                {engines.map((engine) => (
                  <option key={engine.id} value={engine.id}>
                    {engine.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                翻译风格
              </label>
              <select
                value={translationStyle}
                onChange={(e) => setTranslationStyle(e.target.value)}
                className="input"
              >
                {translationStyles.map((style) => (
                  <option key={style.value} value={style.value}>
                    {style.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* 翻译区域 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* 源文本输入 */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-900">
                {sourceLang === 'auto' ? '原文' : languages.find(l => l.code === sourceLang)?.name || '原文'}
              </h3>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => handleSpeakText(sourceText, sourceLang)}
                  disabled={!sourceText.trim()}
                  className="p-2 text-gray-400 hover:text-gray-600 disabled:opacity-50"
                  title="朗读"
                >
                  <SpeakerWaveIcon className="h-5 w-5" />
                </button>
                <button
                  onClick={() => handleCopyText(sourceText)}
                  disabled={!sourceText.trim()}
                  className="p-2 text-gray-400 hover:text-gray-600 disabled:opacity-50"
                  title="复制"
                >
                  <ClipboardDocumentIcon className="h-5 w-5" />
                </button>
              </div>
            </div>
            <textarea
              value={sourceText}
              onChange={(e) => setSourceText(e.target.value)}
              placeholder="请输入要翻译的文本..."
              className="textarea h-64 resize-none"
              maxLength={10000}
            />
            <div className="flex items-center justify-between mt-2 text-sm text-gray-500">
              <span>{sourceText.length}/10000</span>
              <button
                onClick={handleSwapLanguages}
                disabled={sourceLang === 'auto' || !translatedText}
                className="flex items-center space-x-1 text-primary-600 hover:text-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ArrowsRightLeftIcon className="h-4 w-4" />
                <span>交换</span>
              </button>
            </div>
          </div>

          {/* 翻译结果 */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-900">
                {languages.find(l => l.code === targetLang)?.name || '译文'}
              </h3>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => handleSpeakText(translatedText, targetLang)}
                  disabled={!translatedText.trim()}
                  className="p-2 text-gray-400 hover:text-gray-600 disabled:opacity-50"
                  title="朗读"
                >
                  <SpeakerWaveIcon className="h-5 w-5" />
                </button>
                <button
                  onClick={() => handleCopyText(translatedText)}
                  disabled={!translatedText.trim()}
                  className="p-2 text-gray-400 hover:text-gray-600 disabled:opacity-50"
                  title="复制"
                >
                  <ClipboardDocumentIcon className="h-5 w-5" />
                </button>
              </div>
            </div>
            <div className="relative">
              <textarea
                value={translatedText}
                readOnly
                placeholder="翻译结果将显示在这里..."
                className="textarea h-64 resize-none bg-gray-50"
              />
              {isTranslating && (
                <div className="absolute inset-0 bg-white bg-opacity-75 flex items-center justify-center">
                  <div className="flex items-center space-x-2">
                    <LoadingSpinner />
                    <span className="text-gray-600">翻译中...</span>
                  </div>
                </div>
              )}
            </div>
            
            {/* 翻译质量信息 */}
            {currentTranslation && (
              <div className="mt-4 p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center justify-between text-sm">
                  <div className="flex items-center space-x-4">
                    <span className="text-gray-600">
                      引擎: <span className="font-medium">{currentTranslation.engine}</span>
                    </span>
                    {currentTranslation.quality_score && (
                      <div className="flex items-center space-x-1">
                        <StarIcon className="h-4 w-4 text-yellow-400" />
                        <span className="text-gray-600">
                          质量: <span className="font-medium">{currentTranslation.quality_score.toFixed(1)}</span>
                        </span>
                      </div>
                    )}
                    <span className="text-gray-600">
                      用时: <span className="font-medium">{currentTranslation.processing_time.toFixed(2)}s</span>
                    </span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="text-gray-600">
                      {currentTranslation.word_count} 词 / {currentTranslation.character_count} 字符
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* 翻译按钮 */}
        <div className="mt-6 text-center">
          <button
            onClick={handleTranslate}
            disabled={!sourceText.trim() || isTranslating}
            className="btn-primary px-8 py-3 text-lg"
          >
            {isTranslating ? (
              <>
                <LoadingSpinner size="sm" className="mr-2" />
                翻译中...
              </>
            ) : (
              '开始翻译'
            )}
          </button>
        </div>

        {/* 快捷示例 */}
        <div className="mt-8">
          <h3 className="text-lg font-medium text-gray-900 mb-4">快速体验</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[
              { text: 'Hello, how are you today?', lang: 'en' },
              { text: '今天天气真不错！', lang: 'zh' },
              { text: 'Bonjour, comment allez-vous?', lang: 'fr' },
            ].map((example, index) => (
              <button
                key={index}
                onClick={() => {
                  setSourceText(example.text);
                  setSourceLang(example.lang);
                }}
                className="p-3 text-left border border-gray-200 rounded-lg hover:border-primary-300 hover:bg-primary-50 transition-colors"
              >
                <p className="text-sm text-gray-600 mb-1">示例 {index + 1}</p>
                <p className="text-gray-900">{example.text}</p>
              </button>
            ))}
          </div>
        </div>
      </motion.div>
    </div>
  );
};

export default TranslatePage;
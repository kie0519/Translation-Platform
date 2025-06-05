import { api } from './authService';

export interface TranslationRequest {
  text: string;
  source_language?: string;
  target_language?: string;
  engine?: string;
  model?: string;
  style?: string;
  save_to_history?: boolean;
}

export interface TranslationResult {
  id?: number;
  source_text: string;
  translated_text: string;
  source_language: string;
  target_language: string;
  engine: string;
  model?: string;
  quality_score?: number;
  confidence_score?: number;
  processing_time: number;
  word_count: number;
  character_count: number;
  keywords?: string[];
  readability?: Record<string, any>;
  created_at?: string;
}

export interface CompareTranslationRequest {
  text: string;
  source_language?: string;
  target_language?: string;
  engines?: string[];
  save_to_history?: boolean;
}

export interface CompareTranslationResult {
  source_text: string;
  source_language: string;
  target_language: string;
  results: Record<string, TranslationResult>;
  errors: Record<string, string>;
  best_translation?: TranslationResult;
  comparison_id?: number;
}

export interface TranslationEngine {
  id: string;
  name: string;
  enabled: boolean;
  models: string[];
  default_model: string;
}

export interface Language {
  code: string;
  name: string;
}

export interface TranslationStats {
  total_translations: number;
  monthly_translations: number;
  total_words: number;
  popular_language_pairs: Array<{
    source_language: string;
    target_language: string;
    count: number;
  }>;
  popular_engines: Array<{
    engine: string;
    count: number;
  }>;
}

class TranslationService {
  async translate(request: TranslationRequest): Promise<TranslationResult> {
    try {
      const response = await api.post('/translation/translate', request);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || '翻译失败');
    }
  }

  async compareTranslations(request: CompareTranslationRequest): Promise<CompareTranslationResult> {
    try {
      const response = await api.post('/translation/compare', request);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || '翻译对比失败');
    }
  }

  async getAvailableEngines(): Promise<{ engines: TranslationEngine[]; total: number }> {
    try {
      const response = await api.get('/translation/engines');
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || '获取翻译引擎失败');
    }
  }

  async getSupportedLanguages(): Promise<{ languages: Language[]; total: number }> {
    try {
      const response = await api.get('/translation/languages');
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || '获取支持语言失败');
    }
  }

  async detectLanguage(text: string): Promise<{
    detected_language: string;
    language_name: string;
    confidence: number;
  }> {
    try {
      const response = await api.post('/translation/detect-language', null, {
        params: { text }
      });
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || '语言检测失败');
    }
  }

  async getTranslationStats(): Promise<TranslationStats> {
    try {
      const response = await api.get('/translation/stats');
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || '获取统计信息失败');
    }
  }
}

export const translationService = new TranslationService();
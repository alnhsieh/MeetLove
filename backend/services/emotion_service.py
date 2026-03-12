"""
情緒分析服務 - Emotion Analysis Service
整合表情、語音、文字三種情緒輸入，輸出最終喜好判斷
"""

import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime


class EmotionAnalysisService:
    """
    情緒分析服務
    
    功能：
    1. 表情情緒分析
    2. 語音情緒分析
    3. 文字情感分析
    4. 整合決策輸出 High/Normal/Low
    """
    
    def __init__(self):
        # 情緒類型權重
        self.weights = {
            'emotion': 0.4,  # 表情 - 最直接
            'voice': 0.3,    # 語音 - 次之
            'text': 0.3      # 文字 - 輔助
        }
        
        # 閾值設定
        self.thresholds = {
            'high': 0.7,
            'normal': 0.4
        }
        
        # 表情到情緒分數的映射
        self.emotion_weights = {
            'happy': 1.0,
            'surprised': 0.8,
            'neutral': 0.5,
            'fearful': 0.3,
            'disgusted': 0.2,
            'sad': 0.2,
            'angry': 0.1
        }
    
    # ========================
    # 表情分析
    # ========================
    
    def analyze_emotion(self, emotion_data: Dict[str, float]) -> Dict[str, Any]:
        """
        分析臉部表情數據
        
        Args:
            emotion_data: 如 {'happy': 0.8, 'sad': 0.1, 'angry': 0.05, ...}
        
        Returns:
            情緒分析結果
        """
        if not emotion_data:
            return self._empty_result('emotion')
        
        # 計算情緒分數
        score = 0.0
        for emotion, probability in emotion_data.items():
            weight = self.emotion_weights.get(emotion, 0.5)
            score += probability * weight
        
        # 標準化到 0-1
        score = max(0.0, min(1.0, score))
        
        # 主要情緒
        primary_emotion = max(emotion_data.items(), key=lambda x: x[1])[0] if emotion_data else 'neutral'
        
        return {
            'type': 'emotion',
            'score': score,
            'primary_emotion': primary_emotion,
            'details': {
                'emotions': emotion_data,
                'model': 'mediapipe-face-mesh'
            },
            'timestamp': datetime.now().isoformat()
        }
    
    # ========================
    # 語音分析
    # ========================
    
    def analyze_voice(self, voice_features: Dict[str, float]) -> Dict[str, Any]:
        """
        分析語音特徵
        
        Args:
            voice_features: 如 {'pitch_variance': 0.3, 'speech_rate': 0.6, 'energy': 0.7, ...}
        
        Returns:
            語音分析結果
        """
        if not voice_features:
            return self._empty_result('voice')
        
        # 計算各項得分
        scores = {}
        
        # 1. 語調穩定性 - 平穩的語調通常是積極的
        if 'pitch_variance' in voice_features:
            pitch = voice_features['pitch_variance']
            scores['pitch'] = 1.0 - min(pitch, 1.0)  # 低變異 = 高分
        
        # 2. 語速 - 適中語速較好
        if 'speech_rate' in voice_features:
            rate = voice_features['speech_rate']
            scores['rate'] = 1.0 - abs(rate - 0.6) * 2  # 0.6 是理想值
        
        # 3. 能量 - 有活力但不过於激動
        if 'energy' in voice_features:
            energy = voice_features['energy']
            scores['energy'] = energy
        
        # 4. 語調方向（如果有情感分類）
        if 'sentiment' in voice_features:
            sentiment = voice_features['sentiment']
            if sentiment == 'positive':
                scores['sentiment'] = 0.8
            elif sentiment == 'neutral':
                scores['sentiment'] = 0.5
            else:
                scores['sentiment'] = 0.2
        
        # 計算加權平均
        if scores:
            score = sum(scores.values()) / len(scores)
        else:
            score = 0.5
        
        score = max(0.0, min(1.0, score))
        
        return {
            'type': 'voice',
            'score': score,
            'details': {
                'features': voice_features,
                'component_scores': scores
            },
            'timestamp': datetime.now().isoformat()
        }
    
    # ========================
    # 文字分析
    # ========================
    
    def analyze_text(self, text: str, sentiment_result: Optional[Dict] = None) -> Dict[str, Any]:
        """
        分析文字情感
        
        Args:
            text: 用戶說的話
            sentiment_result: 情感分析結果 (可選)
        
        Returns:
            文字分析結果
        """
        if not text and not sentiment_result:
            return self._empty_result('text')
        
        if sentiment_result:
            # 使用傳入的情感分析結果
            label = sentiment_result.get('label', 'neutral')
            confidence = sentiment_result.get('confidence', 0.5)
            
            if label == 'positive':
                score = 0.7 + (confidence * 0.3)
            elif label == 'negative':
                score = 0.3 - (confidence * 0.2)
            else:
                score = 0.5
            
            keywords = sentiment_result.get('keywords', [])
        else:
            # 簡單的基於關鍵詞的分析
            score, keywords = self._simple_keyword_analysis(text)
        
        score = max(0.0, min(1.0, score))
        
        return {
            'type': 'text',
            'score': score,
            'text': text,
            'details': {
                'sentiment': sentiment_result.get('label', 'unknown') if sentiment_result else 'analyzed',
                'keywords': keywords
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def _simple_keyword_analysis(self, text: str) -> tuple:
        """簡單的關鍵詞情感分析"""
        positive_words = ['喜歡', '開心', '好', '棒', '讚', '愛', '美', '厲害', '厲害', '不錯', 'happy', 'love', 'good', 'great']
        negative_words = ['不喜歡', '難過', '差', '糟', '討厭', '恨', '醜', '爛', '無聊', 'sad', 'hate', 'bad', 'terrible']
        
        text_lower = text.lower()
        
        pos_count = sum(1 for w in positive_words if w in text_lower)
        neg_count = sum(1 for w in negative_words if w in text_lower)
        
        keywords = [w for w in positive_words + negative_words if w in text_lower]
        
        if pos_count > neg_count:
            score = 0.7
        elif neg_count > pos_count:
            score = 0.3
        else:
            score = 0.5
        
        return score, keywords
    
    # ========================
    # 整合決策
    # ========================
    
    def calculate_final_score(
        self,
        emotion_result: Optional[Dict] = None,
        voice_result: Optional[Dict] = None,
        text_result: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        整合三種情緒輸入，計算最終喜好狀態
        
        Returns:
            {
                'score': 0.0-1.0,
                'status': 'High' | 'Normal' | 'Low',
                'breakdown': {...},
                'confidence': 0.0-1.0
            }
        """
        scores = {}
        
        # 收集各類型分數
        if emotion_result:
            scores['emotion'] = emotion_result['score']
        if voice_result:
            scores['voice'] = voice_result['score']
        if text_result:
            scores['text'] = text_result['score']
        
        # 計算加權平均
        if scores:
            final_score = sum(
                scores.get(key, 0.5) * weight 
                for key, weight in self.weights.items()
                if key in scores
            )
            # 標準化
            available_weights = sum(self.weights[k] for k in scores.keys())
            if available_weights > 0:
                final_score /= available_weights
        else:
            final_score = 0.5
        
        # 判斷狀態
        if final_score >= self.thresholds['high']:
            status = 'High'
        elif final_score >= self.thresholds['normal']:
            status = 'Normal'
        else:
            status = 'Low'
        
        # 計算自信心
        confidence = self._calculate_confidence(scores)
        
        return {
            'score': final_score,
            'status': status,
            'breakdown': scores,
            'confidence': confidence,
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_confidence(self, scores: Dict[str, float]) -> float:
        """
        計算判斷的自信心
        
        邏輯：
        - 數據來源越多，自信心越高
        - 各來源分數越接近，自信心越高
        """
        if not scores:
            return 0.0
        
        # 數據來源數量
        source_count = len(scores)
        source_score = min(source_count / 3, 1.0) * 0.3
        
        # 分數一致性
        if len(scores) > 1:
            std = np.std(list(scores.values()))
            consistency_score = (1 - min(std * 2, 1)) * 0.7
        else:
            consistency_score = 0.5 * 0.7
        
        confidence = source_score + consistency_score
        return max(0.0, min(1.0, confidence))
    
    def _empty_result(self, emotion_type: str) -> Dict[str, Any]:
        """返回空的結果"""
        return {
            'type': emotion_type,
            'score': 0.5,
            'details': {},
            'timestamp': datetime.now().isoformat()
        }
    
    # ========================
    # 批次分析
    # ========================
    
    def analyze_session(
        self,
        emotion_data_list: List[Dict] = None,
        voice_data_list: List[Dict] = None,
        text_data_list: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        分析整個會話的情緒數據
        
        對一段時間內的所有數據進行聚合分析
        """
        # 處理表情數據
        emotion_results = []
        if emotion_data_list:
            for data in emotion_data_list:
                if 'emotions' in data:
                    result = self.analyze_emotion(data['emotions'])
                    emotion_results.append(result['score'])
        
        # 處理語音數據
        voice_results = []
        if voice_data_list:
            for data in voice_data_list:
                if 'features' in data:
                    result = self.analyze_voice(data['features'])
                    voice_results.append(result['score'])
        
        # 處理文字數據
        text_results = []
        if text_data_list:
            for data in text_data_list:
                if 'text' in data:
                    result = self.analyze_text(data['text'], data.get('sentiment'))
                    text_results.append(result['score'])
        
        # 計算平均分數
        avg_scores = {}
        if emotion_results:
            avg_scores['emotion'] = sum(emotion_results) / len(emotion_results)
        if voice_results:
            avg_scores['voice'] = sum(voice_results) / len(voice_results)
        if text_results:
            avg_scores['text'] = sum(text_results) / len(text_results)
        
        # 計算最終分數
        final = self._calculate_final_from_averages(avg_scores)
        
        return final
    
    def _calculate_final_from_averages(self, avg_scores: Dict[str, float]) -> Dict[str, Any]:
        """從平均分數計算最終結果"""
        if not avg_scores:
            return {
                'score': 0.5,
                'status': 'Normal',
                'breakdown': {},
                'confidence': 0.0
            }
        
        # 加權平均
        final_score = sum(
            avg_scores.get(key, 0.5) * weight
            for key, weight in self.weights.items()
            if key in avg_scores
        )
        
        # 標準化
        available_weights = sum(self.weights[k] for k in avg_scores.keys())
        if available_weights > 0:
            final_score /= available_weights
        else:
            final_score = 0.5
        
        # 判斷狀態
        if final_score >= self.thresholds['high']:
            status = 'High'
        elif final_score >= self.thresholds['normal']:
            status = 'Normal'
        else:
            status = 'Low'
        
        confidence = self._calculate_confidence(avg_scores)
        
        return {
            'score': final_score,
            'status': status,
            'breakdown': avg_scores,
            'confidence': confidence,
            'timestamp': datetime.now().isoformat()
        }
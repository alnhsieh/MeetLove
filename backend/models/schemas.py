"""
Pydantic 資料模型定義
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum


class EmotionType(str, Enum):
    """情緒類型"""
    EMOTION = "emotion"      # 表情
    VOICE = "voice"          # 語音
    TEXT = "text"            # 文字


class LoveStatus(str, Enum):
    """喜好狀態"""
    HIGH = "High"
    NORMAL = "Normal"
    LOW = "Low"


class MatchRequest(BaseModel):
    """配對請求"""
    user_id: str
    preferences: Optional[Dict[str, Any]] = Field(default_factory=dict)


class MatchResponse(BaseModel):
    """配對回應"""
    success: bool
    session_id: Optional[str] = None
    message: str
    partner_id: Optional[str] = None


class EmotionData(BaseModel):
    """情緒數據"""
    type: EmotionType
    score: float = Field(ge=0, le=1)
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: Optional[datetime] = None


class UserSessionData(BaseModel):
    """用戶會話數據"""
    user_id: str
    sid: str
    emotions: List[EmotionData] = Field(default_factory=list)


class SessionResult(BaseModel):
    """會話結果"""
    session_id: str
    users: Dict[str, Dict[str, Any]]
    final_scores: Dict[str, Dict[str, Any]]
    compatibility: float
    created_at: datetime


class EmotionScore(BaseModel):
    """情緒分數"""
    type: EmotionType
    score: float
    confidence: float = 1.0
    details: Dict[str, Any] = Field(default_factory=dict)


class FinalScore(BaseModel):
    """最終分數"""
    score: float
    status: LoveStatus
    breakdown: Dict[str, float]
    confidence: float
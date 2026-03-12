"""
會話相關 API 路由
"""

from fastapi import APIRouter, HTTPException
from typing import Optional

from models.schemas import SessionResult
from services.match_service import MatchService

router = APIRouter()

# 實例化服務
_match_service: Optional[MatchService] = None


def get_match_service() -> MatchService:
    global _match_service
    if _match_service is None:
        _match_service = MatchService()
    return _match_service


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    """取得會話詳情"""
    service = get_match_service()
    session = service.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="會話不存在")
    
    return {
        "session_id": session_id,
        "status": session.get('status', 'unknown'),
        "created_at": session.get('created_at').isoformat() if session.get('created_at') else None,
        "user_a": session.get('user_a', {}).get('user_id'),
        "user_b": session.get('user_b', {}).get('user_id')
    }


@router.get("/session/{session_id}/result")
async def get_session_result(session_id: str):
    """取得會話分析結果"""
    service = get_match_service()
    session = service.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="會話不存在")
    
    if session.get('status') != 'ended':
        # 會話尚未結束，返回當前進度
        emotions_a_count = len(session.get('emotions_a', []))
        emotions_b_count = len(session.get('emotions_b', []))
        
        return {
            "session_id": session_id,
            "status": session.get('status'),
            "message": "會話仍在進行中",
            "data_points": {
                "user_a": emotions_a_count,
                "user_b": emotions_b_count
            }
        }
    
    # 計算最終結果
    final_scores = await service._calculate_final_scores(session)
    compatibility = service._calculate_compatibility(final_scores)
    
    return {
        "session_id": session_id,
        "status": "completed",
        "users": {
            "user_a": {
                "id": session['user_a'].get('user_id'),
                "score": final_scores['user_a']['score'],
                "status": final_scores['user_a']['status'],
                "breakdown": final_scores['user_a']['breakdown']
            },
            "user_b": {
                "id": session['user_b'].get('user_id'),
                "score": final_scores['user_b']['score'],
                "status": final_scores['user_b']['status'],
                "breakdown": final_scores['user_b']['breakdown']
            }
        },
        "compatibility": compatibility,
        "created_at": session.get('created_at').isoformat() if session.get('created_at') else None,
        "ended_at": session.get('ended_at').isoformat() if session.get('ended_at') else None
    }


@router.get("/sessions")
async def list_sessions():
    """列出所有會話"""
    service = get_match_service()
    
    sessions = []
    for session_id, session in service.sessions.items():
        sessions.append({
            "session_id": session_id,
            "status": session.get('status'),
            "created_at": session.get('created_at').isoformat() if session.get('created_at') else None
        })
    
    return {
        "total": len(sessions),
        "sessions": sessions
    }
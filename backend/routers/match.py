"""
配對相關 API 路由
"""

from fastapi import APIRouter, HTTPException
from typing import Optional

from models.schemas import MatchRequest, MatchResponse
from services.match_service import MatchService

router = APIRouter()

# 實例化服務（這裡應該依賴注入，簡化處理）
_match_service: Optional[MatchService] = None


def get_match_service() -> MatchService:
    global _match_service
    if _match_service is None:
        _match_service = MatchService()
    return _match_service


@router.post("/match", response_model=MatchResponse)
async def create_match(request: MatchRequest):
    """
    創建配對（HTTP 備用方案）
    
    注意：主要透過 WebSocket 進行配對，
    此 API 為備用或 RESTful 場景使用
    """
    service = get_match_service()
    
    # 這裡的實現比較有限，因為 HTTP 無法保持長連接
    # 實際使用，建議透過 WebSocket/Socket.IO
    queue_count = service.get_queue_count()
    
    return MatchResponse(
        success=True,
        message=f"已加入配對隊列，目前等待人數：{queue_count}"
    )


@router.get("/match/status")
async def get_match_status():
    """取得配對狀態"""
    service = get_match_service()
    queue_count = service.get_queue_count()
    
    return {
        "queue_count": queue_count,
        "active_sessions": len(service.sessions)
    }


@router.post("/match/leave")
async def leave_match(user_id: str):
    """離開配對"""
    service = get_match_service()
    
    # 找到對應的 sid
    for sid, user in service.sid_to_user.items():
        if user.get('user_id') == user_id:
            await service.remove_from_queue(sid)
            return {"success": True, "message": "已離開配對"}
    
    raise HTTPException(status_code=404, detail="用戶不在配對隊列中")
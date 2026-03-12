"""
MeetLove - 後端主程式
主入口：uvicorn main:app --reload
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import socketio
import asyncio
import uuid
from typing import Dict, Optional
from contextlib import asynccontextmanager

from routers import match, session, auth
from models.schemas import MatchResponse, SessionResult
from services.match_service import MatchService
from services.emotion_service import EmotionAnalysisService

# 創建 FastAPI app
app = FastAPI(
    title="MeetLove API",
    description="個人情緒構成分析及現況情緒反應決策輔助判斷系統",
    version="1.0.0"
)

# 創建 Socket.IO server (async mode)
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    ping_timeout=60,
    ping_interval=25
)

# 包裝成 ASGI app
socket_app = socketio.ASGIApp(sio, app)

# CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全域服務
match_service: Optional[MatchService] = None
emotion_service: Optional[EmotionAnalysisService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用程式生命週期"""
    global match_service, emotion_service
    
    # 啟動時初始化
    print("🚀 MeetLove Backend 啟動中...")
    emotion_service = EmotionAnalysisService()
    match_service = MatchService()
    
    yield
    
    # 關閉時清理
    print("👋 MeetLove Backend 關閉")


app.router.lifespan_context = lifespan


# ========================
# REST API 路由
# ========================

@app.get("/")
async def root():
    """健康檢查"""
    return {
        "status": "ok",
        "message": "MeetLove API 運行中",
        "version": "1.0.0"
    }


@app.get("/api/health")
async def health_check():
    """詳細健康檢查"""
    return {
        "status": "healthy",
        "services": {
            "api": "ok",
            "emotion_analysis": "ok" if emotion_service else "initializing",
            "match_maker": "ok" if match_service else "initializing"
        }
    }


# 掛載路由
app.include_router(match.router, prefix="/api", tags=["配對"])
app.include_router(session.router, prefix="/api", tags=["會話"])
app.include_router(auth.router, prefix="/api", tags=["會員"])


# ========================
# Socket.IO 事件處理
# ========================

@sio.event
async def connect(sid, environ, auth):
    """客戶端連線"""
    print(f"✅ Client connected: {sid}")
    await sio.emit('connected', {'sid': sid})


@sio.event
async def disconnect(sid):
    """客戶端斷線"""
    print(f"❌ Client disconnected: {sid}")
    if match_service:
        await match_service.handle_disconnect(sid)


@sio.event
async def join_queue(sid, data):
    """加入配對隊列"""
    user_id = data.get('user_id', sid)
    user_info = {
        'sid': sid,
        'user_id': user_id,
        'preferences': data.get('preferences', {})
    }
    
    matched = await match_service.add_to_queue(sio, user_info)
    
    if matched:
        # 配對成功，雙方都會收到 matched 事件
        pass
    else:
        # 等待配對
        await sio.emit('waiting', {'message': '等待配對中...'})


@sio.event
async def leave_queue(sid):
    """離開配對隊列"""
    await match_service.remove_from_queue(sid)
    await sio.emit('left_queue', {'message': '已離開隊列'})


@sio.event
async def ready(sid, data):
    """客戶端準備就緒，通知對方"""
    session_id = data.get('session_id')
    if session_id and match_service:
        session = match_service.get_session(session_id)
        if session:
            partner_sid = None
            if session['user_a']['sid'] == sid:
                partner_sid = session['user_b']['sid']
            else:
                partner_sid = session['user_a']['sid']
            
            if partner_sid:
                await sio.emit('partner-ready', {'session_id': session_id}, room=partner_sid)
                print(f"📹 User {sid} is ready, notifying {partner_sid}")


@sio.event
async def signal(sid, data):
    """WebRTC 信號轉發"""
    session_id = data.get('session_id')
    signal_data = data.get('signal')
    
    if session_id and signal_data and match_service:
        session = match_service.get_session(session_id)
        if session:
            # 找出對方
            partner_sid = None
            if session['user_a']['sid'] == sid:
                partner_sid = session['user_b']['sid']
            else:
                partner_sid = session['user_a']['sid']
            
            if partner_sid:
                await sio.emit('signal', {'signal': signal_data}, room=partner_sid)


@sio.event
async def offer(sid, data):
    """WebRTC Offer"""
    session_id = data.get('session_id')
    signal = data.get('signal')
    
    if session_id and match_service:
        session = match_service.get_session(session_id)
        if session:
            partner_sid = None
            if session['user_a']['sid'] == sid:
                partner_sid = session['user_b']['sid']
            else:
                partner_sid = session['user_a']['sid']
            
            if partner_sid:
                await sio.emit('offer', signal, room=partner_sid)
                print(f"📤 Offer sent to {partner_sid}")


@sio.event
async def answer(sid, data):
    """WebRTC Answer"""
    session_id = data.get('session_id')
    signal = data.get('signal')
    
    if session_id and match_service:
        session = match_service.get_session(session_id)
        if session:
            partner_sid = None
            if session['user_a']['sid'] == sid:
                partner_sid = session['user_b']['sid']
            else:
                partner_sid = session['user_a']['sid']
            
            if partner_sid:
                await sio.emit('answer', signal, room=partner_sid)
                print(f"📥 Answer sent to {partner_sid}")


@sio.event
async def ice_candidate(sid, data):
    """ICE Candidate 轉發"""
    session_id = data.get('session_id')
    candidate = data.get('candidate')
    
    if session_id and match_service:
        session = match_service.get_session(session_id)
        if session:
            partner_sid = None
            if session['user_a']['sid'] == sid:
                partner_sid = session['user_b']['sid']
            else:
                partner_sid = session['user_a']['sid']
            
            if partner_sid:
                await sio.emit('ice-candidate', candidate, room=partner_sid)


@sio.event
async def emotion_data(sid, data):
    """接收客戶端傳來的情緒數據"""
    session_id = data.get('session_id')
    emotion_type = data.get('type')  # 'emotion', 'voice', 'text'
    score = data.get('score', 0)
    details = data.get('details', {})
    
    if match_service and session_id:
        # 儲存情緒數據
        await match_service.record_emotion(
            session_id, sid, emotion_type, score, details
        )
        
        # 即時分析並廣播（可選優化）
        # 這裡可以實現即時反饋


@sio.event
async def end_call(sid, data):
    """結束通話"""
    session_id = data.get('session_id')
    if match_service and session_id:
        result = await match_service.end_session(session_id)
        # 廣播結果給雙方
        await sio.emit('session_ended', result, room=session_id)


# 匯出 socket app（給 uvicorn 使用）
# 生產環境：uvicorn main:socket_app --host 0.0.0.0 --port 8000 --workers 4
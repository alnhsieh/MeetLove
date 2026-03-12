"""
會員認證 API 路由
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional

from services.auth_service import auth_service

router = APIRouter()


# ========================
# Request/Response Models
# ========================

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    username: str  # 可為用戶名或郵箱
    password: str


class ProfileUpdateRequest(BaseModel):
    nickname: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    bio: Optional[str] = None
    avatar: Optional[str] = None


class PreferencesUpdateRequest(BaseModel):
    gender_interest: Optional[str] = None  # 'male', 'female', 'any'
    age_range: Optional[list] = None  # [min, max]
    max_distance: Optional[int] = None


# ========================
# API Endpoints
# ========================

@router.post("/auth/register")
async def register(request: RegisterRequest):
    """用戶註冊"""
    try:
        user = auth_service.register(
            username=request.username,
            email=request.email,
            password=request.password
        )
        
        return {
            "success": True,
            "message": "註冊成功",
            "user": {
                "user_id": user['user_id'],
                "username": user['username'],
                "email": user['email'],
                "nickname": user['profile']['nickname']
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="伺服器錯誤")


@router.post("/auth/login")
async def login(request: LoginRequest):
    """用戶登入"""
    try:
        user = auth_service.login(
            username=request.username,
            password=request.password
        )
        
        if not user:
            raise HTTPException(status_code=401, detail="用戶名或密碼錯誤")
        
        return {
            "success": True,
            "message": "登入成功",
            "user": {
                "user_id": user['user_id'],
                "username": user['username'],
                "email": user['email'],
                "nickname": user['profile']['nickname'],
                "profile": user['profile'],
                "stats": user['stats']
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="伺服器錯誤")


@router.get("/auth/user/{user_id}")
async def get_user(user_id: str):
    """取得用戶資料"""
    user = auth_service.get_user(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="用戶不存在")
    
    return {
        "success": True,
        "user": user
    }


@router.put("/auth/profile/{user_id}")
async def update_profile(user_id: str, request: ProfileUpdateRequest):
    """更新用戶資料"""
    try:
        # 過濾掉 None 值
        profile = {k: v for k, v in request.model_dump().items() if v is not None}
        
        user = auth_service.update_profile(user_id, profile)
        
        return {
            "success": True,
            "message": "資料已更新",
            "user": user
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="伺服器錯誤")


@router.put("/auth/preferences/{user_id}")
async def update_preferences(user_id: str, request: PreferencesUpdateRequest):
    """更新配對偏好"""
    try:
        preferences = {k: v for k, v in request.model_dump().items() if v is not None}
        
        user = auth_service.update_preferences(user_id, preferences)
        
        return {
            "success": True,
            "message": "偏好已更新",
            "preferences": user['preferences']
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="伺服器錯誤")


@router.get("/auth/leaderboard")
async def get_leaderboard(limit: int = 10):
    """取得排行榜"""
    leaderboard = auth_service.get_leaderboard(limit)
    
    return {
        "success": True,
        "leaderboard": leaderboard
    }


@router.get("/auth/stats/{user_id}")
async def get_user_stats(user_id: str):
    """取得用戶統計"""
    user = auth_service.get_user(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="用戶不存在")
    
    return {
        "success": True,
        "stats": user['stats']
    }


@router.get("/auth/history/{user_id}")
async def get_emotion_history(user_id: str, limit: int = 20):
    """取得情緒歷史"""
    user = auth_service.get_user(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="用戶不存在")
    
    history = user.get('emotion_history', [])[-limit:]
    
    return {
        "success": True,
        "history": history
    }
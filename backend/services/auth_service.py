"""
用戶認證服務
"""

import json
import uuid
import os
from datetime import datetime, timedelta
from typing import Optional
import hashlib

# 簡單的用戶資料儲存（正式環境應使用資料庫）
USERS_FILE = "data/users.json"


class AuthService:
    def __init__(self):
        self._ensure_data_dir()
        self._ensure_users_file()
        self.jwt_secret = "meetlove-secret-key-2026"  # 生產環境應使用環境變數
    
    def _ensure_data_dir(self):
        """確保數據目錄存在"""
        os.makedirs("data", exist_ok=True)
    
    def _ensure_users_file(self):
        """確保用戶檔案存在"""
        if not os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'w') as f:
                json.dump({}, f)
    
    def _load_users(self) -> dict:
        """載入用戶資料"""
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    
    def _save_users(self, users: dict):
        """儲存用戶資料"""
        with open(USERS_FILE, 'w') as f:
            json.dump(users, f, indent=2, default=str)
    
    def _hash_password(self, password: str) -> str:
        """密碼雜湊"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def register(self, username: str, email: str, password: str) -> dict:
        """註冊新用戶"""
        users = self._load_users()
        
        # 檢查用戶名和郵件是否已存在
        for uid, user in users.items():
            if user.get('username') == username:
                raise ValueError("用戶名已存在")
            if user.get('email') == email:
                raise ValueError("郵箱已被註冊")
        
        # 創建新用戶
        user_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        user = {
            'user_id': user_id,
            'username': username,
            'email': email,
            'password_hash': self._hash_password(password),
            'created_at': now,
            'last_login': now,
            'profile': {
                'nickname': username,
                'gender': None,
                'age': None,
                'bio': '',
                'avatar': None
            },
            'preferences': {
                'gender_interest': 'any',
                'age_range': [18, 99],
                'max_distance': 100
            },
            'emotion_history': [],
            'stats': {
                'total_sessions': 0,
                'total_minutes': 0,
                'high_matches': 0,
                'normal_matches': 0,
                'low_matches': 0
            }
        }
        
        users[user_id] = user
        self._save_users(users)
        
        # 回傳時移除密碼雜湊
        del user['password_hash']
        return user
    
    def login(self, username: str, password: str) -> Optional[dict]:
        """用戶登入"""
        users = self._load_users()
        
        for uid, user in users.items():
            if user.get('username') == username or user.get('email') == username:
                if user.get('password_hash') == self._hash_password(password):
                    # 更新最後登入時間
                    user['last_login'] = datetime.now().isoformat()
                    self._save_users(users)
                    
                    # 回傳時移除密碼雜湊
                    del user['password_hash']
                    return user
                else:
                    raise ValueError("密碼錯誤")
        
        return None
    
    def get_user(self, user_id: str) -> Optional[dict]:
        """取得用戶資料"""
        users = self._load_users()
        user = users.get(user_id)
        
        if user:
            user = user.copy()
            del user['password_hash']
        
        return user
    
    def update_profile(self, user_id: str, profile: dict) -> dict:
        """更新用戶資料"""
        users = self._load_users()
        
        if user_id not in users:
            raise ValueError("用戶不存在")
        
        users[user_id]['profile'].update(profile)
        self._save_users(users)
        
        user = users[user_id].copy()
        del user['password_hash']
        return user
    
    def update_preferences(self, user_id: str, preferences: dict) -> dict:
        """更新配對偏好"""
        users = self._load_users()
        
        if user_id not in users:
            raise ValueError("用戶不存在")
        
        users[user_id]['preferences'].update(preferences)
        self._save_users(users)
        
        user = users[user_id].copy()
        del user['password_hash']
        return user
    
    def update_stats(self, user_id: str, result: str):
        """更新用戶統計"""
        users = self._load_users()
        
        if user_id not in users:
            return
        
        stats = users[user_id].get('stats', {})
        stats['total_sessions'] = stats.get('total_sessions', 0) + 1
        
        if result == 'high':
            stats['high_matches'] = stats.get('high_matches', 0) + 1
        elif result == 'normal':
            stats['normal_matches'] = stats.get('normal_matches', 0) + 1
        else:
            stats['low_matches'] = stats.get('low_matches', 0) + 1
        
        users[user_id]['stats'] = stats
        self._save_users(users)
    
    def record_emotion(self, user_id: str, emotion_data: dict):
        """記錄用戶情緒歷史"""
        users = self._load_users()
        
        if user_id not in users:
            return
        
        emotion_record = {
            'timestamp': datetime.now().isoformat(),
            **emotion_data
        }
        
        emotion_history = users[user_id].get('emotion_history', [])
        emotion_history.append(emotion_record)
        
        # 只保留最近 100 筆
        emotion_history = emotion_history[-100:]
        users[user_id]['emotion_history'] = emotion_history
        self._save_users(users)
    
    def get_leaderboard(self, limit: int = 10) -> list:
        """取得排行榜（按高分匹配次數）"""
        users = self._load_users()
        
        leaderboard = []
        for uid, user in users.items():
            stats = user.get('stats', {})
            leaderboard.append({
                'user_id': uid,
                'username': user.get('username'),
                'nickname': user.get('profile', {}).get('nickname'),
                'total_sessions': stats.get('total_sessions', 0),
                'high_matches': stats.get('high_matches', 0),
                'normal_matches': stats.get('normal_matches', 0)
            })
        
        # 按高分匹配次數排序
        leaderboard.sort(key=lambda x: x['high_matches'], reverse=True)
        return leaderboard[:limit]


# 單例
auth_service = AuthService()
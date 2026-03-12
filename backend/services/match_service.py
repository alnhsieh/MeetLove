"""
配對服務 - Match Service
處理用戶配對、會話管理、喜好分析
"""

import asyncio
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
import socketio

from models.schemas import MatchRequest, MatchResponse, SessionResult, EmotionData
from services.auth_service import auth_service


class MatchService:
    """配對服務"""
    
    def __init__(self):
        # 等待配對的隊列
        self.queue: Dict[str, Dict[str, Any]] = {}
        # 進行中的會話 {session_id: {user_a: {...}, user_b: {...}, emotions: {...}}}
        self.sessions: Dict[str, Dict[str, Any]] = {}
        # sid -> session_id 映射
        self.sid_to_session: Dict[str, str] = {}
        # sid -> user_info 映射
        self.sid_to_user: Dict[str, Dict[str, Any]] = {}
    
    async def add_to_queue(
        self, 
        sio: socketio.AsyncServer, 
        user_info: Dict[str, Any]
    ) -> bool:
        """
        加入配對隊列
        返回 True 表示配對成功
        """
        sid = user_info['sid']
        user_id = user_info['user_id']
        
        # 取得用戶偏好
        user = auth_service.get_user(user_id)
        preferences = user.get('preferences', {}) if user else {}
        
        user_info['preferences'] = preferences
        user_info['profile'] = user.get('profile', {}) if user else {}
        
        # 智能匹配 - 根據偏好篩選
        compatible_matches = []
        for waiting_sid, waiting_user in self.queue.items():
            if self._is_compatible(user_info, waiting_user):
                compatible_matches.append((waiting_sid, waiting_user))
        
        if compatible_matches:
            # 選擇第一個相容的匹配
            other_sid, other_user = compatible_matches[0]
            del self.queue[other_sid]
        elif self.queue:
            # 沒有相容匹配，但隊列有人，先放進隊列
            self.queue[sid] = user_info
            self.sid_to_user[sid] = user_info
            print(f"⏳ 用戶 {user_id} 加入等待隊列 (無相容匹配)")
            
            # 嘗試找其他相容匹配
            await sio.emit('waiting', {
                'message': '等待相容的配對中...',
                'queue_position': len(self.queue)
            })
            return False
        else:
            # 沒有任何人，直接加入隊列
            pass
        
        # 如果沒有找到匹配，加入隊列
        if not compatible_matches and not self.queue:
            self.queue[sid] = user_info
            self.sid_to_user[sid] = user_info
            await sio.emit('waiting', {
                'message': '等待配對中...',
                'queue_position': len(self.queue)
            })
            print(f"⏳ 用戶 {user_id} 加入等待隊列")
            return False
        
        # 配對成功，創建會話
        session_id = str(uuid.uuid4())
        
        # 雙方用戶資料
        user_a = {
            'sid': other_sid,
            'user_id': other_user['user_id'],
            'session_id': session_id,
            'profile': other_user.get('profile', {}),
            'preferences': other_user.get('preferences', {})
        }
        user_b = {
            'sid': sid,
            'user_id': user_id,
            'session_id': session_id,
            'profile': user_info.get('profile', {}),
            'preferences': preferences
        }
        
        # 計算初始匹配度（基於偏好）
        initial_compatibility = self._calculate_preference_match(
            user_info.get('preferences', {}),
            other_user.get('profile', {})
        )
        
        # 儲存會話
        self.sessions[session_id] = {
            'user_a': user_a,
            'user_b': user_b,
            'emotions_a': [],
            'emotions_b': [],
            'created_at': datetime.now(),
            'status': 'active',
            'initial_compatibility': initial_compatibility,
            'real_time_scores': []
        }
        
        # 更新映射
        self.sid_to_session[other_sid] = session_id
        self.sid_to_session[sid] = session_id
        self.sid_to_user[other_sid] = other_user
        self.sid_to_user[sid] = user_info
        
        # 通知雙方配對成功
        room = session_id
        
        await sio.enter_room(other_sid, room)
        await sio.enter_room(sid, room)
        
        # 配對成功事件
        await sio.emit('matched', {
            'session_id': session_id,
            'partner_id': user_id,
            'partner_sid': sid,
            'partner_profile': user_info.get('profile', {}),
            'initial_compatibility': initial_compatibility
        }, room=room)
        
        print(f"🎉 配對成功: {user_id} <-> {other_user['user_id']}, session: {session_id}")
        print(f"   初始匹配度: {initial_compatibility:.1%}")
        return True
    
    def _is_compatible(self, user1: Dict, user2: Dict) -> bool:
        """檢查兩個用戶是否相容"""
        prefs1 = user1.get('preferences', {})
        profile2 = user2.get('profile', {})
        
        # 性別偏好
        gender_interest = prefs1.get('gender_interest', 'any')
        if gender_interest != 'any':
            user_gender = profile2.get('gender')
            if user_gender and user_gender != gender_interest:
                return False
        
        # 年齡偏好
        age = profile2.get('age')
        if age:
            age_range = prefs1.get('age_range', [18, 99])
            if age < age_range[0] or age > age_range[1]:
                return False
        
        return True
    
    def _calculate_preference_match(self, preferences: Dict, profile: Dict) -> float:
        """計算基於偏好的匹配度"""
        score = 0.5  # 基礎分數
        
        # 性別匹配
        gender_interest = preferences.get('gender_interest', 'any')
        user_gender = profile.get('gender')
        
        if gender_interest == 'any':
            score += 0.2
        elif user_gender == gender_interest:
            score += 0.2
        
        # 年齡範圍
        age = profile.get('age')
        if age:
            age_range = preferences.get('age_range', [18, 99])
            if age_range[0] <= age <= age_range[1]:
                score += 0.1
        
        return min(score, 1.0)
    
    async def remove_from_queue(self, sid: str):
        """從隊列中移除"""
        if sid in self.queue:
            user_id = self.queue[sid]['user_id']
            del self.queue[sid]
            print(f"🚪 用戶 {user_id} 離開等待隊列")
    
    async def handle_disconnect(self, sid: str):
        """處理客戶端斷線"""
        # 從隊列移除
        await self.remove_from_queue(sid)
        
        # 從會話移除
        if sid in self.sid_to_session:
            session_id = self.sid_to_session[sid]
            if session_id in self.sessions:
                session = self.sessions[session_id]
                session['status'] = 'ended'
                session['ended_at'] = datetime.now()
                print(f"❌ 會話 {session_id} 結束 (用戶斷線)")
            
            del self.sid_to_session[sid]
    
    async def record_emotion(
        self,
        session_id: str,
        sid: str,
        emotion_type: str,
        score: float,
        details: Dict[str, Any]
    ):
        """記錄情緒數據"""
        if session_id not in self.sessions:
            return
        
        session = self.sessions[session_id]
        
        emotion_record = {
            'type': emotion_type,
            'score': score,
            'details': details,
            'timestamp': datetime.now()
        }
        
        # 判斷是哪個用戶
        if session['user_a']['sid'] == sid:
            session['emotions_a'].append(emotion_record)
            
            # 記錄到用戶歷史
            user_id = session['user_a']['user_id']
            auth_service.record_emotion(user_id, {
                'type': emotion_type,
                'score': score,
                'session_id': session_id
            })
            
        elif session['user_b']['sid'] == sid:
            session['emotions_b'].append(emotion_record)
            
            # 記錄到用戶歷史
            user_id = session['user_b']['user_id']
            auth_service.record_emotion(user_id, {
                'type': emotion_type,
                'score': score,
                'session_id': session_id
            })
        
        # 即時計算並廣播當前匹配度
        realtime_compatibility = self._calculate_realtime_compatibility(session)
        
        # 可以選擇廣播即時匹配度給雙方
        # await sio.emit('compatibility_update', {
        #     'session_id': session_id,
        #     'compatibility': realtime_compatibility
        # }, room=session_id)
    
    async def end_session(self, session_id: str) -> Dict[str, Any]:
        """結束會話並返回結果"""
        if session_id not in self.sessions:
            return {'error': 'Session not found'}
        
        session = self.sessions[session_id]
        session['status'] = 'ended'
        session['ended_at'] = datetime.now()
        
        # 計算最終分數
        final_scores = await self._calculate_final_scores(session)
        
        # 計算雙方匹配度
        compatibility = self._calculate_compatibility(final_scores)
        
        # 整合初始匹配度和實際匹配度
        initial_compat = session.get('initial_compatibility', 0.5)
        
        # 最終匹配度 = 初始偏好匹配度 × 0.3 + 實際情緒匹配度 × 0.7
        final_compatibility = (initial_compat * 0.3) + (compatibility * 0.7)
        
        # 判斷結果
        result_a = final_scores['user_a']['status']
        result_b = final_scores['user_b']['status']
        
        # 更新用戶統計
        user_id_a = session['user_a']['user_id']
        user_id_b = session['user_b']['user_id']
        
        auth_service.update_stats(user_id_a, result_a.lower())
        auth_service.update_stats(user_id_b, result_b.lower())
        
        # 計算通話時長
        duration = (session['ended_at'] - session['created_at']).total_seconds() / 60
        
        result = {
            'session_id': session_id,
            'users': {
                'user_a': {
                    'id': session['user_a']['user_id'],
                    'score': final_scores['user_a']['score'],
                    'status': final_scores['user_a']['status'],
                    'breakdown': final_scores['user_a']['breakdown']
                },
                'user_b': {
                    'id': session['user_b']['user_id'],
                    'score': final_scores['user_b']['score'],
                    'status': final_scores['user_b']['status'],
                    'breakdown': final_scores['user_b']['breakdown']
                }
            },
            'compatibility': {
                'initial': initial_compat,
                'realtime': compatibility,
                'final': final_compatibility,
                'label': 'High' if final_compatibility >= 0.7 else 'Normal' if final_compatibility >= 0.4 else 'Low'
            },
            'duration_minutes': round(duration, 1),
            'created_at': session['created_at'].isoformat()
        }
        
        print(f"📊 會話結果: {session_id}")
        print(f"   User A: {result_a} ({final_scores['user_a']['score']:.2f})")
        print(f"   User B: {result_b} ({final_scores['user_b']['score']:.2f})")
        print(f"   匹配度: {final_compatibility:.1%}")
        
        # 清理會話
        user_a_sid = session['user_a']['sid']
        user_b_sid = session['user_b']['sid']
        
        if user_a_sid in self.sid_to_session:
            del self.sid_to_session[user_a_sid]
        if user_b_sid in self.sid_to_session:
            del self.sid_to_session[user_b_sid]
        
        return result
    
    async def _calculate_final_scores(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """計算最終分數"""
        # 簡單的計算 - 實際應該調用 EmotionAnalysisService
        def calc_score(emotions: List[Dict]) -> Dict[str, Any]:
            if not emotions:
                return {'score': 0.5, 'status': 'Normal', 'breakdown': {}}
            
            # 按類型分組
            by_type = {}
            for e in emotions:
                t = e['type']
                if t not in by_type:
                    by_type[t] = []
                by_type[t].append(e['score'])
            
            # 計算各類型平均
            breakdown = {}
            for t, scores in by_type.items():
                breakdown[t] = sum(scores) / len(scores) if scores else 0.5
            
            # 加權計算最終分數
            weights = {'emotion': 0.4, 'voice': 0.3, 'text': 0.3}
            score = sum(breakdown.get(t, 0.5) * weights.get(t, 0) for t in breakdown)
            
            # 判斷狀態
            if score >= 0.7:
                status = 'High'
            elif score >= 0.4:
                status = 'Normal'
            else:
                status = 'Low'
            
            return {'score': score, 'status': status, 'breakdown': breakdown}
        
        return {
            'user_a': calc_score(session['emotions_a']),
            'user_b': calc_score(session['emotions_b'])
        }
    
    def _calculate_compatibility(self, final_scores: Dict[str, Any]) -> float:
        """計算雙方匹配度"""
        score_a = final_scores['user_a'].get('score', 0.5)
        score_b = final_scores['user_b'].get('score', 0.5)
        
        # 使用餘弦相似度概念
        # 越接近 1 表示越匹配
        compatibility = 1 - abs(score_a - score_b)
        return compatibility
    
    def _calculate_realtime_compatibility(self, session: Dict[str, Any]) -> float:
        """計算即時匹配度"""
        emotions_a = session.get('emotions_a', [])
        emotions_b = session.get('emotions_b', [])
        
        if not emotions_a or not emotions_b:
            return session.get('initial_compatibility', 0.5)
        
        # 計算最新分數
        latest_a = emotions_a[-1]['score'] if emotions_a else 0.5
        latest_b = emotions_b[-1]['score'] if emotions_b else 0.5
        
        # 雙方分數越接近，匹配度越高
        return 1 - abs(latest_a - latest_b)
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """取得會話資料"""
        return self.sessions.get(session_id)
    
    def get_queue_count(self) -> int:
        """取得等待人數"""
        return len(self.queue)
    
    def get_queue_info(self) -> Dict[str, Any]:
        """取得隊列資訊"""
        return {
            'waiting_count': len(self.queue),
            'active_sessions': len([s for s in self.sessions.values() if s.get('status') == 'active']),
            'waiting_users': [
                {
                    'sid': sid,
                    'user_id': user.get('user_id'),
                    'profile': user.get('profile', {})
                }
                for sid, user in self.queue.items()
            ]
        }
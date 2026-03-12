# MeetLove 技術規格說明書

**版本：** v1.0  
**日期：** 2026-03-11  
**目標：** MVP 原型  

---

## 1. 系統架構總覽

```
┌─────────────────────────────────────────────────────────────────┐
│                         客戶端 (瀏覽器)                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   React     │  │   WebRTC    │  │   TensorFlow.js         │ │
│  │   前端      │  │   視訊通話   │  │   表情辨識 + 情緒分析   │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
│          │               │                     │               │
│          └───────────────┼─────────────────────┘               │
│                          │                                       │
│                    Socket.io                                     │
└──────────────────────────┼─────────────────────────────────────┘
                           │
┌──────────────────────────┼─────────────────────────────────────┐
│                    後端伺服器                                     │
├──────────────────────────┼─────────────────────────────────────┤
│                          │                                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    FastAPI (Python)                       │  │
│  ├─────────────┬─────────────┬─────────────┬───────────────┤  │
│  │  WebRTC     │  情緒分析    │  配對邏輯   │   API 控制器   │  │
│  │  Signal     │  (整合)      │             │               │  │
│  └─────────────┴─────────────┴─────────────┴───────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              ML Models (PyTorch/TensorFlow)              │  │
│  │   • 表情分析模型   • 語音情緒模型   • 文字情緒模型        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 技術堆疊

### 2.1 前端

| 技術 | 版本 | 用途 |
|------|------|------|
| React | ^18.x | UI 框架 |
| TypeScript | ^5.x | 類型安全 |
| Vite | ^5.x | 建置工具 |
| simple-peer | ^9.x | WebRTC 包裝 |
| socket.io-client | ^4.x | 即時通訊 |
| @mediapipe/face_mesh | 最新 | 臉部偵測 |
| @tensorflow-models/face-landmarks-detection | 最新 | 表情特徵 |
| TensorFlow.js | ^4.x | 瀏覽器端 ML |

### 2.2 後端

| 技術 | 版本 | 用途 |
|------|------|------|
| Python | 3.10+ | 執行環境 |
| FastAPI | ^0.100 | Web 框架 |
| Uvicorn | ^0.23 | ASGI 伺服器 |
| Socket.IO | ^4.x | 即時通訊 |
| OpenCV | ^4.x | 影像處理 |
| PyTorch | ^2.x | ML 框架 |
| numpy | ^1.24 | 數值計算 |
| aiohttp | ^3.x | HTTP 客戶端 |

### 2.3 資料庫（可選）

| 技術 | 用途 |
|------|------|
| SQLite | MVP 本地儲存 |
| PostgreSQL | 正式環境 |

---

## 3. 功能模組詳情

### 3.1 視訊通話模組

**功能：** 1對1 WebRTC 視訊通話

**流程：**
```
1. 用戶A 進入配對 → 等待隊列
2. 用戶B 進入配對 → 與A配對
3. Socket.io 交換 SDP offer/answer
4. 透過 STUN/TURN 建立 P2P 連線
5. 雙方進行視訊對話
6. 即時分析雙方情緒
```

**關鍵程式碼概念：**
```python
# FastAPI + Socket.IO 訊號交換
@sio.on('offer')
async def handle_offer(sid, data):
    # 轉發給另一位用戶
    await sio.emit('offer', data, room=partner_room)

@sio.on('answer')
async def handle_answer(sid, data):
    await sio.emit('answer', data, room=partner_room)

@sio.on('ice-candidate')
async def handle_ice(sid, data):
    await sio.emit('ice-candidate', data, room=partner_room)
```

### 3.2 表情分析模組

**功能：** 即時偵測臉部表情 → 情緒分類

**使用的情緒類別：**
- 😊 開心 (Happy)
- 😢 悲傷 (Sad)
- 😠 生氣 (Angry)
- 😲 驚訝 (Surprised)
- 😨 恐懼 (Fearful)
- 🤢 厭惡 (Disgusted)
- 😐 中性 (Neutral)

**技術方案：**
1. **瀏覽器端：** MediaPipe Face Mesh + 自訂表情分類器
2. **伺服器端（可選）：** 更精確的 PyTorch 模型

**情緒分數計算：**
```python
def calculate_emotion_score(emotions: dict) -> float:
    """
    將情緒轉換為 0-1 的喜好分數
    開心、驚訝 → 正面 (+分)
    悲傷、生氣、恐懼、厭惡 → 負面 (-分)
    """
    positive_weight = emotions.get('happy', 0) + emotions.get('surprised', 0)
    negative_weight = emotions.get('sad', 0) + emotions.get('angry', 0) + \
                      emotions.get('fearful', 0) + emotions.get('disgusted', 0)
    
    score = (positive_weight - negative_weight + 1) / 2  # 標準化到 0-1
    return max(0, min(1, score))
```

### 3.3 語音分析模組

**功能：** 分析語調、語速、情緒

**特徵提取：**
- 語速 (words per minute)
- 音調變化 (pitch variation)
- 能量強度 (volume/energy)
- 停頓模式 (pause patterns)

**情緒分類：**
```python
# 語音特徵 → 情緒分數
def analyze_voice_features(audio_data) -> dict:
    features = {
        'pitch_variance': calculate_pitch_variance(audio_data),
        'speech_rate': calculate_speech_rate(audio_data),
        'energy_level': calculate_energy(audio_data),
        'sentiment_score': voice_sentiment(audio_data)
    }
    
    # 轉換為喜好分數
    voice_score = (
        features['sentiment_score'] * 0.4 +
        (1 - abs(features['pitch_variance'] - 0.5)) * 0.3 +  # 穩定適當的音調
        (features['energy_level'] / 100) * 0.3
    )
    
    return {
        'features': features,
        'score': voice_score,
        'emotion': map_to_emotion(features)
    }
```

### 3.4 文字分析模組

**功能：** 對話內容情感分析

**實現方式：**
1. **瀏覽器端：** TensorFlow.js NLP 模型
2. **伺服器端：** Python transformers (可選)

**情感分類：**
```python
# 文字 → 情感分數
def analyze_text_sentiment(text: str) -> dict:
    # 使用情感分析模型
    result = sentiment_model(text)
    
    # 計算喜好分數 (0-1)
    positive = result['positive_prob']
    negative = result['negative_prob']
    neutral = result['neutral_prob']
    
    # 喜好分數：正向 > 負向
    score = positive + (neutral * 0.5)
    
    return {
        'text': text,
        'sentiment': result['label'],  # positive/negative/neutral
        'score': score,
        'confidence': result['confidence']
    }
```

### 3.5 整合決策模組

**功能：** 融合三種輸入源 → 最終喜好判斷

**演算法：**

```python
def calculate_love_score(
    emotion_score: float,  # 表情分析 (0-1)
    voice_score: float,    # 語音分析 (0-1)
    text_score: float      # 文字分析 (0-1)
) -> dict:
    """
    整合三種情緒輸入，計算最終喜好狀態
    """
    # 權重設計（可調整）
    weights = {
        'emotion': 0.4,  # 表情最直接
        'voice': 0.3,    # 語音次之
        'text': 0.3      # 文字輔助
    }
    
    # 計算加權平均
    final_score = (
        emotion_score * weights['emotion'] +
        voice_score * weights['voice'] +
        text_score * weights['text']
    )
    
    # 判斷狀態
    if final_score >= 0.7:
        status = 'High'
    elif final_score >= 0.4:
        status = 'Normal'
    else:
        status = 'Low'
    
    return {
        'score': final_score,
        'status': status,
        'breakdown': {
            'emotion': emotion_score,
            'voice': voice_score,
            'text': text_score
        },
        'confidence': calculate_confidence(
            emotion_score, voice_score, text_score
        )
    }

def calculate_confidence(emotion, voice, text) -> float:
    """計算判斷的自信心"""
    std = np.std([emotion, voice, text])
    # 標準差越小，自信心越高
    confidence = 1 - min(std * 2, 1)
    return confidence
```

---

## 4. API 設計

### 4.1 REST API

| Method | Endpoint | 說明 |
|--------|----------|------|
| POST | `/api/match` | 開始配對 |
| GET | `/api/match/{session_id}` | 取得配對狀態 |
| POST | `/api/match/end` | 結束配對 |
| GET | `/api/session/{session_id}/result` | 取得分析結果 |

### 4.2 WebSocket 事件

| Event | Direction | 說明 |
|-------|-----------|------|
| `join_queue` | Client → Server | 加入配對隊列 |
| `matched` | Server → Client | 配對成功 |
| `offer` | Bidirectional | WebRTC SDP |
| `answer` | Bidirectional | WebRTC SDP |
| `ice-candidate` | Bidirectional | ICE 候選 |
| `emotion_update` | Server → Client | 即時情緒更新 |

---

## 5. 資料結構

### 5.1 情緒分析結果

```typescript
interface EmotionResult {
  timestamp: number;
  userId: string;
  modality: 'emotion' | 'voice' | 'text';
  score: number;          // 0-1
  details: {
    // 表情
    primaryEmotion?: string;
    emotions?: Record<string, number>;
    // 語音
    pitch?: number;
    speechRate?: number;
    // 文字
    sentiment?: 'positive' | 'negative' | 'neutral';
    keywords?: string[];
  };
}

interface FinalResult {
  sessionId: string;
  users: {
    userA: { id: string; scores: EmotionResult[] };
    userB: { id: string; scores: EmotionResult[] };
  };
  finalScore: {
    userA: { score: number; status: 'High' | 'Normal' | 'Low' };
    userB: { score: number; status: 'High' | 'Normal' | 'Low' };
  };
  compatibility: number;  // 雙方匹配度
  createdAt: string;
}
```

---

## 6. 部署架構

### 開發環境
```
本機執行：
├── 前端：localhost:5173 (Vite)
└── 後端：localhost:8000 (FastAPI)
```

### MVP 部署
```
├── 前端：Vercel / Netlify (靜態 hosting)
├── 後端：Railway / Render / PythonAnywhere
└── STUN/TURN：Twilio 或自建 Coturn
```

---

## 7. 下一步

1. 確認技術選型是否符合需求
2. 開始實作後端 API
3. 實作前端 React 專案
4. 整合 WebRTC
5. 部署測試

---

*技術規格建立：2026-03-11*
*作者：VVN蝦 🦐*
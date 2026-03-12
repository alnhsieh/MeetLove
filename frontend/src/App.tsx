/*
MeetLove - 主應用程式
*/

import { useState, useEffect, useRef, useCallback } from 'react'
import { io, Socket } from 'socket.io-client'
import VideoCall from './components/VideoCall'
import EmotionDisplay from './components/EmotionDisplay'
import { BACKEND_HOST, BACKEND_PORT } from './config'
import './App.css'

// 類型定義
interface EmotionData {
  type: 'emotion' | 'voice' | 'text'
  score: number
  details: Record<string, unknown>
}

interface MatchData {
  session_id: string
  partner_id: string
  partner_sid: string
}

function App() {
  const [socket, setSocket] = useState<Socket | null>(null)
  const [userId] = useState(() => `user_${Math.random().toString(36).substr(2, 9)}`)
  const [status, setStatus] = useState<'disconnected' | 'connecting' | 'waiting' | 'matched' | 'connected'>('connecting')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [matchData, setMatchData] = useState<MatchData | null>(null)
  const [myScore, setMyScore] = useState<number>(0.5)
  const [partnerScore] = useState<number>(0.5) // TODO: 從服務器獲取對方分數
  const [localStream, setLocalStream] = useState<MediaStream | null>(null)
  const [isStreamReady, setIsStreamReady] = useState(false)
  
  const localVideoRef = useRef<HTMLVideoElement>(null)
  const remoteVideoRef = useRef<HTMLVideoElement>(null)

  // 初始化本地視訊流
  const initLocalStream = useCallback(async () => {
    try {
      // 檢查瀏覽器是否支援
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        console.error('Browser does not support getUserMedia')
        alert('您的瀏覽器不支援視訊通話，請使用 Chrome 或 Edge 瀏覽器')
        return
      }
      
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 640 },
          height: { ideal: 480 },
          facingMode: 'user'
        },
        audio: {
          echoCancellation: true,
          noiseSuppression: true
        }
      })
      
      setLocalStream(stream)
      setIsStreamReady(true)
      console.log('📹 Local stream initialized')
    } catch (err: unknown) {
      console.error('Failed to get local media:', err)
      const error = err as Error
      if (error.name === 'NotAllowedError') {
        alert('請允許相機和麥克風權限後重新整理頁面')
      } else if (error.name === 'NotFoundError') {
        alert('找不到相機或麥克風，請確認設備已連接')
      } else {
        alert('無法存取相機: ' + error.message)
      }
      setStatus('disconnected')
    }
  }, [])

  // 初始化 Socket 連接
  useEffect(() => {
    const newSocket = io(`http://${BACKEND_HOST}:${BACKEND_PORT}`, {
      transports: ['polling'],  // 使用 polling 避免 WebSocket 問題
      autoConnect: true
    })

    newSocket.on('connect', () => {
      console.log('✅ Connected to server')
      setStatus('waiting')
      // 連接成功後初始化視訊
      initLocalStream()
    })

    newSocket.on('connected', (data) => {
      console.log('Socket connected:', data)
      setStatus('waiting')
    })

    newSocket.on('waiting', () => {
      console.log('⏳ Waiting for match...')
      setStatus('waiting')
    })

    newSocket.on('matched', (data: MatchData) => {
      console.log('🎉 Matched!', data)
      setMatchData(data)
      setSessionId(data.session_id)
      setStatus('matched')
    })

    newSocket.on('session_ended', (result) => {
      console.log('📊 Session result:', result)
      if (result.final_scores) {
        alert(`會話結束！\n你的狀態: ${result.final_scores.user_a?.status}\n匹配度: ${Math.round(result.compatibility * 100)}%`)
      }
      setStatus('waiting')
      setSessionId(null)
      setMatchData(null)
    })

    newSocket.on('partner-disconnected', () => {
      console.log('Partner left the call')
      if (remoteVideoRef.current) {
        remoteVideoRef.current.srcObject = null
      }
      setStatus('waiting')
      setSessionId(null)
      setMatchData(null)
    })

    setSocket(newSocket)

    return () => {
      newSocket.close()
      // 清理視訊流
      if (localStream) {
        localStream.getTracks().forEach(track => track.stop())
      }
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // 加入配對隊列
  const joinQueue = useCallback(() => {
    if (socket && isStreamReady) {
      setStatus('connecting')
      socket.emit('join_queue', { user_id: userId })
    }
  }, [socket, userId, isStreamReady])

  // 結束通話
  const endCall = useCallback(() => {
    if (socket && sessionId) {
      socket.emit('end_call', { session_id: sessionId })
      
      // 清理遠端視頻
      if (remoteVideoRef.current) {
        remoteVideoRef.current.srcObject = null
      }
      
      setStatus('waiting')
      setSessionId(null)
      setMatchData(null)
    }
  }, [socket, sessionId])

  // 發送情緒數據
  const sendEmotionData = useCallback((emotion: EmotionData) => {
    if (socket && sessionId) {
      socket.emit('emotion_data', {
        session_id: sessionId,
        type: emotion.type,
        score: emotion.score,
        details: emotion.details
      })
      
      // 更新本地分數顯示
      setMyScore(emotion.score)
    }
  }, [socket, sessionId])

  // 處理情緒更新（從 EmotionDisplay 來的回調）
  const handleEmotionUpdate = useCallback((emotion: EmotionData) => {
    sendEmotionData(emotion)
  }, [sendEmotionData])

  // 渲染本地視頻（用於預覽）
  useEffect(() => {
    if (localVideoRef.current && localStream) {
      localVideoRef.current.srcObject = localStream
    }
  }, [localStream])

  return (
    <div className="app">
      <header className="header">
        <h1>🦐 MeetLove</h1>
        <p>AI 情緒配對分析系統</p>
        <div className="user-id">用戶 ID: {userId}</div>
      </header>

      <main className="main">
        {/* 配對狀態區域 */}
        {status === 'disconnected' ? (
          <div className="status-card">
            <div className="status-icon">📡</div>
            <p>連接失敗，請刷新頁面</p>
            <button className="match-btn" onClick={() => window.location.reload()}>
              重新整理
            </button>
          </div>
        ) : status === 'connecting' ? (
          <div className="status-card">
            <div className="status-icon">🔄</div>
            <p>連接伺服器中...</p>
          </div>
        ) : (
          <>
            {/* 配對按鈕 */}
            {status === 'waiting' && !sessionId && (
              <div className="match-section">
                <div className="status-card waiting">
                  <div className="status-icon">🌸</div>
                  <h2>準備好遇見緣分了嗎？</h2>
                  <p>點擊下方按鈕開始配對</p>
                  <button className="match-btn" onClick={joinQueue}>
                    開始配對
                  </button>
                </div>
                
                {/* 預覽視頻 */}
                {isStreamReady && localStream && (
                  <div className="video-preview">
                    <video
                      ref={localVideoRef}
                      autoPlay
                      playsInline
                      muted
                      style={{
                        width: '200px',
                        height: '150px',
                        objectFit: 'cover',
                        borderRadius: '10px',
                        transform: 'scaleX(-1)'
                      }}
                    />
                    <p className="preview-label">預覽</p>
                  </div>
                )}
              </div>
            )}

            {/* 配對成功 - 視訊區域 */}
            {status === 'matched' && matchData && (
              <div className="video-section">
                <div className="match-info">
                  <span>🎉 配對成功！</span>
                  <span>會話 ID: {sessionId}</span>
                </div>
                
                {/* 整合的視訊元件 */}
                <VideoCall
                  socket={socket}
                  sessionId={sessionId}
                  localVideoRef={localVideoRef}
                  remoteVideoRef={remoteVideoRef}
                  localStream={localStream}
                />

                {/* 情緒分析 */}
                <EmotionDisplay
                  videoStream={localStream}
                  onEmotionData={handleEmotionUpdate}
                />

                <button className="end-btn" onClick={endCall}>
                  結束通話
                </button>
              </div>
            )}
          </>
        )}
      </main>

      {/* 分數顯示 */}
      {(status === 'matched' || status === 'connected') && (
        <div className="score-panel">
          <div className="score-item">
            <span>你的喜好分數</span>
            <div className="score-value">{Math.round(myScore * 100)}%</div>
          </div>
          <div className="score-divider">❤️</div>
          <div className="score-item">
            <span>對方喜好分數</span>
            <div className="score-value">{Math.round(partnerScore * 100)}%</div>
          </div>
        </div>
      )}

      <footer className="footer">
        <p>個人情緒構成分析及現況情緒反應決策輔助判斷系統</p>
      </footer>
    </div>
  )
}

export default App
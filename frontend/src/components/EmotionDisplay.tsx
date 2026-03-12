/**
 * EmotionDisplay - 情緒顯示與分析元件
 * 使用 MediaPipe 進行臉部偵測與表情分析
 */

import { useEffect, useRef, useState } from 'react'
import * as faceLandmarksDetection from '@tensorflow-models/face-landmarks-detection'
import '@tensorflow/tfjs-backend-webgl'
import * as tf from '@tensorflow/tfjs'

interface EmotionDisplayProps {
  videoStream: MediaStream | null
  onEmotionData: (emotion: {
    type: 'emotion' | 'voice' | 'text'
    score: number
    details: Record<string, unknown>
  }) => void
}

// 表情到情緒分數的映射
const EMOTION_WEIGHTS: Record<string, number> = {
  happy: 1.0,
  surprised: 0.8,
  neutral: 0.5,
  fearful: 0.3,
  disgusted: 0.2,
  sad: 0.2,
  angry: 0.1
}

export default function EmotionDisplay({ videoStream, onEmotionData }: EmotionDisplayProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [isModelLoading, setIsModelLoading] = useState(true)
  const [currentEmotions, setCurrentEmotions] = useState<Record<string, number>>({})
  const [currentScore, setCurrentScore] = useState(0.5)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const detectorRef = useRef<faceLandmarksDetection.FaceLandmarksDetector | null>(null)
  const animationRef = useRef<number>()
  const lastEmotionSentRef = useRef<number>(0)

  // 初始化模型
  useEffect(() => {
    let mounted = true

    async function loadModel() {
      try {
        await tf.setBackend('webgl')
        await tf.ready()
        console.log('TensorFlow.js ready')

        const model = faceLandmarksDetection.SupportedModels.MediaPipeFaceMesh
        const detectorConfig: faceLandmarksDetection.MediaPipeFaceMeshMediaPipeModelConfig = {
          runtime: 'mediapipe',
          refineLandmarks: true,
          maxFaces: 1
        }

        const detector = await faceLandmarksDetection.createDetector(model, detectorConfig)

        if (mounted) {
          detectorRef.current = detector
          setIsModelLoading(false)
          console.log('Face detector loaded')
        }
      } catch (err) {
        console.error('Failed to load model:', err)
        if (mounted) {
          setIsModelLoading(false)
        }
      }
    }

    loadModel()

    return () => {
      mounted = false
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
      detectorRef.current = null
    }
  }, [])

  // 當收到外部視頻流時，開始分析
  useEffect(() => {
    if (isModelLoading || !detectorRef.current || !videoStream || !videoRef.current) {
      return
    }

    // 將外部流設置到視頻元素
    videoRef.current.srcObject = videoStream
    
    const video = videoRef.current
    
    const startAnalysis = async () => {
      if (!video || video.readyState < 2) {
        // 等待視頻準備好
        await new Promise<void>((resolve) => {
          video.onloadedmetadata = () => resolve()
        })
      }
      
      await video.play()
      setIsAnalyzing(true)
      detectFrame()
    }

    let running = true

    const detectFrame = async () => {
      if (!running || !detectorRef.current || !video || video.paused || video.ended) {
        return
      }

      try {
        const faces = await detectorRef.current.estimateFaces(video)

        if (faces.length > 0) {
          const face = faces[0]
          const emotions = await analyzeEmotion(face)

          setCurrentEmotions(emotions)

          // 計算分數
          const score = calculateEmotionScore(emotions)
          setCurrentScore(score)

          // 節流發送情緒數據（每秒最多一次）
          const now = Date.now()
          if (now - lastEmotionSentRef.current > 1000) {
            lastEmotionSentRef.current = now
            onEmotionData({
              type: 'emotion',
              score,
              details: {
                emotions,
                timestamp: now
              }
            })
          }

          // 繪製臉部標記（調試用，可關閉）
          drawFace(video)
        }
      } catch (err) {
        // 安靜處理錯誤，避免頻繁輸出
      }

      if (running) {
        animationRef.current = requestAnimationFrame(detectFrame)
      }
    }

    startAnalysis()

    return () => {
      running = false
      setIsAnalyzing(false)
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
  }, [isModelLoading, videoStream, onEmotionData])

  // 分析表情
  const analyzeEmotion = async (face: faceLandmarksDetection.Face): Promise<Record<string, number>> => {
    const keypoints = face.keypoints
    if (!keypoints || keypoints.length === 0) {
      return { neutral: 1.0 }
    }

    // 獲取關鍵臉部特徵點
    const getKeypoint = (name: string) => keypoints.find(k => k.name === name)
    
    const mouthLeft = getKeypoint('mouthLeft')
    const mouthRight = getKeypoint('mouthRight')
    const mouthTop = getKeypoint('mouthUpperLip')
    const mouthBottom = getKeypoint('mouthLowerLip')
    const leftEye = getKeypoint('leftEye')
    const leftEyeUpper = getKeypoint('leftEyeUpper')
    const leftEyeLower = getKeypoint('leftEyeLower')
    const rightEyeUpper = getKeypoint('rightEyeUpper')
    const rightEyeLower = getKeypoint('rightEyeLower')
    const leftEyebrowLeft = getKeypoint('leftEyebrowLeft')
    const leftEyebrowRight = getKeypoint('leftEyebrowRight')
    const leftEyebrowUpper = getKeypoint('leftEyebrowUpper')

    const emotions: Record<string, number> = { neutral: 0.5, happy: 0, surprised: 0, sad: 0, angry: 0 }

    // 1. 微笑檢測 - 嘴巴寬度和高度比例
    if (mouthLeft && mouthRight && mouthTop && mouthBottom) {
      const mouthWidth = Math.abs(mouthRight.x - mouthLeft.x)
      const mouthHeight = Math.abs(mouthBottom.y - mouthTop.y)
      const mouthRatio = mouthHeight / (mouthWidth + 0.1)
      
      // 微笑：嘴巴寬，輕微張開
      if (mouthWidth > 40 && mouthRatio > 0.1 && mouthRatio < 0.5) {
        emotions['happy'] = Math.min((mouthWidth - 40) / 40, 1.0) * 0.9
      }
      // 大笑：嘴巴張開較大
      if (mouthRatio > 0.3) {
        emotions['happy'] = Math.max(emotions['happy'], 0.7)
      }
    }

    // 2. 眼睛睜大 - 驚訝檢測
    if (leftEyeUpper && leftEyeLower && rightEyeUpper && rightEyeLower) {
      const leftEyeOpen = Math.abs(leftEyeUpper.y - leftEyeLower.y)
      const rightEyeOpen = Math.abs(rightEyeUpper.y - rightEyeLower.y)
      const avgEyeOpen = (leftEyeOpen + rightEyeOpen) / 2
      
      // 眼睛睜大表示驚訝
      if (avgEyeOpen > 12) {
        emotions['surprised'] = Math.min(avgEyeOpen / 25, 1.0)
      }
    }

    // 3. 眉毛上揚 - 驚訝或擔心
    if (leftEyebrowUpper && leftEyebrowLeft && leftEyebrowRight && leftEye) {
      const eyebrowHeight = leftEyebrowUpper.y
      const eyeLevel = leftEye.y
      const eyebrowRaise = eyeLevel - eyebrowHeight
      
      // 眉毛抬高
      if (eyebrowRaise > 25) {
        emotions['surprised'] = Math.max(emotions['surprised'], 0.5)
      }
    }

    // 4. 悲傷檢測 - 嘴角向下
    if (mouthLeft && mouthRight && mouthTop && mouthBottom) {
      const mouthHeight = Math.abs(mouthBottom.y - mouthTop.y)
      
      // 嘴角向下彎曲（相對於嘴巴高度）
      if (mouthHeight > 10) {
        emotions['sad'] = 0.3
      }
    }

    // 歸一化情緒分數
    const total = Object.values(emotions).reduce((a, b) => a + b, 0)
    if (total > 0) {
      for (const key of Object.keys(emotions)) {
        emotions[key] = emotions[key] / total
      }
    }

    // 確保有中性情緒
    if (emotions['happy'] < 0.3 && emotions['surprised'] < 0.3 && emotions['sad'] < 0.3) {
      emotions['neutral'] = 0.7
    }

    return emotions
  }

  // 計算情緒分數
  const calculateEmotionScore = (emotions: Record<string, number>): number => {
    let score = 0.3 // 基礎分數

    for (const [emotion, probability] of Object.entries(emotions)) {
      const weight = EMOTION_WEIGHTS[emotion] || 0.5
      score += probability * weight * 0.7
    }

    return Math.max(0, Math.min(1, score))
  }

  // 繪製臉部標記（調試用）
  const drawFace = (video: HTMLVideoElement) => {
    if (!canvasRef.current || !video) return

    const ctx = canvasRef.current.getContext('2d')
    if (!ctx) return

    // 只有在調試模式才繪製
    // canvasRef.current.style.display = 'block'
    
    canvasRef.current.width = video.videoWidth || 640
    canvasRef.current.height = video.videoHeight || 480

    // ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height)
  }

  // 獲取狀態文字和顏色
  const getStatusInfo = () => {
    if (currentScore >= 0.7) return { text: 'High', color: 'high', emoji: '💖' }
    if (currentScore >= 0.4) return { text: 'Normal', color: 'normal', emoji: '💛' }
    return { text: 'Low', color: 'low', emoji: '💔' }
  }

  const statusInfo = getStatusInfo()

  return (
    <div className="emotion-panel">
      <h3>🤖 即時情緒分析</h3>
      
      {isModelLoading ? (
        <div className="loading">載入模型中...</div>
      ) : !videoStream ? (
        <div className="loading">等待視訊鏡頭...</div>
      ) : !isAnalyzing ? (
        <div className="loading">啟動分析中...</div>
      ) : (
        <>
          {/* 隱藏的視訊元素用於分析 */}
          <video
            ref={videoRef}
            style={{ display: 'none' }}
            width={640}
            height={480}
            autoPlay
            playsInline
            muted
          />
          <canvas ref={canvasRef} style={{ display: 'none' }} />

          {/* 情緒顯示 */}
          <div className="emotion-bars">
            {Object.entries(currentEmotions).map(([emotion, value]) => (
              <div key={emotion} className="emotion-item">
                <div className="emotion-label">{emotion}</div>
                <div className="emotion-bar">
                  <div
                    className={`emotion-fill ${value > 0.5 ? 'high' : value > 0.3 ? 'normal' : 'low'}`}
                    style={{ width: `${value * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>

          {/* 總分數 */}
          <div className="emotion-score">
            <span className="score-label">情緒狀態：</span>
            <span className={`score-badge ${statusInfo.color}`}>
              {statusInfo.emoji} {statusInfo.text} ({Math.round(currentScore * 100)}%)
            </span>
          </div>
        </>
      )}

      <style>{`
        .emotion-panel {
          background: white;
          border-radius: 15px;
          padding: 1.5rem;
          margin-top: 1.5rem;
          box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
        }
        .emotion-panel h3 {
          margin-bottom: 1rem;
          color: #333;
          text-align: center;
        }
        .loading {
          text-align: center;
          color: #666;
          padding: 2rem;
        }
        .emotion-bars {
          display: flex;
          gap: 1rem;
          justify-content: center;
          flex-wrap: wrap;
          margin-bottom: 1rem;
        }
        .emotion-item {
          text-align: center;
        }
        .emotion-label {
          font-size: 0.75rem;
          color: #666;
          margin-bottom: 0.3rem;
          text-transform: capitalize;
        }
        .emotion-bar {
          width: 60px;
          height: 6px;
          background: #eee;
          border-radius: 3px;
          overflow: hidden;
        }
        .emotion-fill {
          height: 100%;
          transition: width 0.3s ease;
          border-radius: 3px;
        }
        .emotion-fill.high { background: #2ecc71; }
        .emotion-fill.normal { background: #f39c12; }
        .emotion-fill.low { background: #e74c3c; }
        .emotion-score {
          text-align: center;
          padding-top: 1rem;
          border-top: 1px solid #eee;
        }
        .score-label {
          color: #666;
          margin-right: 0.5rem;
        }
        .score-badge {
          padding: 0.3rem 1rem;
          border-radius: 20px;
          font-weight: 600;
        }
        .score-badge.high {
          background: #d4edda;
          color: #155724;
        }
        .score-badge.normal {
          background: #fff3cd;
          color: #856404;
        }
        .score-badge.low {
          background: #f8d7da;
          color: #721c24;
        }
      `}</style>
    </div>
  )
}
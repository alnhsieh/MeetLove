/* @refresh reload */
import { useEffect, useRef, useCallback, useState } from 'react'
import { Socket } from 'socket.io-client'
import Peer from 'simple-peer'

interface VideoCallProps {
  socket: Socket | null
  sessionId: string | null
  localVideoRef: React.RefObject<HTMLVideoElement>
  remoteVideoRef: React.RefObject<HTMLVideoElement>
  localStream: MediaStream | null
}

export default function VideoCall({ 
  socket, 
  sessionId, 
  localVideoRef, 
  remoteVideoRef,
  localStream 
}: VideoCallProps) {
  const peerRef = useRef<Peer.Instance | null>(null)
  const [isConnecting, setIsConnecting] = useState(false)
  const [isConnected, setIsConnected] = useState(false)

  // 處理 WebRTC 信號
  useEffect(() => {
    if (!socket || !sessionId) return

    // 處理配對成功後的 WebRTC 連線
    socket.on('partner-ready', () => {
      console.log('Partner is ready, creating peer...')
      createPeer(true)
    })

    socket.on('offer', (signal: Peer.SignalData) => {
      console.log('Received offer:', signal)
      if (peerRef.current) {
        peerRef.current.signal(signal)
      } else {
        createPeer(false, signal)
      }
    })

    socket.on('answer', (signal: Peer.SignalData) => {
      console.log('Received answer')
      if (peerRef.current) {
        peerRef.current.signal(signal)
      }
    })

    socket.on('signal', (data: { signal: Peer.SignalData }) => {
      console.log('Received signal from server')
      if (peerRef.current) {
        peerRef.current.signal(data.signal)
      }
    })

    socket.on('ice-candidate', (candidate: unknown) => {
      console.log('Received ICE candidate')
      if (peerRef.current) {
        try {
          peerRef.current.signal(candidate as Peer.SignalData)
        } catch (e) {
          console.warn('Failed to signal ICE candidate:', e)
        }
      }
    })

    socket.on('partner-disconnected', () => {
      console.log('Partner disconnected')
      setIsConnected(false)
      if (peerRef.current) {
        peerRef.current.destroy()
        peerRef.current = null
      }
      if (remoteVideoRef.current) {
        remoteVideoRef.current.srcObject = null
      }
    })

    return () => {
      socket.off('partner-ready')
      socket.off('offer')
      socket.off('answer')
      socket.off('signal')
      socket.off('ice-candidate')
      socket.off('partner-disconnected')
    }
  }, [socket, sessionId, remoteVideoRef])

  // 當本地視訊流準備好時，通知服務器
  useEffect(() => {
    if (socket && sessionId && localStream) {
      console.log('Local stream ready, notifying server')
      socket.emit('ready', { session_id: sessionId })
    }
  }, [socket, sessionId, localStream])

  // 創建 Peer 連線
  const createPeer = useCallback((initiator: boolean, signalData?: Peer.SignalData) => {
    if (!localStream) {
      console.error('No local stream available')
      return
    }

    setIsConnecting(true)

    const peer = new Peer({
      initiator,
      trickle: false,
      stream: localStream
    })

    peer.on('signal', (data) => {
      console.log('Local signal generated')
      if (socket && sessionId) {
        // 根據角色發送不同類型的信號
        if (initiator) {
          socket.emit('offer', { session_id: sessionId, signal: data })
        } else {
          socket.emit('answer', { session_id: sessionId, signal: data })
        }
      }
    })

    peer.on('stream', (remoteStream) => {
      console.log('Received remote stream')
      if (remoteVideoRef.current) {
        remoteVideoRef.current.srcObject = remoteStream
      }
      setIsConnected(true)
      setIsConnecting(false)
    })

    peer.on('connect', () => {
      console.log('Peer connection established')
      setIsConnected(true)
      setIsConnecting(false)
    })

    peer.on('error', (err) => {
      console.error('Peer error:', err)
      setIsConnecting(false)
    })

    peer.on('close', () => {
      console.log('Peer connection closed')
      setIsConnected(false)
    })

    if (signalData) {
      peer.signal(signalData)
    }

    peerRef.current = peer
  }, [localStream, socket, sessionId, remoteVideoRef])

  // 渲染視頻容器
  return (
    <div className="video-container">
      {/* 本地視頻 */}
      <div className="video-wrapper">
        <video
          ref={localVideoRef}
          autoPlay
          playsInline
          muted
          style={{ 
            width: '100%', 
            height: '100%', 
            objectFit: 'cover',
            transform: 'scaleX(-1)' // 鏡像翻轉
          }}
        />
        <div className="video-label">你</div>
      </div>

      {/* 遠程視頻 */}
      <div className="video-wrapper">
        <video
          ref={remoteVideoRef}
          autoPlay
          playsInline
          style={{ 
            width: '100%', 
            height: '100%', 
            objectFit: 'cover' 
          }}
        />
        <div className="video-label">
          {isConnected ? '✅ 連線中' : isConnecting ? '🔄 連線中...' : '等待對方...'}
        </div>
      </div>
    </div>
  )
}
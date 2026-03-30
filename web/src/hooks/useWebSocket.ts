import { useState, useEffect, useRef, useCallback } from 'react'

export interface WSMessage {
  type: 'connected' | 'senses' | 'signal' | 'auto_signal' | 'pong'
  data: any
}

interface UseWebSocketOptions {
  url?: string
  reconnectInterval?: number
  onMessage?: (msg: WSMessage) => void
}

interface UseWebSocketReturn {
  lastMessage: WSMessage | null
  senses: any | null
  signal: any | null
  isConnected: boolean
  sendMessage: (msg: object) => void
}

export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
  const {
    url = `ws://${window.location.host}/ws/live`,
    reconnectInterval = 3000,
    onMessage,
  } = options

  const [lastMessage, setLastMessage] = useState<WSMessage | null>(null)
  const [senses, setSenses] = useState<any | null>(null)
  const [signal, setSignal] = useState<any | null>(null)
  const [isConnected, setIsConnected] = useState(false)

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<number | null>(null)

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(url)

      ws.onopen = () => {
        setIsConnected(true)
        console.log('[WS] Connected')
      }

      ws.onmessage = (event) => {
        try {
          const msg: WSMessage = JSON.parse(event.data)
          setLastMessage(msg)

          if (msg.type === 'senses') {
            setSenses(msg.data)
          } else if (msg.type === 'signal' || msg.type === 'auto_signal') {
            setSignal(msg.data)
          }

          onMessage?.(msg)
        } catch (e) {
          console.error('[WS] Parse error:', e)
        }
      }

      ws.onclose = () => {
        setIsConnected(false)
        console.log('[WS] Disconnected, reconnecting in', reconnectInterval, 'ms')
        reconnectTimer.current = window.setTimeout(connect, reconnectInterval)
      }

      ws.onerror = (err) => {
        console.error('[WS] Error:', err)
        ws.close()
      }

      wsRef.current = ws
    } catch (e) {
      console.error('[WS] Connection failed:', e)
      reconnectTimer.current = window.setTimeout(connect, reconnectInterval)
    }
  }, [url, reconnectInterval, onMessage])

  useEffect(() => {
    connect()
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [connect])

  const sendMessage = useCallback((msg: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg))
    }
  }, [])

  return { lastMessage, senses, signal, isConnected, sendMessage }
}

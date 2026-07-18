import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchState, wsUrl } from '../lib/api'
import type { ClientMessage, DraftState } from '../lib/types'

export type ConnectionStatus =
  | 'connecting' // first attempt
  | 'open'
  | 'reconnecting' // dropped, retrying with backoff
  | 'waking' // several failures in a row: likely Render cold start
  | 'not_found' // invalid token, do not retry

const PING_INTERVAL_MS = 25_000
const MAX_BACKOFF_MS = 15_000

export function useDraftSocket(token: string) {
  const [state, setState] = useState<DraftState | null>(null)
  const [connectionStatus, setConnectionStatus] =
    useState<ConnectionStatus>('connecting')
  const [lastError, setLastError] = useState<string | null>(null)

  const wsRef = useRef<WebSocket | null>(null)
  const stoppedRef = useRef(false)
  const attemptsRef = useRef(0)
  const timersRef = useRef<number[]>([])
  const errorTimerRef = useRef<number | null>(null)

  const showError = useCallback((message: string) => {
    setLastError(message)
    if (errorTimerRef.current !== null) window.clearTimeout(errorTimerRef.current)
    errorTimerRef.current = window.setTimeout(() => setLastError(null), 4000)
  }, [])

  useEffect(() => {
    stoppedRef.current = false
    attemptsRef.current = 0

    // One-off REST snapshot: paints the screen while the socket connects and
    // doubles as a reconnection fallback. WebSockets remain the main channel.
    fetchState(token)
      .then((snapshot) => setState((current) => current ?? snapshot))
      .catch(() => {
        // Server may be cold-starting; the socket retry loop handles it.
      })

    const connect = () => {
      if (stoppedRef.current) return
      const ws = new WebSocket(wsUrl(token))
      wsRef.current = ws

      ws.onopen = () => {
        attemptsRef.current = 0
        setConnectionStatus('open')
        const ping = window.setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }))
          }
        }, PING_INTERVAL_MS)
        timersRef.current.push(ping)
      }

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data as string)
          if (message.type === 'state') setState(message.state as DraftState)
          else if (message.type === 'error') showError(message.message as string)
        } catch {
          // ignore malformed frames
        }
      }

      ws.onclose = (event) => {
        if (stoppedRef.current) return
        if (event.code === 4404) {
          setConnectionStatus('not_found')
          return
        }
        attemptsRef.current += 1
        setConnectionStatus(attemptsRef.current >= 3 ? 'waking' : 'reconnecting')
        const backoff = Math.min(
          1000 * 2 ** (attemptsRef.current - 1),
          MAX_BACKOFF_MS,
        )
        const retry = window.setTimeout(connect, backoff)
        timersRef.current.push(retry)
      }
    }

    connect()

    return () => {
      stoppedRef.current = true
      timersRef.current.forEach((id) => {
        window.clearTimeout(id)
        window.clearInterval(id)
      })
      timersRef.current = []
      wsRef.current?.close()
    }
  }, [token, showError])

  const send = useCallback((message: ClientMessage) => {
    const ws = wsRef.current
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(message))
    }
  }, [])

  return { state, connectionStatus, lastError, send }
}

import { useEffect, useRef, useState } from 'react'

interface Props {
  deadline: number | null
  serverNow: number
}

// Visual countdown only: the server is the authority and resolves the turn
// itself when the deadline passes. We anchor to the server clock offset.
export default function TurnTimer({ deadline, serverNow }: Props) {
  const [now, setNow] = useState(() => Date.now())
  const anchorRef = useRef({ serverNow, receivedAt: Date.now() })

  useEffect(() => {
    anchorRef.current = { serverNow, receivedAt: Date.now() }
  }, [serverNow, deadline])

  useEffect(() => {
    const interval = window.setInterval(() => setNow(Date.now()), 200)
    return () => window.clearInterval(interval)
  }, [])

  if (deadline === null) return <div className="turn-timer turn-timer--idle">–:––</div>

  const elapsed = now - anchorRef.current.receivedAt
  const remainingMs = deadline - anchorRef.current.serverNow - elapsed
  const seconds = Math.max(0, Math.ceil(remainingMs / 1000))
  const label = `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`

  return (
    <div className={`turn-timer${seconds <= 5 ? ' turn-timer--urgent' : ''}`}>
      {label}
    </div>
  )
}

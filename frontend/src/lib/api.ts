import type { DraftState, RoomCreatePayload, RoomLinks } from './types'

export const API_BASE: string = import.meta.env.VITE_API_URL || ''

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init)
  if (!response.ok) {
    let detail = 'Error de comunicación con el servidor.'
    try {
      const body = await response.json()
      if (typeof body.detail === 'string') detail = body.detail
    } catch {
      // keep generic message
    }
    throw new Error(detail)
  }
  return response.json() as Promise<T>
}

export function createRoom(payload: RoomCreatePayload): Promise<RoomLinks> {
  return requestJson<RoomLinks>(`${API_BASE}/api/rooms`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function fetchState(token: string): Promise<DraftState> {
  return requestJson<DraftState>(`${API_BASE}/api/state/${token}`)
}

export function wsUrl(token: string): string {
  const base = API_BASE || window.location.origin
  return `${base.replace(/^http/, 'ws')}/ws/${token}`
}

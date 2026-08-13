// Champion -> lanes map, served slim by our backend (which reduces Meraki's
// large combined file). Cached in localStorage like the Data Dragon catalogue.
// Lane codes are internal ('top'|'jungle'|'mid'|'bot'|'support'); UI labels are
// Spanish. A champion missing from the map matches every lane (never hidden).

import { API_BASE } from './api'
import type { Lane } from './types'

export const LANE_ORDER: Lane[] = ['top', 'jungle', 'mid', 'bot', 'support']

export const LANE_LABELS: Record<Lane, string> = {
  top: 'Top',
  jungle: 'Jungla',
  mid: 'Medio',
  bot: 'Tirador',
  support: 'Soporte',
}

const CACHE_KEY = 'draftpick-lanes-v1'
const CACHE_TTL_MS = 6 * 3600 * 1000

interface Cached {
  savedAt: number
  lanes: Record<string, string[]>
}

function readCache(): Record<string, string[]> | null {
  try {
    const raw = localStorage.getItem(CACHE_KEY)
    if (!raw) return null
    const data = JSON.parse(raw) as Cached
    if (Date.now() - data.savedAt > CACHE_TTL_MS) return null
    return data.lanes
  } catch {
    return null
  }
}

export async function loadChampionLanes(): Promise<Map<string, Lane[]>> {
  let lanes = readCache()
  if (!lanes) {
    const res = await fetch(`${API_BASE}/api/champion-lanes`)
    const body = (await res.json()) as { lanes: Record<string, string[]> }
    lanes = body.lanes ?? {}
    try {
      localStorage.setItem(
        CACHE_KEY,
        JSON.stringify({ savedAt: Date.now(), lanes }),
      )
    } catch {
      // storage full/unavailable: fine, we just refetch next time
    }
  }
  return new Map(Object.entries(lanes) as [string, Lane[]][])
}

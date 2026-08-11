// Post-draft analysis API client + payload types (mirrors backend
// app/analysis/engine.py output). API codes stay in English; the UI layer
// translates them to es-ES.

import { API_BASE } from './api'
import type { Lane, TeamSide } from './types'

export type Confidence = 'alta' | 'media' | 'baja' | 'sin_datos'
export type Archetype = 'engage' | 'poke' | 'peel' | 'flexible'
export type PhaseKey = 'pre15' | '15to25' | 'post30'

export interface LaneMatchupRow {
  lane: Lane
  blue_champion: string
  red_champion: string
  winrate_blue: number | null
  wins: number
  games: number
  confidence: Confidence
  inferred: boolean
}

export interface CompositionBreakdownRow {
  champion_id: string
  engage?: number
  poke?: number
  peel?: number
  frontline?: number
  cc?: number
  missing: boolean
}

export interface TeamCompositionData {
  scores: Record<'engage' | 'poke' | 'peel' | 'frontline' | 'cc', number>
  ranged_count: number
  avg_attack_range: number | null
  damage_mix: Record<'physical' | 'magic' | 'mixed', number>
  damage_warning: 'mostly_physical' | 'mostly_magic' | null
  archetype_primary: Archetype
  archetype_secondary: Archetype | null
  breakdown: CompositionBreakdownRow[]
  partial: boolean
}

export interface PhaseBreakdownRow {
  team: TeamSide
  champion_id: string
  curve: Record<PhaseKey, number>
  source: 'override' | 'heuristic'
  weight: number
}

export interface AnalysisPayload {
  game_number: number
  patch: string
  cached: boolean
  computed_at?: string
  lanes_inferred: boolean
  partial: boolean
  lane_matchups: {
    available: boolean
    stale: boolean
    snapshot_patch: string | null
    rows: LaneMatchupRow[]
  }
  compositions: {
    available: boolean
    stale: boolean
    blue: TeamCompositionData
    red: TeamCompositionData
  }
  phases: {
    available: boolean
    blue: Record<PhaseKey, number>
    red: Record<PhaseKey, number>
    deltas: Record<PhaseKey, number>
    advantage_threshold: number
    breakdown: PhaseBreakdownRow[]
  }
  verdict: {
    total: number
    tier: 'even' | 'slight' | 'clear'
    favors: TeamSide | null
    components: Partial<Record<'lanes' | 'composition' | 'phases', number>>
    weights: Partial<Record<'lanes' | 'composition' | 'phases', number>>
  }
}

export async function fetchAnalysis(
  token: string,
  game?: number,
): Promise<AnalysisPayload> {
  const query = game ? `?game=${game}` : ''
  const response = await fetch(`${API_BASE}/api/analysis/${token}${query}`)
  if (!response.ok) {
    let detail = 'No se ha podido calcular el análisis.'
    try {
      const body = await response.json()
      if (typeof body.detail === 'string') detail = body.detail
    } catch {
      // keep generic message
    }
    throw new Error(detail)
  }
  return response.json() as Promise<AnalysisPayload>
}

export type TeamSide = 'blue' | 'red'
export type Role = TeamSide | 'spectator'
export type ActionType = 'ban' | 'pick'

export interface RoomConfig {
  mode: 'standard' | 'fearless'
  best_of: number
  timer_seconds: number
  blue_name: string
  red_name: string
}

export interface CurrentTurn {
  team: TeamSide
  action_type: ActionType
  slot: number
}

export type DraftStatus =
  | 'waiting'
  | 'in_progress'
  | 'completed'
  | 'series_completed'

export interface DraftState {
  room: RoomConfig
  game_number: number
  status: DraftStatus
  ready: Record<TeamSide, boolean>
  connected: Record<TeamSide, boolean>
  turn_index: number | null
  current_turn: CurrentTurn | null
  deadline: number | null
  server_now: number
  bans: Record<TeamSide, (string | null)[]>
  picks: Record<TeamSide, string[]>
  hovered: string | null
  fearless_blocked: string[]
  your_role: Role
}

export interface RoomLinks {
  room_id: string
  blue_token: string
  red_token: string
  spectator_token: string
}

export interface RoomCreatePayload {
  mode: 'standard' | 'fearless'
  best_of: number
  timer_seconds: number
  blue_name?: string
  red_name?: string
}

export type ClientMessage =
  | { type: 'ready' }
  | { type: 'hover'; champion_id: string | null }
  | { type: 'confirm'; champion_id: string }
  | { type: 'next_game' }
  | { type: 'ping' }

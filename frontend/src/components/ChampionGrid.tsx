import { useMemo, useState } from 'react'
import { portraitUrl } from '../lib/ddragon'
import { LANE_LABELS, LANE_ORDER } from '../lib/championLanes'
import type { Champion } from '../lib/ddragon'
import type { DraftState, Lane } from '../lib/types'

interface Props {
  champions: Champion[]
  version: string
  state: DraftState
  canAct: boolean
  lanesById: Map<string, Lane[]>
  onHover: (championId: string) => void
  onConfirm: (championId: string) => void
}

function normalize(text: string): string {
  return text
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
}

export default function ChampionGrid({
  champions,
  version,
  state,
  canAct,
  lanesById,
  onHover,
  onConfirm,
}: Props) {
  const [search, setSearch] = useState('')
  const [lane, setLane] = useState<Lane | ''>('')

  const banned = useMemo(() => {
    const set = new Set<string>()
    for (const list of [state.bans.blue, state.bans.red])
      for (const c of list) if (c) set.add(c)
    return set
  }, [state.bans])

  const picked = useMemo(
    () => new Set([...state.picks.blue, ...state.picks.red]),
    [state.picks],
  )
  const blocked = useMemo(
    () => new Set(state.fearless_blocked),
    [state.fearless_blocked],
  )

  const visible = useMemo(() => {
    const query = normalize(search.trim())
    return champions.filter((champion) => {
      if (lane) {
        // No lane data (e.g. a brand-new champion) matches every lane, so it is
        // never wrongly hidden.
        const lanes = lanesById.get(champion.id)
        if (lanes && lanes.length && !lanes.includes(lane)) return false
      }
      if (!query) return true
      // Match both the Spanish display name and the English id.
      return (
        normalize(champion.name).includes(query) ||
        normalize(champion.id).includes(query)
      )
    })
  }, [champions, search, lane, lanesById])

  return (
    <div className="champion-browser">
      <div className="champion-filters">
        <input
          type="search"
          placeholder="Buscar campeón…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="Buscar campeón"
        />
        <div className="lane-filters" role="group" aria-label="Filtrar por línea">
          <button
            className={lane === '' ? 'lane-btn lane-btn--on' : 'lane-btn'}
            onClick={() => setLane('')}
          >
            Todas
          </button>
          {LANE_ORDER.map((key) => (
            <button
              key={key}
              className={lane === key ? 'lane-btn lane-btn--on' : 'lane-btn'}
              onClick={() => setLane(lane === key ? '' : key)}
            >
              {LANE_LABELS[key]}
            </button>
          ))}
        </div>
      </div>

      <div className="champion-grid" role="listbox" aria-label="Campeones">
        {visible.map((champion) => {
          const isBanned = banned.has(champion.id)
          const isPicked = picked.has(champion.id)
          const isBlocked = blocked.has(champion.id)
          const isHovered = state.hovered === champion.id
          const selectable = canAct && !isBanned && !isPicked && !isBlocked
          const classes = [
            'champion-card',
            isBanned && 'champion-card--banned',
            isPicked && 'champion-card--picked',
            isBlocked && 'champion-card--blocked',
            isHovered && 'champion-card--hovered',
            selectable && 'champion-card--selectable',
          ]
            .filter(Boolean)
            .join(' ')
          const blockedTitle = isBlocked
            ? ' (bloqueado por Fearless)'
            : isBanned
              ? ' (baneado)'
              : isPicked
                ? ' (elegido)'
                : ''
          return (
            <button
              key={champion.id}
              className={classes}
              disabled={!selectable}
              title={champion.name + blockedTitle}
              onClick={() => selectable && onHover(champion.id)}
              onDoubleClick={() => selectable && onConfirm(champion.id)}
            >
              <img
                src={portraitUrl(version, champion.id)}
                alt={champion.name}
                loading="lazy"
              />
              {isBlocked && <span className="champion-lock">🔒</span>}
              <span className="champion-name">{champion.name}</span>
            </button>
          )
        })}
        {visible.length === 0 && (
          <p className="grid-empty">Ningún campeón coincide con la búsqueda.</p>
        )}
      </div>
    </div>
  )
}

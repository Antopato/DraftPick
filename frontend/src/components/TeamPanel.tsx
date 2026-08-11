import { portraitUrl, splashUrl } from '../lib/ddragon'
import type { Champion } from '../lib/ddragon'
import type { DraftState, TeamSide } from '../lib/types'

interface Props {
  side: TeamSide
  state: DraftState
  version: string
  championsById: Map<string, Champion>
}

const PICK_SLOTS = 5
const BAN_SLOTS = 5

export default function TeamPanel({ side, state, version, championsById }: Props) {
  const name = side === 'blue' ? state.room.blue_name : state.room.red_name
  const picks = state.picks[side]
  const bans = state.bans[side]
  const turn = state.current_turn
  const isActingSide = turn?.team === side

  const activePickIndex =
    isActingSide && turn?.action_type === 'pick' ? picks.length : -1
  const activeBanIndex =
    isActingSide && turn?.action_type === 'ban' ? bans.length : -1

  const nameOf = (id: string) => championsById.get(id)?.name ?? id

  return (
    <aside className={`team-panel team-panel--${side}`}>
      <div className="team-panel__header">
        <span className={`team-dot${state.connected[side] ? ' team-dot--on' : ''}`} />
        <h2>{name}</h2>
        {state.your_role === side && <span className="team-you">(tú)</span>}
      </div>

      <div className="ban-row">
        {Array.from({ length: BAN_SLOTS }, (_, i) => {
          const ban = bans[i]
          const isActive = i === activeBanIndex
          const showHover = isActive && state.hovered
          return (
            <div
              key={i}
              className={`ban-slot${isActive ? ' slot--active' : ''}`}
              title={ban ? `Baneado: ${nameOf(ban)}` : undefined}
            >
              {ban ? (
                <img src={portraitUrl(version, ban)} alt={nameOf(ban)} />
              ) : showHover ? (
                <img
                  className="slot-hovered-img"
                  src={portraitUrl(version, state.hovered!)}
                  alt={nameOf(state.hovered!)}
                />
              ) : i < bans.length ? (
                <span className="ban-skipped" title="Ban saltado">–</span>
              ) : null}
              {ban && <span className="ban-cross">✕</span>}
            </div>
          )
        })}
      </div>

      <ol className="pick-list">
        {Array.from({ length: PICK_SLOTS }, (_, i) => {
          const pick = picks[i]
          const isActive = i === activePickIndex
          const showHover = isActive && state.hovered
          return (
            <li key={i} className={`pick-slot${isActive ? ' slot--active' : ''}`}>
              {pick ? (
                <>
                  <img src={splashUrl(pick)} alt={nameOf(pick)} />
                  <span className="pick-name">{nameOf(pick)}</span>
                </>
              ) : showHover ? (
                <>
                  <img
                    className="slot-hovered-img"
                    src={splashUrl(state.hovered!)}
                    alt={nameOf(state.hovered!)}
                  />
                  <span className="pick-name pick-name--hovered">
                    {nameOf(state.hovered!)}
                  </span>
                </>
              ) : (
                <>
                  <span className="pick-placeholder">?</span>
                  <span className="pick-name pick-name--empty">Pick {i + 1}</span>
                </>
              )}
            </li>
          )
        })}
      </ol>
    </aside>
  )
}

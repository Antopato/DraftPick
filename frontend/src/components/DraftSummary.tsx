import { portraitUrl } from '../lib/ddragon'
import { LANE_LABELS, LANE_ORDER } from '../lib/championLanes'
import type { Champion } from '../lib/ddragon'
import type { DraftState, Lane, TeamSide } from '../lib/types'

interface Props {
  state: DraftState
  version: string
  championsById: Map<string, Champion>
  onNextGame: () => void
  onAssignLane: (pickIndex: number, lane: Lane) => void
}

export default function DraftSummary({
  state,
  version,
  championsById,
  onNextGame,
  onAssignLane,
}: Props) {
  const isCaptain = state.your_role === 'blue' || state.your_role === 'red'
  const seriesOver = state.status === 'series_completed'
  const nameOf = (id: string) => championsById.get(id)?.name ?? id

  const renderTeam = (side: TeamSide) => {
    const canEdit = state.your_role === side // only that team's captain assigns
    return (
      <div className={`summary-team summary-team--${side}`}>
        <h3>{side === 'blue' ? state.room.blue_name : state.room.red_name}</h3>
        <ul className="summary-picks">
          {state.picks[side].map((championId, i) => {
            const lane = state.lanes[side]?.[i] ?? null
            return (
              <li key={championId} className="summary-pick">
                <img
                  src={portraitUrl(version, championId)}
                  alt={nameOf(championId)}
                />
                <span className="summary-pick-name">{nameOf(championId)}</span>
                <div className="lane-picker" role="group" aria-label="Línea">
                  {LANE_ORDER.map((key) => {
                    const on = lane === key
                    const cls = on ? 'lane-chip lane-chip--on' : 'lane-chip'
                    return canEdit ? (
                      <button
                        key={key}
                        className={cls}
                        aria-pressed={on}
                        title={LANE_LABELS[key]}
                        onClick={() => onAssignLane(i, key)}
                      >
                        {LANE_LABELS[key]}
                      </button>
                    ) : (
                      // Read-only: opponent / spectator only see the choice.
                      on && (
                        <span key={key} className="lane-chip lane-chip--on">
                          {LANE_LABELS[key]}
                        </span>
                      )
                    )
                  })}
                </div>
              </li>
            )
          })}
        </ul>
        <div className="summary-bans">
          <span>Bans:</span>
          {state.bans[side].map((championId, i) =>
            championId ? (
              <img
                key={i}
                src={portraitUrl(version, championId)}
                alt={nameOf(championId)}
                title={nameOf(championId)}
              />
            ) : (
              <span key={i} className="ban-skipped" title="Ban saltado">
                –
              </span>
            ),
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="summary">
      <h2>
        {seriesOver && state.room.best_of > 1
          ? `Serie completada (${state.room.best_of} partidas)`
          : `Draft completado — Partida ${state.game_number}`}
      </h2>
      <div className="summary-teams">
        {renderTeam('blue')}
        {renderTeam('red')}
      </div>
      {!seriesOver && (
        <div className="summary-actions">
          {isCaptain ? (
            <button className="confirm-btn" onClick={onNextGame}>
              Siguiente partida ({state.game_number + 1} de {state.room.best_of})
            </button>
          ) : (
            <p>Esperando a que los capitanes inicien la siguiente partida…</p>
          )}
        </div>
      )}
    </div>
  )
}

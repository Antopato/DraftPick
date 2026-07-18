import { portraitUrl, splashUrl } from '../lib/ddragon'
import type { Champion } from '../lib/ddragon'
import type { DraftState, TeamSide } from '../lib/types'

interface Props {
  state: DraftState
  version: string
  championsById: Map<string, Champion>
  onNextGame: () => void
}

export default function DraftSummary({
  state,
  version,
  championsById,
  onNextGame,
}: Props) {
  const isCaptain = state.your_role === 'blue' || state.your_role === 'red'
  const seriesOver = state.status === 'series_completed'
  const nameOf = (id: string) => championsById.get(id)?.name ?? id

  const renderTeam = (side: TeamSide) => (
    <div className={`summary-team summary-team--${side}`}>
      <h3>{side === 'blue' ? state.room.blue_name : state.room.red_name}</h3>
      <div className="summary-picks">
        {state.picks[side].map((championId) => (
          <figure key={championId} className="summary-pick">
            <img src={splashUrl(championId)} alt={nameOf(championId)} />
            <figcaption>{nameOf(championId)}</figcaption>
          </figure>
        ))}
      </div>
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

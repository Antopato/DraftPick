import { portraitUrl } from '../../lib/ddragon'
import { LANE_LABELS } from '../../lib/championLanes'
import { CONFIDENCE_LABELS } from './labels'
import type { Champion } from '../../lib/ddragon'
import type { AnalysisPayload } from '../../lib/analysis'

interface Props {
  matchups: AnalysisPayload['lane_matchups']
  version: string
  championsById: Map<string, Champion>
}

export default function LaneMatchupTable({
  matchups,
  version,
  championsById,
}: Props) {
  const nameOf = (id: string) => championsById.get(id)?.name ?? id

  if (!matchups.available) {
    return (
      <p className="analysis-unavailable">
        Los winrates de matchups no están disponibles ahora mismo.
      </p>
    )
  }

  return (
    <div className="matchup-table">
      {matchups.stale && (
        <p className="analysis-stale">
          Datos del parche {matchups.snapshot_patch?.replace('_', '.')} (no hay
          datos del parche actual todavía).
        </p>
      )}
      {matchups.rows.map((row) => {
        const wr = row.winrate_blue
        return (
          <div key={row.lane} className="matchup-row">
            <span className="matchup-lane">
              {LANE_LABELS[row.lane]}
              {row.inferred && (
                <span
                  className="matchup-inferred"
                  title="Línea inferida automáticamente (no asignada por los capitanes)"
                >
                  (inferida)
                </span>
              )}
            </span>
            <img src={portraitUrl(version, row.blue_champion)} alt={nameOf(row.blue_champion)} title={nameOf(row.blue_champion)} />
            {wr !== null ? (
              <div className="matchup-bar" title={`${row.games} partidas analizadas`}>
                <div className="matchup-bar-blue" style={{ width: `${wr}%` }} />
                <span className="matchup-bar-label">
                  {wr.toFixed(1)}% – {(100 - wr).toFixed(1)}%
                </span>
              </div>
            ) : (
              <div className="matchup-bar matchup-bar--empty">
                <span className="matchup-bar-label">Sin datos</span>
              </div>
            )}
            <img src={portraitUrl(version, row.red_champion)} alt={nameOf(row.red_champion)} title={nameOf(row.red_champion)} />
            <span className={`confidence-chip confidence-chip--${row.confidence}`}>
              {CONFIDENCE_LABELS[row.confidence]}
              {wr !== null && ` · n=${row.games.toLocaleString('es-ES')}`}
            </span>
          </div>
        )
      })}
      <p className="analysis-footnote">
        Winrate 1c1 en línea (soloQ, muestras pequeñas suavizadas hacia el 50 %).
      </p>
    </div>
  )
}

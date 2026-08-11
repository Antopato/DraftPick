import { PHASE_LABELS, PHASE_ORDER } from './labels'
import type { AnalysisPayload } from '../../lib/analysis'
import type { Champion } from '../../lib/ddragon'

interface Props {
  phases: AnalysisPayload['phases']
  blueName: string
  redName: string
  championsById: Map<string, Champion>
}

export default function PhaseTimeline({
  phases,
  blueName,
  redName,
  championsById,
}: Props) {
  const nameOf = (id: string) => championsById.get(id)?.name ?? id
  const threshold = phases.advantage_threshold

  return (
    <div className="phase-timeline">
      <div className="phase-segments">
        {PHASE_ORDER.map((phase) => {
          const delta = phases.deltas[phase]
          const leader =
            delta >= threshold ? 'blue' : delta <= -threshold ? 'red' : null
          return (
            <div
              key={phase}
              className={`phase-segment${leader ? ` phase-segment--${leader}` : ''}`}
            >
              <span className="phase-name">{PHASE_LABELS[phase]}</span>
              <div className="phase-scores">
                <span className="phase-score phase-score--blue">
                  {phases.blue[phase]}
                </span>
                <span className="phase-score phase-score--red">
                  {phases.red[phase]}
                </span>
              </div>
              <span className="phase-verdict">
                {leader === 'blue'
                  ? `Ventaja ${blueName}`
                  : leader === 'red'
                    ? `Ventaja ${redName}`
                    : 'Igualado'}
              </span>
            </div>
          )
        })}
      </div>
      <details className="phase-breakdown">
        <summary>Ver curvas por campeón</summary>
        <table>
          <thead>
            <tr>
              <th>Campeón</th>
              {PHASE_ORDER.map((p) => (
                <th key={p}>{PHASE_LABELS[p]}</th>
              ))}
              <th>Fuente</th>
            </tr>
          </thead>
          <tbody>
            {phases.breakdown.map((row) => (
              <tr key={`${row.team}-${row.champion_id}`} className={`row--${row.team}`}>
                <td>{nameOf(row.champion_id)}</td>
                {PHASE_ORDER.map((p) => (
                  <td key={p}>{row.curve[p]}</td>
                ))}
                <td
                  title={
                    row.source === 'override'
                      ? 'Curva revisada manualmente'
                      : 'Estimada por clase e items'
                  }
                >
                  {row.source === 'override' ? 'curada' : 'estimada'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  )
}

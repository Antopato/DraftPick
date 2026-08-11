import type { AnalysisPayload } from '../../lib/analysis'

interface Props {
  verdict: AnalysisPayload['verdict']
  blueName: string
  redName: string
}

const COMPONENT_LABELS: Record<string, string> = {
  lanes: 'Matchups por línea',
  composition: 'Composición',
  phases: 'Fases de partida',
}

export default function VerdictCard({ verdict, blueName, redName }: Props) {
  const teamName = verdict.favors === 'blue' ? blueName : redName
  const headline =
    verdict.tier === 'even'
      ? 'Draft igualado'
      : verdict.tier === 'slight'
        ? `Ligera ventaja para ${teamName}`
        : `Ventaja clara para ${teamName}`

  return (
    <div
      className={`verdict-card${
        verdict.favors ? ` verdict-card--${verdict.favors}` : ''
      }`}
    >
      <h3>{headline}</h3>
      <table className="verdict-components">
        <tbody>
          {Object.entries(verdict.components).map(([key, value]) => (
            <tr key={key}>
              <td>{COMPONENT_LABELS[key] ?? key}</td>
              <td
                className={
                  value > 0 ? 'delta--blue' : value < 0 ? 'delta--red' : ''
                }
              >
                {value > 0 ? '+' : ''}
                {value.toFixed(1)}
              </td>
              <td className="verdict-weight">
                peso {Math.round((verdict.weights[key as keyof typeof verdict.weights] ?? 0) * 100)}%
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="verdict-note">
        Valores positivos favorecen al equipo azul; negativos, al rojo.
      </p>
    </div>
  )
}

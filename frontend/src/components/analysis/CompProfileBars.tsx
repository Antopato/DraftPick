import { ARCHETYPE_LABELS, DAMAGE_WARNINGS, METRIC_LABELS } from './labels'
import type { AnalysisPayload, TeamCompositionData } from '../../lib/analysis'
import type { Champion } from '../../lib/ddragon'

interface Props {
  compositions: AnalysisPayload['compositions']
  blueName: string
  redName: string
  championsById: Map<string, Champion>
}

const METRICS = ['engage', 'poke', 'peel', 'frontline', 'cc'] as const

function archetypeText(comp: TeamCompositionData): string {
  const primary = ARCHETYPE_LABELS[comp.archetype_primary]
  return comp.archetype_secondary
    ? `${primary} + ${ARCHETYPE_LABELS[comp.archetype_secondary]}`
    : primary
}

function damageText(comp: TeamCompositionData): string {
  const parts: string[] = []
  if (comp.damage_mix.physical) parts.push(`${comp.damage_mix.physical} físico`)
  if (comp.damage_mix.magic) parts.push(`${comp.damage_mix.magic} mágico`)
  if (comp.damage_mix.mixed) parts.push(`${comp.damage_mix.mixed} mixto`)
  return parts.join(' · ') || 'Sin datos'
}

export default function CompProfileBars({
  compositions,
  blueName,
  redName,
  championsById,
}: Props) {
  const nameOf = (id: string) => championsById.get(id)?.name ?? id

  if (!compositions.available) {
    return (
      <p className="analysis-unavailable">
        Los perfiles de composición no están disponibles ahora mismo.
      </p>
    )
  }
  const { blue, red } = compositions

  return (
    <div className="comp-profile">
      <div className="comp-archetypes">
        <span className="comp-badge comp-badge--blue" title={blueName}>
          {archetypeText(blue)}
        </span>
        <span className="comp-vs">vs</span>
        <span className="comp-badge comp-badge--red" title={redName}>
          {archetypeText(red)}
        </span>
      </div>

      {METRICS.map((metric) => (
        <div key={metric} className="comp-metric">
          <span className="comp-metric-value">{blue.scores[metric]}</span>
          <div className="comp-metric-bars">
            <div className="comp-metric-bar comp-metric-bar--blue">
              <div style={{ width: `${blue.scores[metric]}%` }} />
            </div>
            <span className="comp-metric-name">{METRIC_LABELS[metric]}</span>
            <div className="comp-metric-bar comp-metric-bar--red">
              <div style={{ width: `${red.scores[metric]}%` }} />
            </div>
          </div>
          <span className="comp-metric-value">{red.scores[metric]}</span>
        </div>
      ))}

      <div className="comp-facts">
        <span>
          {blue.ranged_count} a distancia · daño: {damageText(blue)}
        </span>
        <span>
          {red.ranged_count} a distancia · daño: {damageText(red)}
        </span>
      </div>
      {(blue.damage_warning || red.damage_warning) && (
        <div className="comp-warnings">
          {blue.damage_warning && (
            <p className="comp-warning comp-warning--blue">
              {blueName}: {DAMAGE_WARNINGS[blue.damage_warning]}
            </p>
          )}
          {red.damage_warning && (
            <p className="comp-warning comp-warning--red">
              {redName}: {DAMAGE_WARNINGS[red.damage_warning]}
            </p>
          )}
        </div>
      )}
      {(blue.partial || red.partial) && (
        <p className="analysis-footnote">
          Faltan datos de algún campeón; los valores se calculan con los
          disponibles.
        </p>
      )}

      <details className="comp-breakdown">
        <summary>Ver desglose por campeón</summary>
        <table>
          <thead>
            <tr>
              <th>Campeón</th>
              {METRICS.map((m) => (
                <th key={m}>{METRIC_LABELS[m]}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {[...blue.breakdown, ...red.breakdown].map((row, i) => (
              <tr key={row.champion_id} className={i < 5 ? 'row--blue' : 'row--red'}>
                <td>{nameOf(row.champion_id)}</td>
                {METRICS.map((m) => (
                  <td key={m}>{row.missing ? '—' : (row[m] ?? 0).toFixed(1)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  )
}

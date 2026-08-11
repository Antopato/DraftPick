import { useEffect, useRef, useState } from 'react'
import { fetchAnalysis } from '../../lib/analysis'
import CompProfileBars from './CompProfileBars'
import LaneMatchupTable from './LaneMatchupTable'
import PhaseTimeline from './PhaseTimeline'
import VerdictCard from './VerdictCard'
import type { AnalysisPayload } from '../../lib/analysis'
import type { Champion } from '../../lib/ddragon'
import type { DraftState } from '../../lib/types'

interface Props {
  state: DraftState
  token: string
  version: string
  championsById: Map<string, Champion>
}

export default function AnalysisPanel({
  state,
  token,
  version,
  championsById,
}: Props) {
  const [analysis, setAnalysis] = useState<AnalysisPayload | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [retryKey, setRetryKey] = useState(0)
  const debounceRef = useRef<number>()

  // Lane reassignments arrive via the WS full-state broadcast; refetch (with a
  // debounce so clicking through the lane chips doesn't hammer the endpoint).
  const lanesKey = JSON.stringify(state.lanes)

  useEffect(() => {
    let cancelled = false
    window.clearTimeout(debounceRef.current)
    debounceRef.current = window.setTimeout(() => {
      setLoading(true)
      setError(null)
      fetchAnalysis(token, state.game_number)
        .then((payload) => {
          if (!cancelled) setAnalysis(payload)
        })
        .catch((err: Error) => {
          if (!cancelled) setError(err.message)
        })
        .finally(() => {
          if (!cancelled) setLoading(false)
        })
    }, 800)
    return () => {
      cancelled = true
      window.clearTimeout(debounceRef.current)
    }
  }, [token, state.game_number, lanesKey, retryKey])

  const blueName = state.room.blue_name
  const redName = state.room.red_name

  return (
    <section className="analysis-panel">
      <h2>Análisis del draft</h2>

      {loading && !analysis && (
        <p className="analysis-loading">Calculando análisis…</p>
      )}
      {error && (
        <div className="analysis-error">
          <p>{error}</p>
          <button className="confirm-btn" onClick={() => setRetryKey((k) => k + 1)}>
            Reintentar
          </button>
        </div>
      )}

      {analysis && (
        <div className={loading ? 'analysis-body analysis-body--refreshing' : 'analysis-body'}>
          <VerdictCard
            verdict={analysis.verdict}
            blueName={blueName}
            redName={redName}
          />
          {analysis.lanes_inferred && (
            <p className="analysis-stale">
              Hay líneas sin asignar: se han inferido automáticamente. Asignadlas
              en el resumen para afinar el análisis.
            </p>
          )}

          <h3>Matchups por línea</h3>
          <LaneMatchupTable
            matchups={analysis.lane_matchups}
            version={version}
            championsById={championsById}
          />

          <h3>Perfil de composición</h3>
          <CompProfileBars
            compositions={analysis.compositions}
            blueName={blueName}
            redName={redName}
            championsById={championsById}
          />

          <h3>Fases de partida</h3>
          <PhaseTimeline
            phases={analysis.phases}
            blueName={blueName}
            redName={redName}
            championsById={championsById}
          />

          <p className="analysis-footnote">
            Parche {analysis.patch}. Análisis automático orientativo: datos de
            soloQ y perfiles de campeón, no sustituye el criterio del equipo.
          </p>
        </div>
      )}
    </section>
  )
}

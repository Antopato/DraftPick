import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import ChampionGrid from '../components/ChampionGrid'
import DraftSummary from '../components/DraftSummary'
import ReadyOverlay from '../components/ReadyOverlay'
import TeamPanel from '../components/TeamPanel'
import TurnBanner from '../components/TurnBanner'
import TurnTimer from '../components/TurnTimer'
import { useDraftSocket } from '../hooks/useDraftSocket'
import { loadChampions } from '../lib/ddragon'
import { loadChampionLanes } from '../lib/championLanes'
import type { ChampionData } from '../lib/ddragon'
import type { Lane } from '../lib/types'

export default function DraftRoomPage() {
  const { token } = useParams<{ token: string }>()
  const { state, connectionStatus, lastError, send } = useDraftSocket(token ?? '')
  const [championData, setChampionData] = useState<ChampionData | null>(null)
  const [championError, setChampionError] = useState(false)
  const [lanesById, setLanesById] = useState<Map<string, Lane[]>>(new Map())

  useEffect(() => {
    let cancelled = false
    loadChampions()
      .then((data) => {
        if (!cancelled) setChampionData(data)
      })
      .catch(() => {
        if (!cancelled) setChampionError(true)
      })
    // Lane data is best-effort: on failure the filter simply shows every lane.
    loadChampionLanes()
      .then((lanes) => {
        if (!cancelled) setLanesById(lanes)
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [])

  const championsById = useMemo(
    () => new Map((championData?.champions ?? []).map((c) => [c.id, c])),
    [championData],
  )

  if (connectionStatus === 'not_found') {
    return (
      <main className="center-message">
        <h1>Sala no encontrada</h1>
        <p>El enlace no es válido o la sala ya no existe.</p>
      </main>
    )
  }

  if (championError) {
    return (
      <main className="center-message">
        <h1>Error</h1>
        <p>
          No se ha podido cargar la lista de campeones de Data Dragon. Revisa tu
          conexión y recarga la página.
        </p>
      </main>
    )
  }

  if (!state || !championData) {
    return (
      <main className="center-message">
        <h1>DraftPick</h1>
        <p>
          {connectionStatus === 'waking'
            ? 'El servidor se está despertando, puede tardar hasta un minuto…'
            : 'Conectando con la sala…'}
        </p>
      </main>
    )
  }

  const role = state.your_role
  const isCaptain = role === 'blue' || role === 'red'
  const myTurn =
    isCaptain &&
    state.status === 'in_progress' &&
    state.current_turn?.team === role
  const draftOver =
    state.status === 'completed' || state.status === 'series_completed'

  return (
    <div className="draft-page">
      <header className="draft-header">
        <span className="header-side header-side--blue">
          {state.room.blue_name}
        </span>
        <div className="header-center">
          <TurnTimer deadline={state.deadline} serverNow={state.server_now} />
          <span className="header-game">
            Partida {state.game_number}
            {state.room.mode === 'fearless' && ` / ${state.room.best_of}`}
            {role === 'spectator' && ' · Espectador'}
          </span>
        </div>
        <span className="header-side header-side--red">{state.room.red_name}</span>
      </header>

      <div className="draft-main">
        <TeamPanel
          side="blue"
          state={state}
          version={championData.version}
          championsById={championsById}
        />
        <section className="draft-center">
          {draftOver ? (
            <DraftSummary
              state={state}
              token={token ?? ''}
              version={championData.version}
              championsById={championsById}
              onNextGame={() => send({ type: 'next_game' })}
              onAssignLane={(pickIndex, lane) =>
                send({ type: 'assign_lane', pick_index: pickIndex, lane })
              }
            />
          ) : (
            <ChampionGrid
              champions={championData.champions}
              version={championData.version}
              state={state}
              canAct={myTurn}
              lanesById={lanesById}
              onHover={(championId) => send({ type: 'hover', champion_id: championId })}
              onConfirm={(championId) =>
                send({ type: 'confirm', champion_id: championId })
              }
            />
          )}
        </section>
        <TeamPanel
          side="red"
          state={state}
          version={championData.version}
          championsById={championsById}
        />
      </div>

      <TurnBanner
        state={state}
        myTurn={myTurn}
        onConfirm={() =>
          state.hovered && send({ type: 'confirm', champion_id: state.hovered })
        }
      />

      <ReadyOverlay state={state} onReady={() => send({ type: 'ready' })} />

      {(connectionStatus === 'reconnecting' || connectionStatus === 'waking') && (
        <div className="conn-banner">
          {connectionStatus === 'waking'
            ? 'El servidor se está despertando, puede tardar hasta un minuto…'
            : 'Conexión perdida. Reconectando…'}
        </div>
      )}
      {lastError && <div className="toast">{lastError}</div>}
    </div>
  )
}

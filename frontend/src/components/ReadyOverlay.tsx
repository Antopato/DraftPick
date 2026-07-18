import type { DraftState } from '../lib/types'

interface Props {
  state: DraftState
  onReady: () => void
}

export default function ReadyOverlay({ state, onReady }: Props) {
  if (state.status !== 'waiting') return null

  const role = state.your_role
  const isCaptain = role === 'blue' || role === 'red'
  const iAmReady = isCaptain && state.ready[role]

  return (
    <div className="overlay">
      <div className="overlay__card">
        <h2>
          Partida {state.game_number}
          {state.room.mode === 'fearless' &&
            ` de ${state.room.best_of} · Modo Fearless`}
        </h2>
        {state.fearless_blocked.length > 0 && (
          <p className="overlay__note">
            {state.fearless_blocked.length} campeones bloqueados de partidas
            anteriores.
          </p>
        )}
        <div className="ready-status">
          <div className={state.ready.blue ? 'ready ready--ok' : 'ready'}>
            {state.room.blue_name}: {state.ready.blue ? '¡Listo!' : 'Esperando…'}
          </div>
          <div className={state.ready.red ? 'ready ready--ok' : 'ready'}>
            {state.room.red_name}: {state.ready.red ? '¡Listo!' : 'Esperando…'}
          </div>
        </div>
        {isCaptain ? (
          <button className="confirm-btn" disabled={iAmReady} onClick={onReady}>
            {iAmReady ? 'Esperando al otro capitán…' : '¡Listo!'}
          </button>
        ) : (
          <p className="overlay__note">
            El draft comenzará cuando ambos capitanes estén listos.
          </p>
        )}
      </div>
    </div>
  )
}

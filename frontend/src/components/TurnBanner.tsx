import type { DraftState } from '../lib/types'

interface Props {
  state: DraftState
  myTurn: boolean
  onConfirm: () => void
}

export default function TurnBanner({ state, myTurn, onConfirm }: Props) {
  if (state.status !== 'in_progress' || !state.current_turn) return null

  const { team, action_type, slot } = state.current_turn
  const teamName = team === 'blue' ? state.room.blue_name : state.room.red_name
  const actionLabel = action_type === 'ban' ? 'BAN' : 'PICK'

  return (
    <footer className={`turn-banner turn-banner--${team}`}>
      <span className="turn-banner__text">
        ≫ TURNO ACTUAL: <strong>{teamName.toUpperCase()}</strong> — {actionLabel}{' '}
        {slot} ≪
      </span>
      {myTurn && (
        <button
          className="confirm-btn"
          disabled={!state.hovered}
          onClick={onConfirm}
        >
          {state.hovered
            ? `Confirmar ${actionLabel.toLowerCase()}`
            : 'Selecciona un campeón'}
        </button>
      )}
    </footer>
  )
}

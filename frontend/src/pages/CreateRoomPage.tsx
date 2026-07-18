import { useState } from 'react'
import type { FormEvent } from 'react'
import { createRoom } from '../lib/api'
import type { RoomLinks } from '../lib/types'

interface LinkRow {
  label: string
  token: string
}

function CopyableLink({ label, token }: LinkRow) {
  const [copied, setCopied] = useState(false)
  const url = `${window.location.origin}/room/${token}`

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(url)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // clipboard unavailable (http, permissions): user can copy manually
    }
  }

  return (
    <div className="link-row">
      <span className="link-label">{label}</span>
      <input readOnly value={url} onFocus={(e) => e.target.select()} />
      <button type="button" onClick={copy}>
        {copied ? '¡Copiado!' : 'Copiar'}
      </button>
    </div>
  )
}

export default function CreateRoomPage() {
  const [mode, setMode] = useState<'standard' | 'fearless'>('standard')
  const [bestOf, setBestOf] = useState(3)
  const [timerSeconds, setTimerSeconds] = useState(30)
  const [blueName, setBlueName] = useState('')
  const [redName, setRedName] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [links, setLinks] = useState<RoomLinks | null>(null)

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      const result = await createRoom({
        mode,
        best_of: mode === 'fearless' ? bestOf : 1,
        timer_seconds: timerSeconds,
        blue_name: blueName.trim() || undefined,
        red_name: redName.trim() || undefined,
      })
      setLinks(result)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'No se ha podido crear la sala. Inténtalo de nuevo.',
      )
    } finally {
      setSubmitting(false)
    }
  }

  if (links) {
    return (
      <main className="create-page">
        <h1>DraftPick</h1>
        <section className="card">
          <h2>Sala creada</h2>
          <p>
            Comparte cada enlace con su destinatario. El rol depende del enlace:
            no los mezcles.
          </p>
          <CopyableLink label="Capitán equipo azul" token={links.blue_token} />
          <CopyableLink label="Capitán equipo rojo" token={links.red_token} />
          <CopyableLink label="Espectador" token={links.spectator_token} />
          <button type="button" className="link-again" onClick={() => setLinks(null)}>
            Crear otra sala
          </button>
        </section>
      </main>
    )
  }

  return (
    <main className="create-page">
      <h1>DraftPick</h1>
      <p className="tagline">
        Draft de League of Legends por turnos, en tiempo real.
      </p>
      <form className="card" onSubmit={submit}>
        <h2>Crear sala de draft</h2>

        <fieldset>
          <legend>Modo</legend>
          <label>
            <input
              type="radio"
              name="mode"
              checked={mode === 'standard'}
              onChange={() => setMode('standard')}
            />
            Estándar (una partida)
          </label>
          <label>
            <input
              type="radio"
              name="mode"
              checked={mode === 'fearless'}
              onChange={() => setMode('fearless')}
            />
            Fearless (serie: los campeones elegidos quedan bloqueados en las
            siguientes partidas)
          </label>
        </fieldset>

        {mode === 'fearless' && (
          <label className="field">
            Partidas de la serie
            <select
              value={bestOf}
              onChange={(e) => setBestOf(Number(e.target.value))}
            >
              <option value={1}>Bo1 (1 partida)</option>
              <option value={3}>Bo3 (3 partidas)</option>
              <option value={5}>Bo5 (5 partidas)</option>
            </select>
          </label>
        )}

        <label className="field">
          Segundos por turno
          <input
            type="number"
            min={5}
            max={180}
            value={timerSeconds}
            onChange={(e) => setTimerSeconds(Number(e.target.value))}
          />
        </label>

        <label className="field">
          Nombre del equipo azul (opcional)
          <input
            type="text"
            maxLength={40}
            placeholder="Equipo Azul"
            value={blueName}
            onChange={(e) => setBlueName(e.target.value)}
          />
        </label>

        <label className="field">
          Nombre del equipo rojo (opcional)
          <input
            type="text"
            maxLength={40}
            placeholder="Equipo Rojo"
            value={redName}
            onChange={(e) => setRedName(e.target.value)}
          />
        </label>

        {error && <p className="form-error">{error}</p>}

        <button className="confirm-btn" type="submit" disabled={submitting}>
          {submitting ? 'Creando sala…' : 'Crear sala'}
        </button>
      </form>
    </main>
  )
}

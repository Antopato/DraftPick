// es-ES labels for the language-neutral analysis API codes.

import type { Archetype, Confidence, PhaseKey } from '../../lib/analysis'

export const ARCHETYPE_LABELS: Record<Archetype, string> = {
  engage: 'Iniciación',
  poke: 'Poke / Asedio',
  peel: 'Protección / Kite',
  flexible: 'Flexible',
}

export const METRIC_LABELS: Record<string, string> = {
  engage: 'Iniciación',
  poke: 'Poke',
  peel: 'Protección',
  frontline: 'Vanguardia',
  cc: 'Control de masas',
}

export const CONFIDENCE_LABELS: Record<Confidence, string> = {
  alta: 'Confianza alta',
  media: 'Confianza media',
  baja: 'Confianza baja',
  sin_datos: 'Sin datos',
}

export const PHASE_LABELS: Record<PhaseKey, string> = {
  pre15: 'Antes del min 15',
  '15to25': 'Min 15–25',
  post30: 'A partir del min 30',
}

export const PHASE_ORDER: PhaseKey[] = ['pre15', '15to25', 'post30']

export const DAMAGE_WARNINGS: Record<string, string> = {
  mostly_physical: 'Casi todo el daño es físico: fácil de itemizar en contra.',
  mostly_magic: 'Casi todo el daño es mágico: fácil de itemizar en contra.',
}

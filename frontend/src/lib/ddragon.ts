// Riot Data Dragon: static CDN, no API key. Champion names come localized
// (es_ES); ids stay English and match what the backend validates against.

export interface Champion {
  id: string
  name: string
  tags: string[]
}

export interface ChampionData {
  version: string
  champions: Champion[]
}

const VERSIONS_URL = 'https://ddragon.leagueoflegends.com/api/versions.json'
const CACHE_KEY = 'draftpick-ddragon-v1'
const CACHE_TTL_MS = 6 * 3600 * 1000

interface CachedData extends ChampionData {
  savedAt: number
}

function readCache(): CachedData | null {
  try {
    const raw = localStorage.getItem(CACHE_KEY)
    if (!raw) return null
    const data = JSON.parse(raw) as CachedData
    if (Date.now() - data.savedAt > CACHE_TTL_MS) return null
    return data
  } catch {
    return null
  }
}

export async function loadChampions(): Promise<ChampionData> {
  const cached = readCache()
  if (cached) return cached

  const versions = (await (await fetch(VERSIONS_URL)).json()) as string[]
  const version = versions[0]
  const listUrl = `https://ddragon.leagueoflegends.com/cdn/${version}/data/es_ES/champion.json`
  const list = (await (await fetch(listUrl)).json()) as {
    data: Record<string, { id: string; name: string; tags: string[] }>
  }
  const champions = Object.values(list.data)
    .map(({ id, name, tags }) => ({ id, name, tags }))
    .sort((a, b) => a.name.localeCompare(b.name, 'es'))

  const data: ChampionData = { version, champions }
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify({ ...data, savedAt: Date.now() }))
  } catch {
    // storage full/unavailable: fine, we just refetch next time
  }
  return data
}

export function portraitUrl(version: string, championId: string): string {
  return `https://ddragon.leagueoflegends.com/cdn/${version}/img/champion/${championId}.png`
}

export function splashUrl(championId: string): string {
  return `https://ddragon.leagueoflegends.com/cdn/img/champion/loading/${championId}_0.jpg`
}

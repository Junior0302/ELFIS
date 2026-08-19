/**
 * Recent Command Center queries — localStorage, max 5.
 * Filename avoids Windows clash with RecentSearches.tsx.
 */

const STORAGE_KEY = 'elfis_command_center_recent'
const MAX_RECENT = 5

/** In-memory fallback when localStorage is unavailable (some test runners). */
const memoryStore: { value: string[] } = { value: [] }

function readStore(): string[] {
  try {
    if (typeof localStorage !== 'undefined' && localStorage) {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (!raw) return []
      const parsed = JSON.parse(raw) as unknown
      if (!Array.isArray(parsed)) return []
      return parsed
        .filter((x): x is string => typeof x === 'string' && x.trim().length > 0)
        .map((x) => x.trim())
        .slice(0, MAX_RECENT)
    }
  } catch {
    /* fall through */
  }
  return [...memoryStore.value]
}

function writeStore(next: string[]): void {
  memoryStore.value = next
  try {
    if (typeof localStorage !== 'undefined' && localStorage) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
    }
  } catch {
    /* ignore quota / private mode */
  }
}

export function getRecentSearches(): string[] {
  return readStore()
}

export function pushRecentSearch(query: string): string[] {
  const q = query.trim()
  if (!q || q.startsWith('>')) return getRecentSearches()
  const next = [q, ...getRecentSearches().filter((x) => x.toLowerCase() !== q.toLowerCase())].slice(
    0,
    MAX_RECENT,
  )
  writeStore(next)
  return next
}

export function clearRecentSearches(): void {
  memoryStore.value = []
  try {
    if (typeof localStorage !== 'undefined' && localStorage) {
      localStorage.removeItem(STORAGE_KEY)
    }
  } catch {
    /* ignore */
  }
}

export const RECENT_SEARCHES_KEY = STORAGE_KEY

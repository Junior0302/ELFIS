export type ThemeMode = 'light' | 'dark'

const THEME_KEY = 'cp_theme'

export function getStoredTheme(): ThemeMode | null {
  try {
    const raw = localStorage.getItem(THEME_KEY)
    if (raw === 'dark' || raw === 'light') return raw
  } catch {
    /* ignore */
  }
  return null
}

export function resolveTheme(): ThemeMode {
  const stored = getStoredTheme()
  if (stored) return stored
  if (typeof window !== 'undefined' && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return 'dark'
  }
  return 'light'
}

export function applyTheme(mode: ThemeMode): void {
  document.documentElement.setAttribute('data-theme', mode)
  document.documentElement.style.colorScheme = mode
  try {
    localStorage.setItem(THEME_KEY, mode)
  } catch {
    /* ignore */
  }
}

export function initTheme(): ThemeMode {
  const mode = resolveTheme()
  applyTheme(mode)
  return mode
}

export function toggleTheme(): ThemeMode {
  const next: ThemeMode = resolveTheme() === 'dark' ? 'light' : 'dark'
  applyTheme(next)
  return next
}

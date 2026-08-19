/**
 * Feature flag Vague 1 — bascule progressive UI unifiée sans casse.
 * Défaut : activé. Opt-out : VITE_UNIFIED_PLATFORM_UI=false ou localStorage / override mémoire.
 */

export const UNIFIED_PLATFORM_UI_STORAGE_KEY = 'elfis.unifiedPlatformUi'
export const UNIFIED_PLATFORM_UI_ENV_KEY = 'VITE_UNIFIED_PLATFORM_UI'

/** Override process (tests / runtime) — prioritaire sur storage/env. */
let memoryOverride: boolean | null = null

function readEnvFlag(): boolean | null {
  try {
    const raw = (import.meta.env?.VITE_UNIFIED_PLATFORM_UI as string | undefined)?.trim().toLowerCase()
    if (raw === '0' || raw === 'false' || raw === 'off') return false
    if (raw === '1' || raw === 'true' || raw === 'on') return true
  } catch {
    /* SSR / hors Vite */
  }
  return null
}

function readStorageFlag(): boolean | null {
  if (typeof localStorage === 'undefined') return null
  try {
    const raw = localStorage.getItem(UNIFIED_PLATFORM_UI_STORAGE_KEY)
    if (raw === '0' || raw === 'false') return false
    if (raw === '1' || raw === 'true') return true
  } catch {
    /* quota / private */
  }
  return null
}

/** true = shell/tokens unifiés actifs (Vague 1 défaut). */
export function isUnifiedPlatformUiEnabled(): boolean {
  if (memoryOverride != null) return memoryOverride
  const fromStorage = readStorageFlag()
  if (fromStorage != null) return fromStorage
  const fromEnv = readEnvFlag()
  if (fromEnv != null) return fromEnv
  return true
}

export function setUnifiedPlatformUiEnabled(enabled: boolean): void {
  memoryOverride = enabled
  try {
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(UNIFIED_PLATFORM_UI_STORAGE_KEY, enabled ? '1' : '0')
    }
  } catch {
    /* ignore — mémoire suffit */
  }
}

/** Remet le flag au défaut (tests). */
export function resetUnifiedPlatformUiFlag(): void {
  memoryOverride = null
  try {
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem(UNIFIED_PLATFORM_UI_STORAGE_KEY)
    }
  } catch {
    /* ignore */
  }
}

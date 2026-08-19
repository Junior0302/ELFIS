/**
 * DEV-only theme diagnostics — never runs noise in production.
 */

import type { ProductId } from '../types'

type ChangeLog = {
  from: ProductId | string
  to: ProductId | string
  reason: string
  path: string
}

const recentChanges: { t: number; path: string }[] = []

export function logThemeChange(entry: ChangeLog): void {
  if (typeof import.meta === 'undefined' || !import.meta.env?.DEV) return
  // eslint-disable-next-line no-console
  console.info(
    `[ELFIS Theme]\nfrom=${entry.from}\nto=${entry.to}\nreason=${entry.reason}\npath=${entry.path}`,
  )
}

/** Detects >3 theme changes in 2s without a path change → oscillation. */
export function trackThemeOscillation(path: string): void {
  if (typeof import.meta === 'undefined' || !import.meta.env?.DEV) return
  const now = Date.now()
  recentChanges.push({ t: now, path })
  while (recentChanges.length && now - recentChanges[0].t > 2000) {
    recentChanges.shift()
  }
  if (recentChanges.length <= 3) return
  const paths = new Set(recentChanges.map((c) => c.path))
  if (paths.size === 1) {
    // eslint-disable-next-line no-console
    console.error(
      `[ELFIS Theme] Oscillation détectée: ${recentChanges.length} changements en <2s sans changement de route (${path}). Vérifier les writers concurrents.`,
    )
  }
}

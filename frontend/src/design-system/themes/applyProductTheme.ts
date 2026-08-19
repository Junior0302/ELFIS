/**
 * DOM theme applier — injects --pilot-* via style.setProperty.
 * Does not touch legacy :root vars (--forest, --mint, …).
 * Atomic: writes new values before removing obsolete keys (no green flash).
 */

import { PILOT_CSS_VAR_NAMES, THEME_DOM_ATTR } from './cssVariables'
import { themeToCssVariables, themeToDomAttributes } from './themeToCssVariables'
import type { ProductTheme } from './interfaces'

export type ThemeTarget = Pick<HTMLElement, 'style' | 'setAttribute' | 'removeAttribute'>

function getDefaultTarget(): ThemeTarget | null {
  if (typeof document === 'undefined') return null
  return document.documentElement
}

/** Removes only Pilot CSS variables previously managed by the Theme Engine. */
export function clearProductTheme(target?: ThemeTarget | null): void {
  const el = target === undefined ? getDefaultTarget() : target
  if (!el) return
  for (const name of PILOT_CSS_VAR_NAMES) {
    el.style.removeProperty(name)
  }
  el.removeAttribute(THEME_DOM_ATTR.product)
  el.removeAttribute(THEME_DOM_ATTR.theme)
  el.removeAttribute(THEME_DOM_ATTR.colorScheme)
}

/**
 * Applies product theme CSS variables and data attributes.
 * Returns a cleanup function. Safe when document is absent (SSR/tests).
 */
export function applyProductTheme(
  theme: ProductTheme,
  target?: ThemeTarget | null,
): () => void {
  const el = target === undefined ? getDefaultTarget() : target
  if (!el) {
    return () => undefined
  }

  const vars = themeToCssVariables(theme)
  const attrs = themeToDomAttributes(theme)
  const nextKeys = new Set(Object.keys(vars))

  // Write new values first (atomic) — never clear to :root green mid-flight.
  for (const [name, value] of Object.entries(vars)) {
    el.style.setProperty(name, value)
  }
  for (const name of PILOT_CSS_VAR_NAMES) {
    if (!nextKeys.has(name)) {
      el.style.removeProperty(name)
    }
  }

  el.setAttribute(THEME_DOM_ATTR.product, attrs['data-product'])
  el.setAttribute(THEME_DOM_ATTR.theme, attrs['data-theme'])
  el.setAttribute(THEME_DOM_ATTR.colorScheme, attrs['data-color-scheme'])

  return () => {
    /* Cleanup is a no-op for application root to avoid StrictMode flicker.
       Explicit clearProductTheme remains available for tests/sandbox. */
  }
}

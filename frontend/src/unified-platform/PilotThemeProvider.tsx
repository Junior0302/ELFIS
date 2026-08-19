/**
 * PilotThemeProvider — accents only (Core navy / Compta vert / Sales bleu).
 * Surfaces restent neutres plateforme ; délègue ProductThemeProvider si présent.
 */

import {
  createContext,
  useContext,
  useMemo,
  type CSSProperties,
  type ReactNode,
} from 'react'
import type { ProductId } from '../design-system'
import {
  resolvePilotTheme,
  type PilotAccentContract,
  type UnifiedPilotId,
} from './PilotTheme'
import { cx } from '../design-system'

export type PilotThemeContextValue = PilotAccentContract & {
  setAccentClass: (extra?: string) => string
}

const PilotThemeContext = createContext<PilotThemeContextValue | null>(null)

export type PilotThemeProviderProps = {
  pilotId: ProductId
  children: ReactNode
  className?: string
  /** Applique data-pilot + classes accent sur le wrapper. */
  applyWrapper?: boolean
}

export function PilotThemeProvider({
  pilotId,
  children,
  className,
  applyWrapper = true,
}: PilotThemeProviderProps) {
  const theme = useMemo(() => resolvePilotTheme(pilotId), [pilotId])
  const value = useMemo<PilotThemeContextValue>(
    () => ({
      ...theme,
      setAccentClass: (extra?: string) =>
        cx(theme.shellAccentClass, theme.sidebarAccentClass, extra),
    }),
    [theme],
  )

  const content = (
    <PilotThemeContext.Provider value={value}>{children}</PilotThemeContext.Provider>
  )

  if (!applyWrapper) return content

  return (
    <div
      className={cx('up-pilot-theme', theme.shellAccentClass, className)}
      data-pilot-theme={theme.pilotId}
      data-pilot-accent={theme.accent}
      style={
        {
          ['--up-pilot-accent' as string]: theme.accent,
          ['--up-pilot-primary' as string]: theme.primary,
          ['--up-pilot-secondary' as string]: theme.secondary,
        } as CSSProperties
      }
    >
      {content}
    </div>
  )
}

export function usePilotTheme(): PilotThemeContextValue {
  const ctx = useContext(PilotThemeContext)
  if (!ctx) {
    const fallback = resolvePilotTheme('elfis-core')
    return {
      ...fallback,
      setAccentClass: (extra?: string) => cx(fallback.shellAccentClass, extra),
    }
  }
  return ctx
}

export function usePilotThemeId(): UnifiedPilotId {
  return usePilotTheme().pilotId
}

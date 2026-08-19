/**
 * Focus mode — distractions réduites pendant la création de document.
 * Générique : pas de logique métier facturation.
 */
import { useCallback, useMemo, useState } from 'react'
import type { ComposerFocusExitTarget, ComposerFocusModeConfig } from './types'

export type UseComposerFocusOptions = {
  /** Activer le focus dès le montage (ex. route création) */
  initialEnabled?: boolean
  exitTargets?: ComposerFocusExitTarget[]
  defaultExitId?: string
  onExitNavigate?: (href: string, targetId: string) => void
}

export type UseComposerFocusResult = {
  focusMode: boolean
  enableFocus: () => void
  disableFocus: () => void
  toggleFocus: () => void
  exitTargets: ComposerFocusExitTarget[]
  exitTo: (targetId: string) => void
  config: ComposerFocusModeConfig
  hideSecondaryNav: boolean
  hideProductSidebar: boolean
  hideChromeExtras: boolean
}

export function useComposerFocus(options: UseComposerFocusOptions = {}): UseComposerFocusResult {
  const {
    initialEnabled = true,
    exitTargets = [],
    defaultExitId,
    onExitNavigate,
  } = options

  const [focusMode, setFocusMode] = useState(initialEnabled)

  const enableFocus = useCallback(() => setFocusMode(true), [])
  const disableFocus = useCallback(() => setFocusMode(false), [])
  const toggleFocus = useCallback(() => setFocusMode((v) => !v), [])

  const exitTo = useCallback(
    (targetId: string) => {
      const target =
        exitTargets.find((t) => t.id === targetId) ??
        exitTargets.find((t) => t.id === defaultExitId) ??
        exitTargets[0]
      if (!target) return
      setFocusMode(false)
      onExitNavigate?.(target.href, target.id)
    },
    [exitTargets, defaultExitId, onExitNavigate],
  )

  const config = useMemo<ComposerFocusModeConfig>(
    () => ({
      enabled: focusMode,
      exitTargets,
      onExit: exitTo,
      hideSecondaryNav: focusMode,
      hideProductSidebar: focusMode,
      hideChromeExtras: focusMode,
    }),
    [focusMode, exitTargets, exitTo],
  )

  return {
    focusMode,
    enableFocus,
    disableFocus,
    toggleFocus,
    exitTargets,
    exitTo,
    config,
    hideSecondaryNav: focusMode,
    hideProductSidebar: focusMode,
    hideChromeExtras: focusMode,
  }
}

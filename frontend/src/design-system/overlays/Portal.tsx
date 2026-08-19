import { useEffect, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { useOverlayContextOptional } from './OverlayProvider'
import { OVERLAY_ROOT_ID } from './utils/zIndex'

export type PortalProps = {
  children: ReactNode
  /** Force a specific container (tests). */
  container?: HTMLElement | null
}

/**
 * Renders children into #elfis-overlay-root (or document.body fallback).
 * Safe without document (SSR / node) — returns null.
 * When `document` exists (browser / jsdom), portals on the first paint so focus
 * management can attach to the panel immediately.
 */
export function Portal({ children, container }: PortalProps) {
  const ctx = useOverlayContextOptional()
  const [mounted, setMounted] = useState(() => typeof document !== 'undefined')

  useEffect(() => {
    setMounted(true)
  }, [])

  if (!mounted || typeof document === 'undefined') return null

  const target =
    container ??
    ctx?.portalRoot ??
    document.getElementById(OVERLAY_ROOT_ID) ??
    document.body

  if (!target) return null
  return createPortal(children, target)
}

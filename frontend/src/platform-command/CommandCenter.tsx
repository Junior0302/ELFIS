import { useCallback, useEffect, useId, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Dialog } from '../design-system/overlays/Dialog'
import { closeAllOverlays } from '../design-system/overlays/manager/overlayLifecycle'
import { trackProductEvent } from '../productEvents'
import { CommandCenterPanel } from './CommandCenterPanel'
import { cx } from '../design-system/components/cx'
import { closeChromeMenus } from '../platform-shell/global-nav/chromeMenus'
import './command-center.css'

const MOBILE_MQ = '(max-width: 1024px)'

function useIsMobileCommand(): boolean {
  const [mobile, setMobile] = useState(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return false
    return window.matchMedia(MOBILE_MQ).matches
  })
  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return
    const mq = window.matchMedia(MOBILE_MQ)
    const onChange = () => setMobile(mq.matches)
    onChange()
    mq.addEventListener?.('change', onChange)
    return () => mq.removeEventListener?.('change', onChange)
  }, [])
  return mobile
}

export type CommandCenterProps = {
  /** Controlled open — when omitted, internal state + global ⌘K */
  open?: boolean
  onOpenChange?: (open: boolean) => void
  /** Topbar trigger (default true) */
  showTrigger?: boolean
  compactTrigger?: boolean
  className?: string
  /** When false, skip registering Ctrl/Cmd+K (parent owns shortcut) */
  registerShortcut?: boolean
}

/**
 * ELFIS Command Center V1 — universal entry (search / navigate / commands).
 * Desktop: Dialog ~960px · Mobile: fullscreen Dialog.
 * Search Engine V1 via api.searchElfis — no second engine.
 */
export function CommandCenter({
  open: openProp,
  onOpenChange,
  showTrigger = true,
  compactTrigger,
  className,
  registerShortcut = true,
}: CommandCenterProps) {
  const [internalOpen, setInternalOpen] = useState(false)
  const controlled = openProp !== undefined
  const open = controlled ? Boolean(openProp) : internalOpen
  const isMobile = useIsMobileCommand()
  const navigate = useNavigate()
  const panelId = useId()
  const triggerRef = useRef<HTMLButtonElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const setOpen = useCallback(
    (next: boolean) => {
      if (next) {
        closeAllOverlays('programmatic')
        closeChromeMenus()
      }
      if (!controlled) setInternalOpen(next)
      onOpenChange?.(next)
      try {
        trackProductEvent(next ? 'command_center.open' : 'command_center.close', {
          viewport: isMobile ? 'mobile' : 'desktop',
        })
      } catch {
        /* analytics must never block */
      }
    },
    [controlled, onOpenChange, isMobile],
  )

  useEffect(() => {
    if (!registerShortcut) return
    const onKey = (e: KeyboardEvent) => {
      if (!(e.metaKey || e.ctrlKey) || e.shiftKey) return
      if (e.key.toLowerCase() !== 'k') return
      e.preventDefault()
      setOpen(!open)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [registerShortcut, open, setOpen])

  const handleNavigate = useCallback(
    (href: string) => {
      setOpen(false)
      navigate(href)
    },
    [navigate, setOpen],
  )

  const panel = (embedded: boolean) => (
    <CommandCenterPanel
      open={open}
      onNavigate={handleNavigate}
      onClose={() => setOpen(false)}
      embedded={embedded}
      panelId={panelId}
      inputRef={inputRef}
    />
  )

  return (
    <>
      {showTrigger ? (
        <div className={cx('ps-search', compactTrigger && 'ps-search--compact', className)}>
          <button
            ref={triggerRef}
            type="button"
            className="ps-search__trigger"
            aria-expanded={open}
            aria-controls={panelId}
            aria-haspopup="dialog"
            onClick={() => setOpen(true)}
          >
            <span className="ps-search__icon" aria-hidden>
              ⌕
            </span>
            {!compactTrigger ? <span>Rechercher…</span> : <span className="sr-only">Rechercher</span>}
            {!compactTrigger ? <kbd className="ps-search__kbd">⌘K</kbd> : null}
          </button>
        </div>
      ) : null}

      <Dialog
        open={open}
        onOpenChange={setOpen}
        title="ELFIS Command Center"
        description="Recherchez, naviguez ou lancez une action."
        size={isMobile ? 'full' : 'xl'}
        className={cx('command-center-dialog', isMobile && 'command-center-dialog--mobile')}
        closeOnEscape
        closeOnBackdrop
        aria-label="ELFIS Command Center"
        initialFocusRef={inputRef}
        returnFocusRef={showTrigger ? triggerRef : undefined}
      >
        {panel(isMobile)}
      </Dialog>
    </>
  )
}

/**
 * DocumentCreationModalRoot — root unique overlay création document (F1.3.1.3).
 * Gère portal, focus trap, scroll lock, aria-modal, Escape, z-index, transitions.
 * Une seule surface : type_selection → composer (pas de portails concurrents).
 *
 * CRITIQUE : closeOnRouteChange=false — l’URL `/documents/new` sync le stage,
 * elle ne doit JAMAIS fermer le modal (régression F1.3.1.2 / OverlayRouteBridge).
 */

import {
  useCallback,
  useEffect,
  useId,
  useRef,
  type ReactNode,
  type RefObject,
} from 'react'
import { Portal } from '../../design-system/overlays/Portal'
import { useOverlayBehaviour } from '../../design-system/overlays/hooks/useOverlayBehaviour'
import { useOverlayContextOptional } from '../../design-system/overlays/OverlayProvider'
import { OverlayParentIdContext } from '../../design-system/overlays/OverlayContext'
import { cx } from '../../design-system/components/cx'
import type { OverlayCloseReason } from '../../design-system/overlays/manager/types'
import type { ComposerModalStage } from './workflow/composerModalMachine'
import { composerDialogPhase } from './workflow/composerModalMachine'
import { FP_OVERLAY_Z } from './overlayLayers'

export type ComposerDialogPhase = 'type' | 'composer'

export type DocumentCreationModalRootProps = {
  open: boolean
  /** Stage machine — mappe vers phase visuelle type | composer */
  stage: ComposerModalStage
  onOpenChange: (open: boolean) => void
  children: ReactNode
  title?: string
  description?: string
  footer?: ReactNode
  returnFocusRef?: RefObject<HTMLElement | null>
  dismissible?: boolean
  closeOnBackdrop?: boolean
  closeOnEscape?: boolean
  onRequestClose?: (reason: OverlayCloseReason) => void
  className?: string
  inertTargetSelector?: string
}

/** @deprecated Prefer DocumentCreationModalRoot — alias compat tests F1.3.1.2 */
export type ComposerDialogProps = Omit<DocumentCreationModalRootProps, 'stage'> & {
  phase: ComposerDialogPhase
}

export function DocumentCreationModalRoot({
  open,
  stage,
  onOpenChange,
  children,
  title,
  description,
  footer,
  returnFocusRef,
  dismissible = true,
  closeOnBackdrop = true,
  closeOnEscape = true,
  onRequestClose,
  className,
  inertTargetSelector = '[data-billing-layout="fp05"]',
}: DocumentCreationModalRootProps) {
  const panelRef = useRef<HTMLDivElement>(null)
  const reactId = useId()
  const titleId = `${reactId}-title`
  const descriptionId = `${reactId}-desc`
  const mgr = useOverlayContextOptional()
  const scrollYRef = useRef(0)
  const phase = composerDialogPhase(stage)
  const isComposer = phase === 'composer'

  const handleClose = useCallback(
    (reason?: OverlayCloseReason) => {
      /* route_change : URL sync du workflow — ne jamais fermer ici */
      if (reason === 'route_change') return
      if (onRequestClose && reason) {
        onRequestClose(reason)
        return
      }
      onOpenChange(false)
    },
    [onOpenChange, onRequestClose],
  )

  const { overlayId } = useOverlayBehaviour({
    open,
    type: 'dialog',
    modal: true,
    dismissible,
    closeOnEscape,
    closeOnBackdrop: closeOnBackdrop && dismissible,
    /* Anti-régression F1.3.1.3 : navigate /documents/new ne doit pas close */
    closeOnRouteChange: false,
    onClose: handleClose,
    panelRef,
    returnFocusRef,
    lockScroll: true,
  })

  useEffect(() => {
    if (!open || typeof document === 'undefined') return
    scrollYRef.current = window.scrollY
    const target = document.querySelector(inertTargetSelector)
    if (target instanceof HTMLElement) {
      target.setAttribute('inert', '')
      target.setAttribute('aria-hidden', 'true')
    }
    return () => {
      if (target instanceof HTMLElement) {
        target.removeAttribute('inert')
        target.removeAttribute('aria-hidden')
      }
      window.scrollTo({ top: scrollYRef.current })
    }
  }, [open, inertTargetSelector])

  if (!open || !phase) return null

  return (
    <Portal>
      <div
        className={cx(
          'ds-overlay-backdrop',
          'ds-overlay-backdrop--dialog',
          'fp-composer-dialog-backdrop',
          isComposer && 'fp-composer-dialog-backdrop--composer',
        )}
        role="presentation"
        data-fp-create-phase={phase}
        data-fp-modal-stage={stage}
        data-fp-overlay-layer="composer-backdrop"
        style={{ zIndex: FP_OVERLAY_Z.composerBackdrop }}
        onClick={() => {
          if (closeOnBackdrop && dismissible) {
            mgr?.requestClose(overlayId, 'backdrop') ?? handleClose('backdrop')
          }
        }}
      >
        <div
          ref={panelRef}
          className={cx(
            'ds-dialog',
            isComposer ? 'fp-composer-dialog' : 'ds-dialog--sm fp-new-doc-dialog',
            'fp-create-flow',
            isComposer ? 'fp-create-flow--composer' : 'fp-create-flow--type',
            className,
          )}
          role="dialog"
          aria-modal="true"
          aria-labelledby={isComposer ? undefined : titleId}
          aria-label={isComposer ? 'Création de document' : undefined}
          aria-describedby={!isComposer && description ? descriptionId : undefined}
          tabIndex={-1}
          data-fp-composer-dialog={isComposer ? 'true' : undefined}
          data-fp-create-phase={phase}
          data-fp-modal-stage={stage}
          data-fp-document-creation-modal-root="true"
          data-fp-overlay-layer="composer-dialog"
          style={{ zIndex: FP_OVERLAY_Z.composerDialog }}
          onClick={(e) => e.stopPropagation()}
        >
          <OverlayParentIdContext.Provider value={overlayId}>
            {!isComposer ? (
              <header className="ds-dialog__header">
                <h2 id={titleId} className="ds-dialog__title">
                  {title}
                </h2>
                {description ? (
                  <p id={descriptionId} className="ds-dialog__description">
                    {description}
                  </p>
                ) : null}
                {dismissible ? (
                  <button
                    type="button"
                    className="ds-dialog__close"
                    aria-label="Fermer"
                    onClick={() => handleClose('cancel')}
                  >
                    ×
                  </button>
                ) : null}
              </header>
            ) : null}

            <div
              className={cx(
                isComposer ? 'fp-composer-dialog__body' : 'ds-dialog__content',
              )}
            >
              {children}
            </div>

            {!isComposer && footer ? (
              <footer className="ds-dialog__footer">{footer}</footer>
            ) : null}
          </OverlayParentIdContext.Provider>
        </div>
      </div>
    </Portal>
  )
}

/** Compat F1.3.1.2 — mappe phase → stage */
export function ComposerDialog({
  open,
  phase,
  onOpenChange,
  children,
  ...rest
}: ComposerDialogProps) {
  const stage: ComposerModalStage =
    phase === 'type' ? 'type_selection' : phase === 'composer' ? 'composer' : 'closed'
  return (
    <DocumentCreationModalRoot
      open={open}
      stage={stage}
      onOpenChange={onOpenChange}
      {...rest}
    >
      {children}
    </DocumentCreationModalRoot>
  )
}

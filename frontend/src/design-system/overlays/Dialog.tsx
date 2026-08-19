import {
  createContext,
  useCallback,
  useContext,
  useId,
  useMemo,
  useRef,
  type ReactNode,
  type RefObject,
} from 'react'
import { Portal } from './Portal'
import { useOverlayBehaviour } from './hooks/useOverlayBehaviour'
import { useOverlayContextOptional } from './OverlayProvider'
import { OverlayParentIdContext } from './OverlayContext'
import { cx } from '../components/cx'
import type { OverlayType } from './manager/types'

export type DialogSize = 'sm' | 'md' | 'lg' | 'xl' | 'full'

export type DialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description?: string
  children?: ReactNode
  footer?: ReactNode
  size?: DialogSize
  initialFocusRef?: RefObject<HTMLElement | null>
  returnFocusRef?: RefObject<HTMLElement | null>
  closeOnEscape?: boolean
  closeOnBackdrop?: boolean
  dismissible?: boolean
  overlayType?: OverlayType
  'aria-label'?: string
  className?: string
}

type DialogCtx = {
  titleId: string
  descriptionId: string
  hasDescription: boolean
  onClose: () => void
  dismissible: boolean
}

const DialogContext = createContext<DialogCtx | null>(null)

export function Dialog({
  open,
  onOpenChange,
  title,
  description,
  children,
  footer,
  size = 'md',
  initialFocusRef,
  returnFocusRef,
  closeOnEscape = true,
  closeOnBackdrop = true,
  dismissible = true,
  overlayType = 'dialog',
  'aria-label': ariaLabel,
  className,
}: DialogProps) {
  const panelRef = useRef<HTMLDivElement>(null)
  const reactId = useId()
  const titleId = `${reactId}-title`
  const descriptionId = `${reactId}-desc`
  const mgr = useOverlayContextOptional()
  const onClose = useCallback(() => onOpenChange(false), [onOpenChange])

  const { overlayId } = useOverlayBehaviour({
    open,
    type: overlayType,
    modal: true,
    dismissible,
    closeOnEscape,
    closeOnBackdrop,
    onClose,
    panelRef,
    initialFocusRef,
    returnFocusRef,
    lockScroll: true,
  })

  const ctx = useMemo<DialogCtx>(
    () => ({
      titleId,
      descriptionId,
      hasDescription: Boolean(description),
      onClose,
      dismissible,
    }),
    [titleId, descriptionId, description, onClose, dismissible],
  )

  if (!open) return null

  return (
    <Portal>
      <div
        className="ds-overlay-backdrop ds-overlay-backdrop--dialog"
        role="presentation"
        onClick={() => {
          if (closeOnBackdrop && dismissible) {
            mgr?.requestClose(overlayId, 'backdrop') ?? onClose()
          }
        }}
      >
        <div
          ref={panelRef}
          className={cx('ds-dialog', `ds-dialog--${size}`, className)}
          role="dialog"
          aria-modal="true"
          aria-labelledby={ariaLabel ? undefined : titleId}
          aria-label={ariaLabel}
          aria-describedby={description ? descriptionId : undefined}
          tabIndex={-1}
          onClick={(e) => e.stopPropagation()}
        >
          <OverlayParentIdContext.Provider value={overlayId}>
            <DialogContext.Provider value={ctx}>
              <DialogHeader>
                <DialogTitle>{title}</DialogTitle>
                {description ? <DialogDescription>{description}</DialogDescription> : null}
                {dismissible ? <DialogClose /> : null}
              </DialogHeader>
              {children ? <DialogContent>{children}</DialogContent> : null}
              {footer ? <DialogFooter>{footer}</DialogFooter> : null}
            </DialogContext.Provider>
          </OverlayParentIdContext.Provider>
        </div>
      </div>
    </Portal>
  )
}

function useDialogCtx() {
  const ctx = useContext(DialogContext)
  if (!ctx) throw new Error('Dialog subcomponent hors Dialog')
  return ctx
}

export function DialogHeader({ children, className }: { children: ReactNode; className?: string }) {
  return <header className={cx('ds-dialog__header', className)}>{children}</header>
}

export function DialogTitle({ children }: { children: ReactNode }) {
  const { titleId } = useDialogCtx()
  return (
    <h2 id={titleId} className="ds-dialog__title">
      {children}
    </h2>
  )
}

export function DialogDescription({ children }: { children: ReactNode }) {
  const { descriptionId } = useDialogCtx()
  return (
    <p id={descriptionId} className="ds-dialog__description">
      {children}
    </p>
  )
}

export function DialogContent({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cx('ds-dialog__content', className)}>{children}</div>
}

export function DialogFooter({ children, className }: { children: ReactNode; className?: string }) {
  return <footer className={cx('ds-dialog__footer', className)}>{children}</footer>
}

export function DialogClose({ label = 'Fermer' }: { label?: string }) {
  const { onClose, dismissible } = useDialogCtx()
  if (!dismissible) return null
  return (
    <button type="button" className="ds-dialog__close" onClick={onClose} aria-label={label}>
      ×
    </button>
  )
}

import { useCallback, useId, useRef, type ReactNode, type RefObject } from 'react'
import { Portal } from './Portal'
import { useOverlayBehaviour } from './hooks/useOverlayBehaviour'
import { cx } from '../components/cx'

export type DrawerSide = 'left' | 'right' | 'bottom'
export type DrawerSize = 'sm' | 'md' | 'lg' | 'full'

export type DrawerProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  side?: DrawerSide
  size?: DrawerSize
  modal?: boolean
  title: string
  description?: string
  children?: ReactNode
  footer?: ReactNode
  closeOnEscape?: boolean
  closeOnBackdrop?: boolean
  dismissible?: boolean
  initialFocusRef?: RefObject<HTMLElement | null>
  returnFocusRef?: RefObject<HTMLElement | null>
  className?: string
}

export function Drawer({
  open,
  onOpenChange,
  side = 'right',
  size = 'md',
  modal = true,
  title,
  description,
  children,
  footer,
  closeOnEscape = true,
  closeOnBackdrop = true,
  dismissible = true,
  initialFocusRef,
  returnFocusRef,
  className,
}: DrawerProps) {
  const panelRef = useRef<HTMLElement>(null)
  const reactId = useId()
  const titleId = `${reactId}-drawer-title`
  const descId = `${reactId}-drawer-desc`
  const onClose = useCallback(() => onOpenChange(false), [onOpenChange])

  useOverlayBehaviour({
    open,
    type: 'drawer',
    modal,
    dismissible,
    closeOnEscape,
    closeOnBackdrop,
    onClose,
    panelRef,
    initialFocusRef,
    returnFocusRef,
    lockScroll: modal,
  })

  if (!open) return null

  return (
    <Portal>
      <div
        className={cx(
          'ds-overlay-backdrop',
          'ds-overlay-backdrop--drawer',
          !modal && 'ds-overlay-backdrop--transparent',
        )}
        role="presentation"
        onClick={() => {
          if (modal && closeOnBackdrop && dismissible) onClose()
        }}
      >
        <aside
          ref={panelRef}
          className={cx(
            'ds-drawer',
            `ds-drawer--${side}`,
            `ds-drawer--${size}`,
            className,
          )}
          role="dialog"
          aria-modal={modal || undefined}
          aria-labelledby={titleId}
          aria-describedby={description ? descId : undefined}
          tabIndex={-1}
          onClick={(e) => e.stopPropagation()}
        >
          <header className="ds-drawer__header">
            <div>
              <h2 id={titleId} className="ds-drawer__title">
                {title}
              </h2>
              {description ? (
                <p id={descId} className="ds-drawer__description">
                  {description}
                </p>
              ) : null}
            </div>
            {dismissible ? (
              <button
                type="button"
                className="ds-drawer__close"
                onClick={onClose}
                aria-label="Fermer"
              >
                ×
              </button>
            ) : null}
          </header>
          <div className="ds-drawer__content">{children}</div>
          {footer ? <footer className="ds-drawer__footer">{footer}</footer> : null}
        </aside>
      </div>
    </Portal>
  )
}

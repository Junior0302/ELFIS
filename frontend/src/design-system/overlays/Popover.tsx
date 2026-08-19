import {
  useCallback,
  useEffect,
  useId,
  useRef,
  type ReactNode,
  type RefObject,
} from 'react'
import { useOverlayBehaviour } from './hooks/useOverlayBehaviour'
import { cx } from '../components/cx'

export type PopoverPlacement = 'top' | 'right' | 'bottom' | 'left'

export type PopoverProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  trigger: ReactNode
  children: ReactNode
  placement?: PopoverPlacement
  modal?: boolean
  closeOnInteractOutside?: boolean
  initialFocusRef?: RefObject<HTMLElement | null>
  className?: string
}

/**
 * Lightweight non-modal popover (default). Option B positioning.
 */
export function Popover({
  open,
  onOpenChange,
  trigger,
  children,
  placement = 'bottom',
  modal = false,
  closeOnInteractOutside = true,
  initialFocusRef,
  className,
}: PopoverProps) {
  const panelRef = useRef<HTMLDivElement>(null)
  const wrapRef = useRef<HTMLSpanElement>(null)
  const reactId = useId()
  const onClose = useCallback(() => onOpenChange(false), [onOpenChange])

  useOverlayBehaviour({
    open,
    type: 'popover',
    modal,
    dismissible: true,
    closeOnEscape: true,
    onClose,
    panelRef,
    initialFocusRef,
    lockScroll: modal,
  })

  useEffect(() => {
    if (!open || !closeOnInteractOutside) return
    const onPointer = (event: MouseEvent) => {
      const target = event.target as Node
      if (panelRef.current?.contains(target)) return
      if (wrapRef.current?.contains(target)) return
      onClose()
    }
    document.addEventListener('mousedown', onPointer)
    return () => document.removeEventListener('mousedown', onPointer)
  }, [open, closeOnInteractOutside, onClose])

  return (
    <span className={cx('ds-popover-wrap', `ds-popover-wrap--${placement}`)} ref={wrapRef}>
      <span
        className="ds-popover-trigger"
        onClick={() => onOpenChange(!open)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            onOpenChange(!open)
          }
        }}
      >
        {trigger}
      </span>
      {open ? (
        <div
          ref={panelRef}
          id={reactId}
          role="dialog"
          aria-modal={modal || undefined}
          className={cx('ds-popover', `ds-popover--${placement}`, className)}
          tabIndex={-1}
        >
          {children}
        </div>
      ) : null}
    </span>
  )
}

import {
  cloneElement,
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type ReactElement,
  type ReactNode,
} from 'react'
import { cx } from '../components/cx'
import { useOverlayBehaviour } from './hooks/useOverlayBehaviour'

export type TooltipPlacement = 'top' | 'right' | 'bottom' | 'left'

export type TooltipProps = {
  content: ReactNode
  children: ReactElement
  placement?: TooltipPlacement
  delay?: number
  disabled?: boolean
  maxWidth?: number
  id?: string
}

/**
 * Accessible tooltip — hover + focus. Registered as passive overlay (no scroll lock / focus trap).
 */
export function Tooltip({
  content,
  children,
  placement = 'top',
  delay = 200,
  disabled = false,
  maxWidth = 240,
  id,
}: TooltipProps) {
  const reactId = useId()
  const tipId = id ?? `${reactId}-tip`
  const [open, setOpen] = useState(false)
  const timerRef = useRef<number | null>(null)
  const panelRef = useRef<HTMLSpanElement>(null)

  const hide = useCallback(() => {
    if (timerRef.current) window.clearTimeout(timerRef.current)
    timerRef.current = null
    setOpen(false)
  }, [])

  const show = () => {
    if (disabled) return
    if (timerRef.current) window.clearTimeout(timerRef.current)
    timerRef.current = window.setTimeout(() => setOpen(true), delay)
  }

  useOverlayBehaviour({
    open: open && !disabled,
    type: 'tooltip',
    modal: false,
    dismissible: true,
    closeOnEscape: true,
    closeOnRouteChange: true,
    onClose: hide,
    panelRef,
    lockScroll: false,
  })

  useEffect(() => () => {
    if (timerRef.current) window.clearTimeout(timerRef.current)
  }, [])

  const child = cloneElement(children, {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ...(children.props as any),
    'aria-describedby': open
      ? tipId
      : (children.props as { 'aria-describedby'?: string })['aria-describedby'],
    onMouseEnter: (e: React.MouseEvent) => {
      ;(children.props as { onMouseEnter?: (e: React.MouseEvent) => void }).onMouseEnter?.(e)
      show()
    },
    onMouseLeave: (e: React.MouseEvent) => {
      ;(children.props as { onMouseLeave?: (e: React.MouseEvent) => void }).onMouseLeave?.(e)
      hide()
    },
    onFocus: (e: React.FocusEvent) => {
      ;(children.props as { onFocus?: (e: React.FocusEvent) => void }).onFocus?.(e)
      show()
    },
    onBlur: (e: React.FocusEvent) => {
      ;(children.props as { onBlur?: (e: React.FocusEvent) => void }).onBlur?.(e)
      hide()
    },
    onKeyDown: (e: React.KeyboardEvent) => {
      ;(children.props as { onKeyDown?: (e: React.KeyboardEvent) => void }).onKeyDown?.(e)
      if (e.key === 'Escape') hide()
    },
  })

  return (
    <span className={cx('ds-tooltip-wrap', `ds-tooltip-wrap--${placement}`)}>
      {child}
      {open && !disabled ? (
        <span
          ref={panelRef}
          id={tipId}
          role="tooltip"
          className={cx('ds-tooltip', `ds-tooltip--${placement}`)}
          style={{ maxWidth }}
        >
          {content}
        </span>
      ) : null}
    </span>
  )
}

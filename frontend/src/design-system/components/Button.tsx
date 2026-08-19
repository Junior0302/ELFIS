import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react'
import { cx } from './cx'

export type ButtonVariant = 'primary' | 'secondary' | 'danger'
export type ButtonSize = 'sm' | 'md'

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant
  size?: ButtonSize
  children: ReactNode
}

/** Product-identity button — wraps legacy `.btn` for visual parity. */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = 'primary', size = 'md', className, type = 'button', children, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      className={cx(
        'btn',
        variant === 'secondary' && 'secondary',
        variant === 'danger' && 'danger-outline',
        size === 'sm' && 'btn-sm',
        'ds-btn',
        className,
      )}
      {...rest}
    >
      {children}
    </button>
  )
})

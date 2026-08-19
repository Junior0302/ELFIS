import { forwardRef, type InputHTMLAttributes } from 'react'
import { cx } from './cx'

export type InputProps = InputHTMLAttributes<HTMLInputElement>

/** Neutral text input — styles aligned with legacy `.field input`. */
export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { className, ...rest },
  ref,
) {
  return <input ref={ref} className={cx('ds-input', className)} {...rest} />
})

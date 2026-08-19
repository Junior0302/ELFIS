import {
  Children,
  cloneElement,
  isValidElement,
  type ReactElement,
  type ReactNode,
} from 'react'
import { cx } from './cx'

export type FormFieldProps = {
  label: string
  htmlFor: string
  children: ReactNode
  error?: string | null
  hint?: string
  required?: boolean
  className?: string
}

/** Accessible label + control + error/hint wrapper. No validation logic. */
export function FormField({
  label,
  htmlFor,
  children,
  error,
  hint,
  required,
  className,
}: FormFieldProps) {
  const describedBy = error ? `${htmlFor}-error` : hint ? `${htmlFor}-hint` : undefined

  const control = (() => {
    if (!describedBy || !isValidElement(children)) return children
    const child = children as ReactElement<{ 'aria-describedby'?: string; id?: string }>
    const existing = child.props['aria-describedby']
    return cloneElement(child, {
      id: child.props.id ?? htmlFor,
      'aria-describedby': existing ? `${existing} ${describedBy}` : describedBy,
      'aria-invalid': error ? true : undefined,
    } as never)
  })()

  return (
    <div className={cx('ds-form-field', 'field', className)}>
      <label htmlFor={htmlFor}>
        {label}
        {required ? (
          <span className="ds-form-field__required" aria-hidden>
            {' '}
            *
          </span>
        ) : null}
      </label>
      {Children.count(children) === 1 ? control : children}
      {hint && !error ? (
        <p id={`${htmlFor}-hint`} className="ds-form-field__hint muted">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={`${htmlFor}-error`} className="ds-form-field__error enterprise-setup-field-error" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  )
}

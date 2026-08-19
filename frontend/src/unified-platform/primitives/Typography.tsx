/**
 * Primitives typographie plateforme.
 */

import type { HTMLAttributes, ReactNode } from 'react'
import { cx } from '../../design-system'

export function DisplayTitle({
  children,
  className,
  as: Tag = 'h1',
  ...rest
}: HTMLAttributes<HTMLHeadingElement> & {
  children: ReactNode
  as?: 'h1' | 'h2' | 'h3'
}) {
  return (
    <Tag className={cx('up-display-title', className)} {...rest}>
      {children}
    </Tag>
  )
}

export function BodyText({
  children,
  className,
  muted,
  ...rest
}: HTMLAttributes<HTMLParagraphElement> & {
  children: ReactNode
  muted?: boolean
}) {
  return (
    <p className={cx('up-body-text', muted && 'up-body-text--muted', className)} {...rest}>
      {children}
    </p>
  )
}

export function Eyebrow({
  children,
  className,
  ...rest
}: HTMLAttributes<HTMLParagraphElement> & { children: ReactNode }) {
  return (
    <p className={cx('up-eyebrow', className)} {...rest}>
      {children}
    </p>
  )
}

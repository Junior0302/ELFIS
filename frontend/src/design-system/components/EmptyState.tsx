import type { ReactNode } from 'react'
import { cx } from './cx'

export type EmptyStateProps = {
  title: string
  description?: string
  action?: ReactNode
  className?: string
}

export function EmptyState({ title, description, action, className }: EmptyStateProps) {
  return (
    <div className={cx('ui-empty', 'ds-empty', className)} role="status">
      <p className="ui-empty-title">{title}</p>
      {description ? <p className="muted">{description}</p> : null}
      {action ? <div className="ui-empty-action">{action}</div> : null}
    </div>
  )
}

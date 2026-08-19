import type { ReactNode } from 'react'
import { cx } from './cx'

export type PageHeaderProps = {
  title: string
  description?: string
  eyebrow?: string
  actions?: ReactNode
  children?: ReactNode
  className?: string
}

export function PageHeader({
  title,
  description,
  eyebrow,
  actions,
  children,
  className,
}: PageHeaderProps) {
  return (
    <header className={cx('page-head', 'ds-page-header', className)}>
      <div className="ds-page-header__main">
        {eyebrow ? <p className="ds-page-header__eyebrow">{eyebrow}</p> : null}
        <h2 className="ds-page-header__title">{title}</h2>
        {description ? <p className="ds-page-header__description">{description}</p> : null}
        {children}
      </div>
      {actions ? <div className="ds-page-header__actions">{actions}</div> : null}
    </header>
  )
}

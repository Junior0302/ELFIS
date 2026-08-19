import type { ReactNode } from 'react'
import { cx } from './cx'

export type SectionVariant = 'default' | 'muted' | 'bordered'
export type SectionSpacing = 'compact' | 'normal' | 'spacious'

export type SectionProps = {
  title?: string
  description?: string
  eyebrow?: string
  actions?: ReactNode
  children: ReactNode
  variant?: SectionVariant
  spacing?: SectionSpacing
  className?: string
}

export function Section({
  title,
  description,
  eyebrow,
  actions,
  children,
  variant = 'default',
  spacing = 'normal',
  className,
}: SectionProps) {
  const hasHeader = Boolean(title || description || eyebrow || actions)
  return (
    <section
      className={cx(
        'ds-section',
        `ds-section--${variant}`,
        `ds-section--${spacing}`,
        className,
      )}
    >
      {hasHeader ? (
        <header className="ds-section__header">
          <div className="ds-section__heading">
            {eyebrow ? <p className="ds-section__eyebrow">{eyebrow}</p> : null}
            {title ? <h3 className="ds-section__title">{title}</h3> : null}
            {description ? <p className="ds-section__description">{description}</p> : null}
          </div>
          {actions ? <div className="ds-section__actions">{actions}</div> : null}
        </header>
      ) : null}
      <div className="ds-section__content">{children}</div>
    </section>
  )
}

/**
 * Section Accueil plateforme — en-tête sobre + contenu.
 */

import type { ReactNode } from 'react'
import { cx } from '../design-system'

export type PlatformHomeSectionProps = {
  id?: string
  title: string
  description?: string
  eyebrow?: string
  actions?: ReactNode
  children: ReactNode
  className?: string
  /** Niveau hiérarchique visuel (1 = action, 4 = historique). */
  level?: 1 | 2 | 3 | 4
}

export function PlatformHomeSection({
  id,
  title,
  description,
  eyebrow,
  actions,
  children,
  className,
  level = 3,
}: PlatformHomeSectionProps) {
  const titleId = id ? `${id}-title` : undefined
  return (
    <section
      id={id}
      className={cx('ph-section', `ph-section--l${level}`, className)}
      aria-labelledby={titleId}
      data-ph-level={level}
    >
      <header className="ph-section__head">
        <div className="ph-section__titles">
          {eyebrow ? <p className="ph-section__eyebrow">{eyebrow}</p> : null}
          <h2 id={titleId} className="ph-section__title">
            {title}
          </h2>
          {description ? <p className="ph-section__desc">{description}</p> : null}
        </div>
        {actions ? <div className="ph-section__actions">{actions}</div> : null}
      </header>
      <div className="ph-section__body">{children}</div>
    </section>
  )
}

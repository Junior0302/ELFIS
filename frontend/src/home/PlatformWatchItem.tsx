/**
 * Élément « À surveiller » — signaux actionnables uniquement.
 */

import type { CSSProperties } from 'react'
import { Link } from 'react-router-dom'
import { cx } from '../design-system'

export type PlatformWatchItemProps = {
  id: string
  title: string
  context?: string
  href?: string
  tone?: 'attention' | 'info'
  accent?: string
}

export function PlatformWatchItem({
  title,
  context,
  href,
  tone = 'attention',
  accent,
}: PlatformWatchItemProps) {
  const style = accent ? ({ '--ph-watch-accent': accent } as CSSProperties) : undefined
  const className = cx('ph-watch-item', `ph-watch-item--${tone}`)

  const inner = (
    <>
      <span className="ph-watch-item__dot" aria-hidden />
      <span className="ph-watch-item__body">
        <strong className="ph-watch-item__title">{title}</strong>
        {context ? <span className="ph-watch-item__ctx">{context}</span> : null}
      </span>
      {href ? (
        <span className="ph-watch-item__cta">Ouvrir</span>
      ) : null}
    </>
  )

  if (href) {
    return (
      <Link to={href} className={className} style={style}>
        {inner}
      </Link>
    )
  }

  return (
    <div className={className} style={style} role="status">
      {inner}
    </div>
  )
}

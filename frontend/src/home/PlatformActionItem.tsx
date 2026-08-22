/**
 * Action rapide Accueil — route réelle + label d’espace métier.
 */

import type { CSSProperties } from 'react'
import { Link } from 'react-router-dom'
import { cx } from '../design-system'

export type PlatformActionItemProps = {
  title: string
  description: string
  href: string
  workspaceLabel: string
  accent?: string
  className?: string
}

export function PlatformActionItem({
  title,
  description,
  href,
  workspaceLabel,
  accent,
  className,
}: PlatformActionItemProps) {
  const style = accent ? ({ '--ph-action-accent': accent } as CSSProperties) : undefined
  return (
    <Link
      to={href}
      className={cx('ph-action', className)}
      style={style}
      data-workspace-label={workspaceLabel}
    >
      <span className="ph-action__mark" aria-hidden>
        {title.charAt(0)}
      </span>
      <span className="ph-action__body">
        <strong className="ph-action__title">{title}</strong>
        <span className="ph-action__desc">{description}</span>
      </span>
      <span className="ph-action__space">{workspaceLabel}</span>
    </Link>
  )
}

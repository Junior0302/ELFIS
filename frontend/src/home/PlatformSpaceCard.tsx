/**
 * Carte espace métier Accueil — SoT = WorkspaceConfig / registry.
 */

import type { CSSProperties, MouseEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { cx } from '../design-system'
import { openWorkspaceSpace } from './openWorkspaceSpace'

export type PlatformSpaceCardProps = {
  id: string
  title: string
  description: string
  engineLabel?: string
  statusLabel: string
  accent: string
  available: boolean
  to: string | null
  engineProductId?: string | null
  resumeHint?: string | null
}

export function PlatformSpaceCard({
  title,
  description,
  engineLabel,
  statusLabel,
  accent,
  available,
  to,
  engineProductId,
  resumeHint,
}: PlatformSpaceCardProps) {
  const navigate = useNavigate()
  const style = { '--ph-space-accent': accent } as CSSProperties
  const letter = title.charAt(0).toUpperCase()

  const body = (
    <>
      <span className="ph-space__bar" aria-hidden />
      <div className="ph-space__top">
        <span className="ph-space__icon" aria-hidden>
          {letter}
        </span>
        <div className="ph-space__identity">
          <strong className="ph-space__title">{title}</strong>
          {engineLabel ? <span className="ph-space__engine">{engineLabel}</span> : null}
        </div>
        <span className={cx('ph-space__status', available ? 'is-on' : 'is-soon')}>
          {statusLabel}
        </span>
      </div>
      <p className="ph-space__desc">{description}</p>
      {resumeHint ? <p className="ph-space__resume">{resumeHint}</p> : null}
      {available && to ? (
        <span className="ph-space__cta">
          Ouvrir <span aria-hidden>→</span>
        </span>
      ) : null}
    </>
  )

  if (!available || !to) {
    return (
      <div className="ph-space is-disabled" style={style} data-space-card={title}>
        {body}
      </div>
    )
  }

  const onClick = (e: MouseEvent) => {
    e.preventDefault()
    openWorkspaceSpace(navigate, { route: to, engineProductId })
  }

  return (
    <Link
      to={to}
      className="ph-space ph-space--link"
      style={style}
      data-space-card={title}
      onClick={onClick}
    >
      {body}
    </Link>
  )
}

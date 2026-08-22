/**
 * Carte espace métier Accueil — SoT = WorkspaceConfig / registry.
 */

import type { CSSProperties, MouseEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { cx } from '../design-system'
import { WorkspaceSpaceIcon } from '../workspaces/WorkspaceSpaceIcon'
import { openWorkspaceSpace } from './openWorkspaceSpace'

export type PlatformSpaceCardProps = {
  id: string
  title: string
  description: string
  icon: string
  engineLabel?: string
  statusLabel: string
  accent: string
  accentSoft?: string
  available: boolean
  to: string | null
  engineProductId?: string | null
  resumeHint?: string | null
}

export function PlatformSpaceCard({
  title,
  description,
  icon,
  engineLabel,
  statusLabel,
  accent,
  accentSoft,
  available,
  to,
  engineProductId,
  resumeHint,
}: PlatformSpaceCardProps) {
  const navigate = useNavigate()
  const style = { '--ph-space-accent': accent } as CSSProperties

  const body = (
    <>
      <span className="ph-space__bar" aria-hidden />
      <div className="ph-space__top">
        <WorkspaceSpaceIcon
          icon={icon}
          accent={accent}
          soft={accentSoft}
          size="sm"
          className="ph-space__icon"
        />
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

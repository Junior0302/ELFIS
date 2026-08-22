/**
 * Marque visuelle espace métier — fond pastel, coins 12px, icône Lucide trait 2px.
 */

import type { CSSProperties } from 'react'
import { cx } from '../design-system/components/cx'
import { resolveWorkspaceIcon } from './workspaceIcons'

export type WorkspaceSpaceIconProps = {
  icon: string
  accent: string
  soft?: string
  size?: 'sm' | 'md'
  className?: string
}

export function WorkspaceSpaceIcon({
  icon,
  accent,
  soft,
  size = 'md',
  className,
}: WorkspaceSpaceIconProps) {
  const style = {
    '--ws-icon-accent': accent,
    '--ws-icon-soft': soft ?? `color-mix(in srgb, ${accent} 14%, #fff)`,
  } as CSSProperties

  return (
    <span
      className={cx('workspace-space-icon', `workspace-space-icon--${size}`, className)}
      style={style}
      aria-hidden
    >
      {resolveWorkspaceIcon(icon, 'workspace-space-icon__glyph')}
    </span>
  )
}

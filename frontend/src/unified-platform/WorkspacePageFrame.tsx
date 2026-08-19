import type { ReactNode } from 'react'
import { cx } from '../design-system'
import { isUnifiedPlatformUiEnabled } from './featureFlag'
import { ElfisPageFrame, type ElfisPageFramePadding } from './primitives/ElfisPageFrame'

export type WorkspacePageFrameProps = {
  children: ReactNode
  /** Désactive le frame (composer full focus, etc.). */
  disabled?: boolean
  padding?: ElfisPageFramePadding
  className?: string
}

/**
 * Frame page workspace — aligne padding / max-width des pages standard
 * sur le même contrat que les dashboards (ElfisPageFrame 1680px).
 */
export function WorkspacePageFrame({
  children,
  disabled = false,
  padding = 'comfortable',
  className,
}: WorkspacePageFrameProps) {
  if (disabled || !isUnifiedPlatformUiEnabled()) {
    return <>{children}</>
  }

  return (
    <ElfisPageFrame
      padding={padding}
      className={cx('workspace-page-frame', className)}
      data-workspace-page-frame="v1"
    >
      {children}
    </ElfisPageFrame>
  )
}

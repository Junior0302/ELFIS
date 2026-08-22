/**
 * En-tête de page workspace — réutilise ElfisPageHeader / PageHeader DS.
 * Accent via data-workspace sur le shell (pas de couleur hardcodée).
 */

import type { ReactNode } from 'react'
import { cx } from '../design-system'
import {
  ElfisPageHeader,
  type ElfisPageHeaderProps,
} from '../unified-platform/primitives/ElfisPageHeader'

export type WorkspacePageHeaderProps = ElfisPageHeaderProps & {
  /** Actions secondaires (export, …) regroupées après actions. */
  secondaryActions?: ReactNode
}

export function WorkspacePageHeader({
  className,
  actions,
  secondaryActions,
  ...rest
}: WorkspacePageHeaderProps) {
  const mergedActions =
    actions || secondaryActions ? (
      <div className="workspace-page-header__actions">
        {actions}
        {secondaryActions}
      </div>
    ) : undefined

  return (
    <ElfisPageHeader
      {...rest}
      actions={mergedActions}
      className={cx('workspace-page-header', className)}
    />
  )
}

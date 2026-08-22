/**
 * Adapter Commercial — WorkspaceSidebar + commercialWorkspaceConfig.
 * Pas de liens cross-domaine Espaces (Finance / ELFIS) — Espaces = seul sélecteur global.
 */

import { useCallback } from 'react'
import { SALES_PRODUCT_NAV_ID } from './SalesProductNav.ids'
import { WorkspaceSidebar } from '../workspaces/WorkspaceSidebar'
import { commercialWorkspaceConfig } from '../workspaces'
import type { WorkspaceNavGroup } from '../workspaces'

export { SALES_PRODUCT_NAV_ID } from './SalesProductNav.ids'

type SalesProductNavProps = {
  onNavigate?: () => void
  collapsed?: boolean
  onCollapsedChange?: (collapsed: boolean | ((prev: boolean) => boolean)) => void
}

function preferClientsOverProspection(
  best: WorkspaceNavGroup | undefined,
  candidate: WorkspaceNavGroup,
): boolean {
  return candidate.id === 'clients' && best?.id === 'prospection'
}

/**
 * Adapter Commercial — même comportement nested expand que Finance.
 * Accent bleu via --workspace-commercial.
 */
export function SalesProductNav({
  onNavigate,
  collapsed = false,
  onCollapsedChange,
}: SalesProductNavProps) {
  const preferActiveGroup = useCallback(preferClientsOverProspection, [])

  return (
    <WorkspaceSidebar
      workspace={commercialWorkspaceConfig}
      navId={SALES_PRODUCT_NAV_ID}
      ariaLabel="Navigation Commercial"
      collapsed={collapsed}
      onCollapsedChange={onCollapsedChange}
      onNavigate={onNavigate}
      preferActiveGroup={preferActiveGroup}
      className="ps-product-nav--sales sales-product-nav"
    />
  )
}

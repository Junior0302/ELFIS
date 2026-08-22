/**
 * Adapter Documents — sidebar minimale (hub Vault).
 */

import { DOCUMENTS_PRODUCT_NAV_ID } from './DocumentsProductNav.ids'
import { WorkspaceSidebar } from '../workspaces/WorkspaceSidebar'
import { documentsWorkspaceConfig } from '../workspaces'

export { DOCUMENTS_PRODUCT_NAV_ID } from './DocumentsProductNav.ids'

type DocumentsProductNavProps = {
  onNavigate?: () => void
  collapsed?: boolean
  onCollapsedChange?: (collapsed: boolean | ((prev: boolean) => boolean)) => void
}

export function DocumentsProductNav({
  onNavigate,
  collapsed = false,
  onCollapsedChange,
}: DocumentsProductNavProps) {
  return (
    <WorkspaceSidebar
      workspace={documentsWorkspaceConfig}
      navId={DOCUMENTS_PRODUCT_NAV_ID}
      ariaLabel="Navigation Documents"
      collapsed={collapsed}
      onCollapsedChange={onCollapsedChange}
      onNavigate={onNavigate}
      className="ps-product-nav--documents documents-product-nav"
    />
  )
}

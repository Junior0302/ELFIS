import { Outlet } from 'react-router-dom'
import { SalesProductNav } from '../../platform-shell/SalesProductNav'
import { getProductShellConfiguration } from '../../platform-shell/productShellConfig'
import { useProductSidebarCollapsed } from '../../platform-shell/useProductSidebarCollapsed'
import { PilotWorkspace, WorkspacePageFrame } from '../../unified-platform'

/**
 * SalesPilot — shell unifié + nav métier.
 * Collapse UI.P1 (mêmes dimensions que Compta). Thème via RuntimeThemeSync.
 * Espaces = seul sélecteur global.
 */
export default function SalesWorkspaceLayout() {
  const config = getProductShellConfiguration('salespilot')
  const { collapsed: sidebarCollapsed, setCollapsed: setSidebarCollapsed } =
    useProductSidebarCollapsed()

  return (
    <PilotWorkspace
      pilotId={config.productId}
      dataWorkspace="commercial"
      chrome={config.chrome}
      sidebarCollapsed={sidebarCollapsed}
      nav={({ closeMobileNav }) => (
        <SalesProductNav
          onNavigate={closeMobileNav}
          collapsed={sidebarCollapsed}
          onCollapsedChange={setSidebarCollapsed}
        />
      )}
    >
      <WorkspacePageFrame>
        <Outlet />
      </WorkspacePageFrame>
    </PilotWorkspace>
  )
}

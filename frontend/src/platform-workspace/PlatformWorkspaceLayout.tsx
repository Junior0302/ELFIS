import { Outlet } from 'react-router-dom'
import { PlatformNavigation } from './PlatformNavigation'
import { PilotWorkspace, WorkspacePageFrame } from '../unified-platform'
import { useProductSidebarCollapsed } from '../platform-shell/useProductSidebarCollapsed'
import './platform-workspace.css'

/**
 * Layout workspace ELFIS — distinct de Compta / Sales.
 * Même navigation que Home (elfisNavigationConfig).
 */
export default function PlatformWorkspaceLayout() {
  const { collapsed, setCollapsed } = useProductSidebarCollapsed()

  return (
    <PilotWorkspace
      pilotId="elfis-core"
      title="ELFIS"
      applyPilotAccent={false}
      className="ps-shell--platform ps-shell--home-hybrid"
      sidebarClassName="ps-sidebar--platform"
      sidebarCollapsed={collapsed}
      chrome={{
        showLauncher: true,
        showSearch: true,
        showNotifications: true,
        showOrganizationSwitcher: true,
        showWorkspaceSwitcher: false,
        showProductIndicator: false,
      }}
      nav={({ closeMobileNav }) => (
        <PlatformNavigation
          onNavigate={closeMobileNav}
          collapsed={collapsed}
          onCollapsedChange={setCollapsed}
        />
      )}
    >
      <WorkspacePageFrame>
        <Outlet />
      </WorkspacePageFrame>
    </PilotWorkspace>
  )
}


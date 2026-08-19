import { Outlet } from 'react-router-dom'
import { PilotWorkspace, WorkspacePageFrame } from '../unified-platform'
import { HomePlatformSidebar } from './HomePlatformSidebar'
import { getProductShellConfiguration } from '../platform-shell/productShellConfig'
import { useProductSidebarCollapsed } from '../platform-shell/useProductSidebarCollapsed'
import './home.css'

/**
 * Layout ELFIS Home — shell unifié + sidebar Home (config unique NAV.CORE.1).
 */
export default function ElfisHomeLayout() {
  const config = getProductShellConfiguration('elfis-core')
  const { collapsed, setCollapsed } = useProductSidebarCollapsed()

  return (
    <PilotWorkspace
      pilotId={config.productId}
      title="Plateforme"
      className="ps-shell--home-hybrid"
      sidebarClassName="ps-sidebar--home"
      chrome={config.chrome}
      sidebarCollapsed={collapsed}
      nav={({ closeMobileNav }) => (
        <HomePlatformSidebar
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


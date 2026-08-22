import { Outlet, useLocation } from 'react-router-dom'
import { PlatformNavigation } from './PlatformNavigation'
import { DocumentsProductNav } from '../platform-shell/DocumentsProductNav'
import { PilotWorkspace, WorkspacePageFrame } from '../unified-platform'
import { useProductSidebarCollapsed } from '../platform-shell/useProductSidebarCollapsed'
import './platform-workspace.css'

function isDocumentsWorkspacePath(pathname: string): boolean {
  return pathname === '/platform/documents' || pathname.startsWith('/platform/documents/')
}

/**
 * Layout workspace ELFIS — distinct de Compta / Sales.
 * Sur /platform/documents : sidebar Documents (violet).
 * Sinon : navigation plateforme ELFIS.
 */
export default function PlatformWorkspaceLayout() {
  const { collapsed, setCollapsed } = useProductSidebarCollapsed()
  const location = useLocation()
  const documentsSpace = isDocumentsWorkspacePath(location.pathname)

  return (
    <PilotWorkspace
      pilotId="elfis-core"
      title="ELFIS"
      applyPilotAccent={false}
      dataWorkspace={documentsSpace ? 'documents' : undefined}
      className={
        documentsSpace
          ? 'ps-shell--platform ps-shell--home-hybrid ps-shell--documents-workspace'
          : 'ps-shell--platform ps-shell--home-hybrid'
      }
      sidebarClassName="ps-sidebar--platform"
      sidebarCollapsed={collapsed}
      chrome={{
        showLauncher: true,
        showSearch: true,
        showNotifications: true,
        showOrganizationSwitcher: true,
        showProductIndicator: false,
      }}
      nav={({ closeMobileNav }) =>
        documentsSpace ? (
          <DocumentsProductNav
            onNavigate={closeMobileNav}
            collapsed={collapsed}
            onCollapsedChange={setCollapsed}
          />
        ) : (
          <PlatformNavigation
            onNavigate={closeMobileNav}
            collapsed={collapsed}
            onCollapsedChange={setCollapsed}
          />
        )
      }
    >
      <WorkspacePageFrame>
        <Outlet />
      </WorkspacePageFrame>
    </PilotWorkspace>
  )
}

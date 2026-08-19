/**

 * Sidebar Home — même config / composant que le drawer global.

 */



import { ElfisGlobalNavigation } from '../platform-shell/global-nav/ElfisGlobalNavigation'



type HomePlatformSidebarProps = {

  onNavigate?: () => void

  collapsed?: boolean

  onCollapsedChange?: (collapsed: boolean | ((prev: boolean) => boolean)) => void

}



export function HomePlatformSidebar({

  onNavigate,

  collapsed,

  onCollapsedChange,

}: HomePlatformSidebarProps) {

  return (

    <ElfisGlobalNavigation

      mode="sidebar"

      collapsed={collapsed}

      onCollapsedChange={onCollapsedChange}

      onNavigate={onNavigate}

    />

  )

}



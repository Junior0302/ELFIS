/**

 * Sidebar workspace plateforme — même config / composant que Home + drawer.

 */



import { ElfisGlobalNavigation } from '../platform-shell/global-nav/ElfisGlobalNavigation'



type PlatformNavigationProps = {

  onNavigate?: () => void

  collapsed?: boolean

  onCollapsedChange?: (collapsed: boolean | ((prev: boolean) => boolean)) => void

}



export function PlatformNavigation({

  onNavigate,

  collapsed,

  onCollapsedChange,

}: PlatformNavigationProps) {

  return (

    <ElfisGlobalNavigation

      mode="sidebar"

      collapsed={collapsed}

      onCollapsedChange={onCollapsedChange}

      onNavigate={onNavigate}

    />

  )

}



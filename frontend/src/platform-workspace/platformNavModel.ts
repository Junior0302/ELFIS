/**

 * Navigation ELFIS — surfaces partagées.

 * Dérivé de elfisNavigationConfig (source unique).

 */



import {

  ELFIS_NAVIGATION_CONFIG,

  filterElfisNavSections,

  flattenElfisNavItems,

  getMainNavSections,

} from '../platform-shell/global-nav/elfisNavigationConfig'



export type PlatformNavItem = {

  id: string

  label: string

  to: string

  end?: boolean

  permission?: string

  icon?: string

}



export const PLATFORM_NAV_ITEMS: readonly PlatformNavItem[] = getMainNavSections(

  ELFIS_NAVIGATION_CONFIG,

)

  .flatMap((section) => section.items)

  .filter((item): item is typeof item & { to: string } => Boolean(item.to))

  .map((item) => ({

    id: item.id,

    label: item.label,

    to: item.to,

    end: item.match === 'exact',

    permission: item.permission,

    icon: item.icon,

  }))



export function filterPlatformNav(

  items: readonly PlatformNavItem[],

  can: (permission?: string) => boolean,

): PlatformNavItem[] {

  const visible = new Set(

    flattenElfisNavItems(filterElfisNavSections(ELFIS_NAVIGATION_CONFIG, can)).map((i) => i.id),

  )

  return items.filter((item) => visible.has(item.id))

}



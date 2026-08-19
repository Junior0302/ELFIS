/**

 * Compatibilité — dérive du modèle plat historique depuis elfisNavigationConfig.

 * Préférer elfisNavigationConfig / ElfisGlobalNavigation pour le runtime.

 */



import {

  ELFIS_NAVIGATION_CONFIG,

  filterElfisNavSections,

  flattenElfisNavItems,

  isComptaPilotPath,

  isElfisNavItemActive,

  isSalesPilotPath,

  normalizeNavPath,

  type ElfisNavItemConfig,

} from './elfisNavigationConfig'



export type GlobalNavGroupId =

  | 'principal'

  | 'entreprise'

  | 'donnees'

  | 'plateforme'

  | 'outils'

  | 'support'

  | 'home'

  | 'platform'

  | 'apps'



export type GlobalNavItem = {

  id: string

  group: GlobalNavGroupId

  label: string

  to?: string

  action?: 'logout'

  permission?: string

  match?: 'exact' | 'prefix' | 'comptapilot' | 'salespilot' | 'hash'

  icon?: string

  destructive?: boolean

  disabled?: boolean

  badge?: string

}



function toLegacyItem(item: ElfisNavItemConfig, group: GlobalNavGroupId): GlobalNavItem {

  return {

    id: item.id,

    group,

    label: item.label,

    to: item.to,

    action: item.action,

    permission: item.permission,

    match: item.match,

    icon: item.icon,

    destructive: item.destructive,

    disabled: item.disabled,

    badge: item.badge,

  }

}



export const GLOBAL_NAV_ITEMS: readonly GlobalNavItem[] = ELFIS_NAVIGATION_CONFIG.flatMap(

  (section) => section.items.map((item) => toLegacyItem(item, section.id as GlobalNavGroupId)),

)



export const GLOBAL_NAV_GROUP_LABELS: Record<string, string | null> = Object.fromEntries(

  ELFIS_NAVIGATION_CONFIG.map((s) => [s.id, s.label]),

)



export {

  normalizeNavPath,

  isComptaPilotPath,

  isSalesPilotPath,

  flattenElfisNavItems,

}



export function isGlobalNavItemActive(pathname: string, item: GlobalNavItem, hash = ''): boolean {

  if (item.match === 'comptapilot') return isComptaPilotPath(pathname)

  if (item.match === 'salespilot') return isSalesPilotPath(pathname)

  return isElfisNavItemActive(pathname, hash, {

    id: item.id,

    label: item.label,

    icon: item.icon || 'home',

    to: item.to,

    action: item.action,

    permission: item.permission,

    match: item.match === 'hash' || item.match === 'exact' || item.match === 'prefix' ? item.match : 'prefix',

    destructive: item.destructive,

    disabled: item.disabled,

    badge: item.badge,

  })

}



export function filterGlobalNavItems(

  items: readonly GlobalNavItem[],

  can: (permission?: string) => boolean,

): GlobalNavItem[] {

  const visibleIds = new Set(

    filterElfisNavSections(ELFIS_NAVIGATION_CONFIG, can).flatMap((s) => s.items.map((i) => i.id)),

  )

  return items.filter((item) => visibleIds.has(item.id))

}



export function groupGlobalNavItems(items: readonly GlobalNavItem[]): {

  group: GlobalNavGroupId

  label: string | null

  items: GlobalNavItem[]

}[] {

  const order = ELFIS_NAVIGATION_CONFIG.map((s) => s.id)

  return order

    .map((group) => ({

      group: group as GlobalNavGroupId,

      label: GLOBAL_NAV_GROUP_LABELS[group] ?? null,

      items: items.filter((i) => i.group === group),

    }))

    .filter((g) => g.items.length > 0)

}



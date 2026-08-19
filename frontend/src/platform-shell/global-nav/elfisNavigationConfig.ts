/**

 * Configuration unique navigation ELFIS (sidebar + drawer).

 * Uniquement des destinations réelles — pas de routes inventées.

 */



export type ElfisNavMatch = 'exact' | 'prefix' | 'hash'



export type ElfisNavItemConfig = {

  id: string

  label: string

  icon: string

  to?: string

  action?: 'logout'

  permission?: string

  badge?: string

  destructive?: boolean

  disabled?: boolean

  match?: ElfisNavMatch

}



export type ElfisNavPlacement = 'main' | 'footer'



export type ElfisNavSectionConfig = {

  id: string

  label: string | null

  order: number

  placement: ElfisNavPlacement

  permission?: string

  badge?: string

  items: readonly ElfisNavItemConfig[]

}



/** Entrées cibles sans surface user dédiée — hors menu actif. */

export type ElfisNavBacklogEntry = {

  id: string

  label: string

  sectionId: string

  reason: string

}



export const ELFIS_NAV_BRAND = {

  name: 'ELFIS',

  subtitle: 'Plateforme',

  tagline: 'Le système d’exploitation de votre entreprise',

} as const



/**

 * Structure NAV.CORE.1 adaptée aux routes réelles.

 * Absents (backlog) : Contacts, Entreprises, Centre de santé, Journal.

 */

export const ELFIS_NAVIGATION_CONFIG: readonly ElfisNavSectionConfig[] = [

  {

    id: 'principal',

    label: 'Principal',

    order: 1,

    placement: 'main',

    items: [

      {

        id: 'home',

        label: 'Accueil',

        icon: 'home',

        to: '/home',

        match: 'exact',

      },

      {

        id: 'favorites',

        label: 'Favoris',

        icon: 'star',

        to: '/home#home-apps',

        match: 'hash',

      },

      {

        id: 'activity',

        label: 'Activité',

        icon: 'activity',

        to: '/home#home-activity',

        match: 'hash',

      },

    ],

  },

  {

    id: 'entreprise',

    label: 'Entreprise',

    order: 2,

    placement: 'main',

    items: [

      {

        id: 'organization',

        label: 'Organisation',

        icon: 'building',

        to: '/platform/organization',

        match: 'prefix',

      },

      {

        id: 'members',

        label: 'Membres et équipes',

        icon: 'users',

        to: '/platform/members',

        permission: 'users.manage',

        match: 'prefix',

      },

      {

        id: 'roles',

        label: 'Rôles et permissions',

        icon: 'shield',

        to: '/platform/members#roles',

        permission: 'users.manage',

        match: 'hash',

      },

    ],

  },

  {

    id: 'donnees',

    label: 'Données partagées',

    order: 3,

    placement: 'main',

    items: [

      {

        id: 'relations',

        label: 'Relations',

        icon: 'network',

        to: '/platform/relations',

        match: 'prefix',

      },

      {

        id: 'documents',

        label: 'Documents',

        icon: 'file',

        to: '/platform/documents',

        permission: 'documents.read',

        match: 'prefix',

      },

    ],

  },

  {

    id: 'plateforme',

    label: 'Plateforme',

    order: 4,

    placement: 'main',

    items: [

      {

        id: 'notifications',

        label: 'Notifications',

        icon: 'bell',

        to: '/notifications',

        match: 'prefix',

      },

      {

        id: 'communications',

        label: 'Communications',

        icon: 'mail',

        to: '/platform/communications',

        match: 'prefix',

      },

      {

        id: 'settings',

        label: 'Paramètres',

        icon: 'settings',

        to: '/platform/settings',

        match: 'prefix',

      },

    ],

  },

  {

    id: 'outils',

    label: 'Outils',

    order: 5,

    placement: 'main',

    items: [

      {

        id: 'intelligence',

        label: 'Intelligence ELFIS',

        icon: 'sparkles',

        to: '/platform/aura',

        permission: 'ai.analysis',

        match: 'prefix',

      },

      {

        id: 'search',

        label: 'Recherche globale',

        icon: 'search',

        to: '/search',

        match: 'prefix',

      },

    ],

  },

  {

    id: 'support',

    label: null,

    order: 6,

    placement: 'footer',

    items: [

      {

        id: 'help',

        label: 'Aide et support',

        icon: 'help-circle',

        to: '/home#home-status',

        match: 'hash',

      },

      {

        id: 'logout',

        label: 'Déconnexion',

        icon: 'log-out',

        action: 'logout',

        destructive: true,

      },

    ],

  },

]



export const ELFIS_NAV_BACKLOG: readonly ElfisNavBacklogEntry[] = [

  {

    id: 'contacts',

    label: 'Contacts',

    sectionId: 'donnees',

    reason: 'Pas de surface plateforme partagée ; Contacts SalesPilot (`/sales/contacts`) hors menu Core.',

  },

  {

    id: 'companies',

    label: 'Entreprises',

    sectionId: 'donnees',

    reason: 'Pas de surface plateforme partagée ; Entreprises SalesPilot (`/sales/companies`) hors menu Core.',

  },

  {

    id: 'health-center',

    label: 'Centre de santé',

    sectionId: 'outils',

    reason: 'Pas de page user ; health services réservé developer/admin.',

  },

  {

    id: 'journal',

    label: 'Journal',

    sectionId: 'outils',

    reason: 'Pas de journal plateforme ; journal Sales (`/sales/journal`) hors menu Core.',

  },

]



const COMPTA_PREFIXES = [

  '/dashboard',

  '/facturation',

  '/devis',

  '/clients',

  '/fournisseurs',

  '/documents',

  '/deposit',

  '/accounting',

  '/banque',

  '/finance',

  '/tva',

  '/cloture',

  '/copilote',

  '/intelligence',

  '/history',

  '/catalogue',

  '/activites',

  '/settings',

  '/reports',

  '/cockpit',

  '/migration',

  '/work-queue',

  '/decisions',

  '/search',

  '/result',

] as const



export function normalizeNavPath(pathname: string): string {

  const path = (pathname.split('?')[0].split('#')[0] || '/').replace(/\/+$/, '')

  return path || '/'

}



export function splitNavTarget(to: string | undefined): { path: string; hash: string | null } {

  if (!to) return { path: '', hash: null }

  const [pathPart, hashPart] = to.split('#')

  return {

    path: normalizeNavPath(pathPart || '/'),

    hash: hashPart ? hashPart : null,

  }

}



export function isComptaPilotPath(pathname: string): boolean {

  const path = normalizeNavPath(pathname)

  if (path.startsWith('/platform') || path === '/home' || path.startsWith('/home/')) return false

  if (path === '/sales' || path.startsWith('/sales/')) return false

  return COMPTA_PREFIXES.some((p) => path === p || path.startsWith(`${p}/`))

}



export function isSalesPilotPath(pathname: string): boolean {

  const path = normalizeNavPath(pathname)

  return path === '/sales' || path.startsWith('/sales/')

}



export function flattenElfisNavItems(

  sections: readonly ElfisNavSectionConfig[] = ELFIS_NAVIGATION_CONFIG,

): ElfisNavItemConfig[] {

  return sections.flatMap((section) => [...section.items])

}



export function filterElfisNavSections(

  sections: readonly ElfisNavSectionConfig[],

  can: (permission?: string) => boolean,

): ElfisNavSectionConfig[] {

  return sections

    .filter((section) => !section.permission || can(section.permission))

    .map((section) => ({

      ...section,

      items: section.items.filter((item) => {

        if (item.action === 'logout') return true

        if (item.disabled) return true

        if (!item.permission) return true

        return can(item.permission)

      }),

    }))

    .filter((section) => section.items.length > 0)

    .sort((a, b) => a.order - b.order)

}



export function getMainNavSections(

  sections: readonly ElfisNavSectionConfig[] = ELFIS_NAVIGATION_CONFIG,

): ElfisNavSectionConfig[] {

  return sections.filter((s) => s.placement === 'main')

}



export function getFooterNavSection(

  sections: readonly ElfisNavSectionConfig[] = ELFIS_NAVIGATION_CONFIG,

): ElfisNavSectionConfig | undefined {

  return sections.find((s) => s.placement === 'footer')

}



export function isElfisNavItemActive(

  pathname: string,

  hash: string,

  item: ElfisNavItemConfig,

): boolean {

  if (item.action || !item.to) return false

  const path = normalizeNavPath(pathname)

  // Hash vide, "#" seul, ou absent → pas de fragment « spécial »
  const currentHash = (hash || '').replace(/^#/, '')

  const target = splitNavTarget(item.to)



  switch (item.match) {

    case 'exact':

      // Accueil : pathname exact, sans hash de section (Favoris / Activité / Aide, etc.)
      return path === target.path && currentHash === ''

    case 'hash': {

      if (!target.hash) return false

      if (path !== target.path) return false

      return currentHash === target.hash

    }

    case 'prefix': {

      if (item.id === 'members' && currentHash === 'roles') return false

      return path === target.path || path.startsWith(`${target.path}/`)

    }

    default:

      return path === target.path && currentHash === ''

  }

}



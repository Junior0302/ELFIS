/**
 * Navigation Commercial (domaine métier) — NAV.DOMAIN.1 + parité accordion Finance.
 * Catégories dépliables + feuilles ; routes réelles uniquement.
 * Relations plateforme = accès contextuel (badge ELFIS), pas un second CRM.
 */

import { normalizePathname } from '../navModel'

export type SalesNavItem = {
  id: string
  label: string
  to: string
  /** Indication discrète (ex. lien contextuel plateforme) */
  badge?: string
}

export type SalesNavCategoryId =
  | 'dashboard'
  | 'prospection'
  | 'pipeline'
  | 'activites'
  | 'reporting'
  | 'clients'
  | 'parametres'

export type SalesNavCategory = {
  id: SalesNavCategoryId
  label: string
  /** Route d’entrée au clic sur la catégorie */
  to: string
  /** Clé icône (chemin présent dans navIcons) */
  iconTo: string
  children: readonly SalesNavItem[]
}

/**
 * Arborescence Commercial — même logique nested expand que Finance.
 * Entrées sans page réelle : omises (voir docs/domain-boundaries/10-commercial-nav-parity.md).
 */
export const salesNavCategories: readonly SalesNavCategory[] = [
  {
    id: 'dashboard',
    label: 'Tableau de bord',
    to: '/sales',
    iconTo: '/sales',
    children: [],
  },
  {
    id: 'prospection',
    label: 'Prospection',
    to: '/sales/leads',
    iconTo: '/sales/leads',
    children: [
      { id: 'leads', label: 'Prospects', to: '/sales/leads' },
      { id: 'companies', label: 'Entreprises', to: '/sales/companies' },
      { id: 'contacts', label: 'Contacts', to: '/sales/contacts' },
      { id: 'import', label: 'Import', to: '/sales/import' },
    ],
  },
  {
    id: 'pipeline',
    label: 'Pipeline',
    to: '/sales/pipeline',
    iconTo: '/sales/pipeline',
    children: [
      { id: 'pipeline-overview', label: 'Vue d’ensemble', to: '/sales/pipeline' },
      { id: 'proposals', label: 'Propositions', to: '/sales/proposals' },
    ],
  },
  {
    id: 'activites',
    label: 'Activités',
    to: '/sales/activities',
    iconTo: '/sales/activities',
    children: [
      { id: 'activities-overview', label: 'Vue d’ensemble', to: '/sales/activities' },
      { id: 'calendar', label: 'Calendrier', to: '/sales/calendar' },
      { id: 'tasks', label: 'Tâches', to: '/sales/tasks' },
      { id: 'journal', label: 'Journal', to: '/sales/journal' },
    ],
  },
  {
    id: 'reporting',
    label: 'Reporting',
    to: '/sales/reports',
    iconTo: '/sales/reports',
    children: [
      { id: 'reports-overview', label: 'Vue d’ensemble', to: '/sales/reports' },
      { id: 'intelligence', label: 'Performances', to: '/sales/intelligence' },
    ],
  },
  {
    id: 'clients',
    label: 'Clients',
    to: '/sales/companies',
    iconTo: '/sales/companies',
    children: [
      { id: 'clients-companies', label: 'Entreprises', to: '/sales/companies' },
      { id: 'clients-contacts', label: 'Contacts', to: '/sales/contacts' },
    ],
  },
  {
    id: 'parametres',
    label: 'Paramètres',
    to: '/sales/settings',
    iconTo: '/sales/settings',
    children: [{ id: 'settings-general', label: 'Général', to: '/sales/settings' }],
  },
] as const

/** Liste plate (compat tests / consumers) — dérivée des catégories. */
export const SALES_NAV_ITEMS: readonly SalesNavItem[] = salesNavCategories.flatMap((cat) =>
  cat.children.length === 0
    ? [{ id: cat.id, label: cat.label, to: cat.to }]
    : [...cat.children],
)

/** Sous-pages dont le préfixe chevauche d’autres enfants → match exact dans NavLink. */
export const SALES_NAV_EXACT = new Set([
  '/sales',
  '/sales/pipeline',
  '/sales/activities',
  '/sales/reports',
  '/sales/settings',
  '/sales/leads',
])

export function getSalesNavTos(): string[] {
  return [
    ...new Set(salesNavCategories.flatMap((cat) => [cat.to, ...cat.children.map((c) => c.to)])),
  ]
}

/** Surfaces plateforme interdites comme menu métier permanent (hors lien contextuel badge). */
export const SALES_FORBIDDEN_PLATFORM_PATHS = [
  '/platform/organization',
  '/platform/members',
  '/platform/settings',
  '/platform/documents',
  '/platform/communications',
  '/platform/relations',
  '/organisation',
  '/admin/equipe',
] as const

/** Correspondance chemin ↔ entrée Sales (plus long préfixe gagne ; /sales exact). */
export function salesPathMatches(pathname: string, to: string): boolean {
  const path = normalizePathname(pathname)
  const target = normalizePathname(to)
  if (path === target) return true
  if (target === '/sales') return false
  return path.startsWith(`${target}/`)
}

export function salesCategoryHasChildren(category: SalesNavCategory | undefined): boolean {
  return Boolean(category && category.children.length > 0)
}

/**
 * Catégorie active pour le pathname courant.
 * Sur égalité de score (ex. Entreprises dans Prospection + Clients),
 * préfère `clients` pour les routes entité partagées.
 */
export function findActiveSalesCategory(pathname: string): SalesNavCategory | undefined {
  const path = normalizePathname(pathname)
  let best: SalesNavCategory | undefined
  let bestScore = -1

  for (const category of salesNavCategories) {
    const candidates = [category.to, ...category.children.map((c) => c.to)]
    for (const to of candidates) {
      if (!salesPathMatches(path, to)) continue
      const score = normalizePathname(to).length
      if (score > bestScore) {
        bestScore = score
        best = category
      } else if (score === bestScore && category.id === 'clients' && best?.id === 'prospection') {
        best = category
      }
    }
  }

  return best
}

export function findActiveSalesLeaf(
  pathname: string,
  category: SalesNavCategory,
): SalesNavItem | undefined {
  const path = normalizePathname(pathname)
  let best: SalesNavItem | undefined
  let bestScore = -1
  for (const leaf of category.children) {
    if (!salesPathMatches(path, leaf.to)) continue
    const score = normalizePathname(leaf.to).length
    if (score > bestScore) {
      bestScore = score
      best = leaf
    }
  }
  return best
}

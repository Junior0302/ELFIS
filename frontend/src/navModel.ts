/**
 * Navigation Finance (domaine métier) — NAV.DOMAIN.1.
 * Surfaces transversales (Organisation, Relations globales, Vault générique,
 * Communications, équipe plateforme) → ELFIS uniquement.
 * Routes existantes conservées ; pas de fausses entrées.
 */

export type NavCategoryId =
  | 'dashboard'
  | 'ventes'
  | 'pilotage'
  | 'comptabilite'
  | 'documents'
  | 'tiers'
  | 'assistant'
  | 'parametres'

export type NavLeaf = {
  id: string
  to: string
  label: string
  permission?: string
  /** Indication discrète (ex. lien contextuel plateforme) */
  badge?: string
}

export type NavCategory = {
  id: NavCategoryId
  label: string
  /** Route d’entrée au clic sur la catégorie */
  to: string
  /** Clé icône (chemin déjà présent dans navIcons) */
  iconTo: string
  permission?: string
  /** Vide = pas de sous-menu (ex. Tableau de bord) */
  children: readonly NavLeaf[]
}

/**
 * Arborescence Finance — routes réelles uniquement.
 * Search & Notifications restent en topbar.
 */
export const navCategories: readonly NavCategory[] = [
  {
    id: 'dashboard',
    label: 'Tableau de bord',
    to: '/dashboard',
    iconTo: '/dashboard',
    permission: 'invoice.read',
    children: [],
  },
  {
    id: 'ventes',
    label: 'Facturation',
    to: '/facturation',
    iconTo: '/facturation',
    permission: 'invoice.read',
    children: [
      {
        id: 'facturation-overview',
        to: '/facturation',
        label: 'Vue d’ensemble',
        permission: 'invoice.read',
      },
      {
        id: 'facturation-documents',
        to: '/facturation/documents',
        label: 'Documents',
        permission: 'invoice.read',
      },
      {
        id: 'devis',
        to: '/devis',
        label: 'Devis',
        permission: 'invoice.read',
      },
      {
        id: 'catalogue',
        to: '/catalogue',
        label: 'Catalogue',
        permission: 'invoice.read',
      },
      {
        id: 'activites',
        to: '/activites',
        label: 'Activité',
        permission: 'invoice.read',
      },
    ],
  },
  {
    id: 'pilotage',
    label: 'Finance',
    to: '/finance',
    iconTo: '/finance',
    permission: 'invoice.read',
    children: [
      { id: 'finance', to: '/finance', label: 'Vue d’ensemble', permission: 'invoice.read' },
      { id: 'tva', to: '/tva', label: 'TVA', permission: 'invoice.read' },
      { id: 'cloture', to: '/cloture', label: 'Clôture', permission: 'invoice.read' },
      { id: 'cockpit', to: '/cockpit', label: 'Centre opérationnel', permission: 'invoice.read' },
      { id: 'reports', to: '/reports', label: 'Rapports', permission: 'invoice.read' },
    ],
  },
  {
    id: 'comptabilite',
    label: 'Comptabilité',
    to: '/accounting',
    iconTo: '/accounting',
    permission: 'ai.analysis',
    children: [
      { id: 'accounting-hub', to: '/accounting', label: 'Vue d’ensemble', permission: 'ai.analysis' },
      {
        id: 'accounting-proposals',
        to: '/accounting/proposals',
        label: 'Propositions',
        permission: 'ai.analysis',
      },
      {
        id: 'accounting-engine',
        to: '/accounting/engine',
        label: 'Journaux',
        permission: 'ai.analysis',
      },
      { id: 'history', to: '/history', label: 'Historique', permission: 'invoice.read' },
    ],
  },
  {
    id: 'documents',
    label: 'Documents comptables',
    to: '/documents',
    iconTo: '/documents',
    permission: 'documents.read',
    children: [
      {
        id: 'documents-list',
        to: '/documents',
        label: 'Documents comptables',
        permission: 'documents.read',
      },
      { id: 'deposit', to: '/deposit', label: 'Importer', permission: 'invoice.create' },
      {
        id: 'migration',
        to: '/migration',
        label: 'Centre d’import',
        permission: 'migration_center.read',
      },
    ],
  },
  {
    id: 'tiers',
    label: 'Clients & fournisseurs',
    to: '/clients',
    iconTo: '/clients',
    permission: 'invoice.read',
    children: [
      {
        id: 'clients',
        to: '/clients',
        label: 'Clients',
        permission: 'invoice.read',
      },
      {
        id: 'fournisseurs',
        to: '/fournisseurs',
        label: 'Fournisseurs',
        permission: 'invoice.read',
      },
    ],
  },
  {
    id: 'assistant',
    label: 'Assistance',
    to: '/copilote',
    iconTo: '/copilote',
    permission: 'ai.analysis',
    children: [
      { id: 'copilote', to: '/copilote', label: 'Assistant financier', permission: 'ai.analysis' },
      { id: 'signaux', to: '/intelligence', label: 'Signaux', permission: 'ai.analysis' },
    ],
  },
  {
    id: 'parametres',
    label: 'Paramètres',
    to: '/settings',
    iconTo: '/settings',
    children: [
      {
        id: 'settings',
        to: '/settings',
        label: 'Paramètres Finance',
      },
    ],
  },
] as const

export function normalizePathname(pathname: string): string {
  const trimmed = pathname.replace(/\/+$/, '')
  return trimmed || '/'
}

/** Correspondance chemin ↔ entrée (plus long préfixe gagne). */
export function pathMatches(pathname: string, to: string): boolean {
  const path = normalizePathname(pathname)
  const target = normalizePathname(to)
  if (path === target) return true
  if (target === '/dashboard') return false
  if (target === '/home') return false
  return path.startsWith(`${target}/`)
}

export function filterLeavesByPermission(
  leaves: readonly NavLeaf[],
  can: (permission?: string) => boolean,
): NavLeaf[] {
  return leaves.filter((leaf) => can(leaf.permission))
}

export function isCategoryVisible(
  category: NavCategory,
  can: (permission?: string) => boolean,
): boolean {
  if (!can(category.permission)) return false
  if (category.children.length === 0) return true
  return filterLeavesByPermission(category.children, can).length > 0
}

export function getVisibleCategories(can: (permission?: string) => boolean): NavCategory[] {
  return navCategories.filter((cat) => isCategoryVisible(cat, can))
}

/** Toutes les cibles de navigation Finance (catégories + feuilles). */
export function getFinanceNavTos(): string[] {
  return [
    ...new Set(navCategories.flatMap((cat) => [cat.to, ...cat.children.map((c) => c.to)])),
  ]
}

/** Catégorie active pour le pathname courant. */
export function findActiveCategory(pathname: string): NavCategory | undefined {
  const path = normalizePathname(pathname)
  let best: NavCategory | undefined
  let bestScore = -1

  for (const category of navCategories) {
    const candidates = [category.to, ...category.children.map((c) => c.to)]
    for (const to of candidates) {
      if (!pathMatches(path, to)) continue
      const score = normalizePathname(to).length
      if (score > bestScore) {
        bestScore = score
        best = category
      }
    }
  }

  return best
}

/** Sous-page active (plus long match). */
export function findActiveLeaf(pathname: string, category: NavCategory): NavLeaf | undefined {
  const path = normalizePathname(pathname)
  let best: NavLeaf | undefined
  let bestScore = -1
  for (const leaf of category.children) {
    if (!pathMatches(path, leaf.to)) continue
    const score = normalizePathname(leaf.to).length
    if (score > bestScore) {
      bestScore = score
      best = leaf
    }
  }
  return best
}

export function categoryHasChildren(category: NavCategory | undefined): boolean {
  return Boolean(category && category.children.length > 0)
}

/** @deprecated alias Sprint 1 — préférer categoryHasChildren */
export function categoryHasSubnav(category: NavCategory | undefined): boolean {
  return categoryHasChildren(category)
}

/** Official product categories — single source of truth. */

import type { ProductCategory, ProductCategoryId } from '../types'

export const PRODUCT_CATEGORIES: readonly ProductCategory[] = [
  {
    id: 'platform',
    label: 'Plateforme',
    description: 'Socle central ELFIS : compte, organisation, sécurité et services partagés.',
    iconKey: 'category-platform',
    order: 1,
    status: 'active',
  },
  {
    id: 'finance',
    label: 'Finance et comptabilité',
    description: 'Comptabilité, facturation, trésorerie et pilotage financier.',
    iconKey: 'category-finance',
    order: 2,
    status: 'active',
  },
  {
    id: 'sales',
    label: 'Ventes et relation client',
    description: 'Pipeline commercial, clients, devis et suivi des opportunités.',
    iconKey: 'category-sales',
    order: 3,
    status: 'coming_soon',
  },
  {
    id: 'documents',
    label: 'Documents et connaissance',
    description: 'Coffre documentaire, OCR, recherche et classement intelligent.',
    iconKey: 'category-documents',
    order: 4,
    status: 'coming_soon',
  },
  {
    id: 'people',
    label: 'Ressources humaines',
    description: 'Collaborateurs, documents RH, absences et processus internes.',
    iconKey: 'category-people',
    order: 5,
    status: 'coming_soon',
  },
  {
    id: 'legal',
    label: 'Juridique et conformité',
    description: 'Contrats, échéances, conformité et documents légaux.',
    iconKey: 'category-legal',
    order: 6,
    status: 'coming_soon',
  },
  {
    id: 'operations',
    label: 'Opérations et logistique',
    description: 'Inventaire, mouvements, approvisionnements et alertes opérationnelles.',
    iconKey: 'category-operations',
    order: 7,
    status: 'coming_soon',
  },
  {
    id: 'marketing',
    label: 'Marketing et croissance',
    description: 'Campagnes, contenus, canaux et mesure de performance.',
    iconKey: 'category-marketing',
    order: 8,
    status: 'coming_soon',
  },
  {
    id: 'projects',
    label: 'Projets et collaboration',
    description: 'Missions, tâches, délais, budgets et rentabilité des projets.',
    iconKey: 'category-projects',
    order: 9,
    status: 'coming_soon',
  },
  {
    id: 'support',
    label: 'Support et service client',
    description: 'Demandes, tickets, priorités et historique du service client.',
    iconKey: 'category-support',
    order: 10,
    status: 'coming_soon',
  },
] as const

const BY_ID: Record<ProductCategoryId, ProductCategory> = PRODUCT_CATEGORIES.reduce(
  (acc, category) => {
    acc[category.id] = category
    return acc
  },
  {} as Record<ProductCategoryId, ProductCategory>,
)

export function getCategoryById(id: ProductCategoryId): ProductCategory {
  return BY_ID[id]
}

export function isKnownCategoryId(value: string): value is ProductCategoryId {
  return value in BY_ID
}

export function listCategories(): ProductCategory[] {
  return [...PRODUCT_CATEGORIES].sort((a, b) => a.order - b.order)
}

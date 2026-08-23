/**
 * Modèle public Homepage V2 — indépendant du WORKSPACE_REGISTRY.
 * Banque, Comptabilité, Facturation et Paramètres ne sont pas des Espaces autonomes.
 */

export type PublicSpaceId = 'finance' | 'commercial' | 'documents'

export type PublicSpace = {
  id: PublicSpaceId
  label: string
  description: string
  icon: 'trending-up' | 'handshake' | 'file-text'
  accent: string
  accentSoft: string
  modules: readonly string[]
}

export type UpcomingPublicSpace = {
  id: string
  label: string
  description: string
}

export const PUBLIC_OPEN_SPACES: readonly PublicSpace[] = [
  {
    id: 'finance',
    label: 'Finance',
    description: 'Pilotage financier et trésorerie.',
    icon: 'trending-up',
    accent: '#16A34A',
    accentSoft: '#ECFDF5',
    modules: ['Trésorerie', 'Échéances', 'Documents'],
  },
  {
    id: 'commercial',
    label: 'Commercial',
    description: 'Ventes et relation client.',
    icon: 'handshake',
    accent: '#2563EB',
    accentSoft: '#EFF6FF',
    modules: ['Pipeline', 'Contacts', 'Relances'],
  },
  {
    id: 'documents',
    label: 'Documents',
    description: 'Centralisation et intelligence documentaire.',
    icon: 'file-text',
    accent: '#7C3AED',
    accentSoft: '#F5F3FF',
    modules: ['Classement', 'Recherche', 'Validation'],
  },
] as const

/** Roadmap marketing — 8 Espaces à venir. Pas le catalogue technique. */
export const PUBLIC_UPCOMING_SPACES: readonly UpcomingPublicSpace[] = [
  { id: 'achats', label: 'Achats', description: 'Gestion des achats et des fournisseurs.' },
  {
    id: 'stock',
    label: 'Stock & Inventaire',
    description: 'Suivi des stocks, mouvements et inventaires.',
  },
  {
    id: 'logistique',
    label: 'Logistique',
    description: 'Organisation des expéditions et des opérations logistiques.',
  },
  {
    id: 'rh',
    label: 'Ressources Humaines',
    description: 'Gestion des collaborateurs, équipes et informations RH.',
  },
  {
    id: 'planning',
    label: 'Planning',
    description: 'Planification du travail, des ressources et des activités.',
  },
  {
    id: 'projets',
    label: 'Projets',
    description: 'Organisation des projets, tâches et responsabilités.',
  },
  {
    id: 'conformite',
    label: 'Conformité',
    description: 'Suivi des obligations, contrôles et processus de conformité.',
  },
  {
    id: 'rse',
    label: 'RSE',
    description: 'Pilotage progressif des engagements sociaux et environnementaux.',
  },
] as const

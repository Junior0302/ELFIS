/**
 * Hub Espaces ELFIS — types domaine métier (BRAND.ELFIS.1).
 * Routes / moteurs inchangés ; terminologie UX = espaces, pas applications.
 */

import type { ProductId } from '../design-system/types'
import type { LauncherProductState } from './launcher.types'

export type SpaceId =
  | 'finance'
  | 'commercial'
  | 'documents'
  | 'achats'
  | 'stock'
  | 'logistique'
  | 'rh'
  | 'planning'
  | 'projets'
  | 'banque'
  | 'comptabilite'
  | 'facturation'
  | 'conformite'
  | 'rse'
  | 'parametres'

export type SpaceShortcut = {
  id: string
  label: string
  to: string
}

export type SpaceDefinition = {
  id: SpaceId
  title: string
  description: string
  /** Clé icône Lucide (maquette espaces métiers). */
  icon: string
  /** Accent discret carte (navy shell + teinte domaine). */
  accent: string
  /** Fond pastel icône. */
  accentSoft?: string
  /** Signature moteur interne — non affichée en Phase A. */
  engineLabel: string | null
  /** Produit moteur associé (lastProduct / thème) — null si aucun. */
  engineProductId: ProductId | null
  /** Route d’entrée réelle SPA, ou null → badge À venir. */
  entryRoute: string | null
  shortcuts: readonly SpaceShortcut[]
  /** Alias recherche métier (facture, TVA, pipeline…). */
  searchAliases: readonly string[]
  capabilities: readonly string[]
}

export type ResolvedSpace = {
  space: SpaceDefinition
  state: LauncherProductState
  canOpen: boolean
  route?: string
  label: string
  reason?: string
  isLastUsed?: boolean
  /** Horodatage lastProduct si données réelles. */
  lastActivityAt?: string | null
}

export type SpaceSections = {
  available: ResolvedSpace[]
  comingSoon: ResolvedSpace[]
}

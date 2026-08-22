/**
 * WorkspaceConfig — métadonnées d’espace métier ELFIS.
 * Compose Product Registry (moteurs) + navigation locale.
 * Ne remplace pas Product Registry : référence engineProductId.
 */

import type { ProductId } from '../design-system/types'
import type { SpaceId } from '../app-launcher/spaces.types'

/** Identifiants workspace = SpaceId launcher (même domaine UX). */
export type WorkspaceId = SpaceId

export type WorkspaceAvailability = 'available' | 'coming_soon' | 'locked'

/**
 * Politique d’état actif (Phase 3 sidebar).
 * - prefix / exact : match classique
 * - primary : gagne quand plusieurs feuilles partagent le même path
 * - contextual : même path qu’un sibling primary — ne s’active jamais en même temps
 *   (ex. Trésorerie → /finance tant qu’il n’y a pas de sous-vue dédiée)
 */
export type WorkspaceNavActivePolicy = 'prefix' | 'exact' | 'primary' | 'contextual'

export type WorkspaceNavLeaf = {
  id: string
  label: string
  /** Route SPA réelle uniquement — jamais fictive. */
  to: string
  permission?: string
  badge?: string
  activePolicy?: WorkspaceNavActivePolicy
}

export type WorkspaceNavGroup = {
  id: string
  label: string
  /** Route d’entrée au clic sur le groupe (si pas de children, item simple). */
  to: string
  /** Clé icône compatible navIcons / Lucide (chemin ou id). */
  iconKey: string
  permission?: string
  children: readonly WorkspaceNavLeaf[]
}

export type WorkspaceAccentTokens = {
  /** Accent principal officiel (menu actif, CTA, tabs…). */
  primary: string
  /** Fond léger (carte active, soft highlight). */
  soft: string
  /** Hover / pressed / texte sur fond clair. */
  dark: string
  /** Nom CSS custom property --workspace-*. */
  cssVar: string
  softCssVar: string
  darkCssVar: string
}

export type WorkspaceConfig = {
  id: WorkspaceId
  label: string
  description: string
  /** Signature moteur (affichage launcher). */
  engineLabel: string | null
  /** Product Registry id — null si aucun moteur. */
  engineProductId: ProductId | null
  /** Clé icône Lucide / registry (ex. chart-column, handshake, file-text). */
  icon: string
  accent: WorkspaceAccentTokens
  /** Route d’entrée SPA, ou null → À venir. */
  rootPath: string | null
  availability: WorkspaceAvailability
  /** Raccourcis launcher (routes réelles). */
  shortcuts: readonly { id: string; label: string; to: string }[]
  searchAliases: readonly string[]
  capabilities: readonly string[]
  /** Groupes pour future WorkspaceSidebar — vide si coming_soon. */
  navigationGroups: readonly WorkspaceNavGroup[]
}

export type WorkspaceRegistry = readonly WorkspaceConfig[]

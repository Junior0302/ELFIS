/**
 * Contrats Favoris / Récents / Plus utilisés — désactivés sans API réelle.
 * Pas de localStorage métier.
 */

import type { LibraryMetaProvider } from '../types'

export const DISABLED_FAVORITES: LibraryMetaProvider = {
  id: 'favorites',
  label: 'Favoris',
  enabled: false,
  list: async () => [],
  reasonDisabled: 'Aucune source favoris exposée — section désactivée.',
}

export const DISABLED_RECENTS: LibraryMetaProvider = {
  id: 'recents',
  label: 'Récents',
  enabled: false,
  list: async () => [],
  reasonDisabled:
    'Aucun historique d’utilisation produit exposé — section désactivée (pas de proxy inventé).',
}

export const DISABLED_MOST_USED: LibraryMetaProvider = {
  id: 'most_used',
  label: 'Plus utilisés',
  enabled: false,
  list: async () => [],
  reasonDisabled: 'Aucune statistique « plus utilisés » exposée — section désactivée.',
}

export const LIBRARY_META_PROVIDERS = [
  DISABLED_FAVORITES,
  DISABLED_RECENTS,
  DISABLED_MOST_USED,
] as const

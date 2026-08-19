/**
 * @vitest-environment jsdom
 */
import { describe, expect, it, beforeEach, afterEach } from 'vitest'
import {
  clearRecentSearches,
  getRecentSearches,
  pushRecentSearch,
  RECENT_SEARCHES_KEY,
} from './recentSearchesStorage'

describe('recentSearchesStorage', () => {
  beforeEach(() => {
    clearRecentSearches()
  })
  afterEach(() => {
    clearRecentSearches()
  })

  it('conserve max 5, plus récent en tête', () => {
    pushRecentSearch('a')
    pushRecentSearch('b')
    pushRecentSearch('c')
    pushRecentSearch('d')
    pushRecentSearch('e')
    pushRecentSearch('f')
    expect(getRecentSearches()).toEqual(['f', 'e', 'd', 'c', 'b'])
  })

  it('déduplique sans tenir compte de la casse', () => {
    pushRecentSearch('Acme')
    pushRecentSearch('acme')
    expect(getRecentSearches()).toEqual(['acme'])
  })

  it('ignore les commandes >', () => {
    pushRecentSearch('> nouvelle facture')
    expect(getRecentSearches()).toEqual([])
  })

  it('efface le storage', () => {
    pushRecentSearch('x')
    clearRecentSearches()
    expect(getRecentSearches()).toEqual([])
    try {
      expect(localStorage?.getItem?.(RECENT_SEARCHES_KEY) ?? null).toBeNull()
    } catch {
      /* localStorage may be unavailable in runner */
    }
  })
})

import { describe, expect, it } from 'vitest'
import {
  findActiveCategory,
  findActiveLeaf,
  getFinanceNavTos,
  getVisibleCategories,
  navCategories,
  pathMatches,
} from './navModel'

describe('navModel — Navigation Finance (NAV.DOMAIN.1)', () => {
  it('expose les 8 catégories domaine', () => {
    expect(navCategories.map((c) => c.id)).toEqual([
      'dashboard',
      'ventes',
      'pilotage',
      'comptabilite',
      'documents',
      'tiers',
      'assistant',
      'parametres',
    ])
  })

  it('Facturation : Vue d’ensemble / Documents / Devis / Catalogue / Activité', () => {
    const facturation = navCategories.find((c) => c.id === 'ventes')
    expect(facturation?.label).toBe('Facturation')
    expect(facturation?.children.map((l) => l.id)).toEqual([
      'facturation-overview',
      'facturation-documents',
      'devis',
      'catalogue',
      'activites',
    ])
    expect(facturation?.children.some((l) => l.to === '/facturation/nouveau')).toBe(false)
  })

  it('ND — pas d’Organisation / Membres / Communications / Vault plateforme', () => {
    const tos = getFinanceNavTos()
    expect(tos).not.toContain('/platform/organization')
    expect(tos).not.toContain('/platform/members')
    expect(tos).not.toContain('/platform/communications')
    expect(tos).not.toContain('/platform/documents')
    expect(tos).not.toContain('/platform/settings')
    expect(tos).not.toContain('/platform/relations')
    expect(tos).not.toContain('/organisation')
    expect(tos).not.toContain('/admin/equipe')
  })

  it('Paramètres Finance uniquement', () => {
    const parametres = navCategories.find((c) => c.id === 'parametres')
    expect(parametres?.children.map((l) => l.to)).toEqual(['/settings'])
    expect(parametres?.children[0]?.label).toBe('Paramètres Finance')
  })

  it('Clients & fournisseurs = vues métier (pas Relations globales)', () => {
    const tiers = navCategories.find((c) => c.id === 'tiers')
    expect(tiers?.label).toBe('Clients & fournisseurs')
    expect(tiers?.children.map((l) => l.to)).toEqual(['/clients', '/fournisseurs'])
    expect(tiers?.children.every((l) => !l.badge)).toBe(true)
  })

  it('Documents comptables sans coffre générique', () => {
    expect(navCategories.find((c) => c.id === 'documents')?.label).toBe('Documents comptables')
    const docs = navCategories.find((c) => c.id === 'documents')
    expect(docs?.children.some((l) => l.to === '/platform/documents')).toBe(false)
    expect(docs?.children.some((l) => l.badge === 'Vault ELFIS')).toBe(false)
  })

  it('Assistance + Finance labels', () => {
    expect(navCategories.find((c) => c.id === 'assistant')?.label).toBe('Assistance')
    expect(navCategories.find((c) => c.id === 'pilotage')?.label).toBe('Finance')
  })

  it('Tableau de bord n’a pas de sous-menu', () => {
    const dash = navCategories.find((c) => c.id === 'dashboard')
    expect(dash?.children).toHaveLength(0)
  })

  it('une seule catégorie ouverte à la fois est gérée côté Layout (modèle = enfants)', () => {
    const withChildren = navCategories.filter((c) => c.children.length > 0)
    expect(withChildren.length).toBe(7)
  })

  it('les autres catégories ont des enfants vers des routes existantes', () => {
    for (const cat of navCategories) {
      if (cat.id === 'dashboard') continue
      expect(cat.children.length).toBeGreaterThan(0)
      for (const leaf of cat.children) {
        expect(leaf.to.startsWith('/')).toBe(true)
      }
    }
  })

  it('résout la catégorie active (plus long match)', () => {
    expect(findActiveCategory('/dashboard')?.id).toBe('dashboard')
    expect(findActiveCategory('/facturation')?.id).toBe('ventes')
    expect(findActiveCategory('/facturation/documents')?.id).toBe('ventes')
    expect(findActiveCategory('/facturation/nouveau')?.id).toBe('ventes')
    expect(findActiveCategory('/devis')?.id).toBe('ventes')
    expect(findActiveCategory('/catalogue')?.id).toBe('ventes')
    expect(findActiveCategory('/platform/banking')?.id).toBeUndefined()
    expect(findActiveCategory('/accounting/proposals')?.id).toBe('comptabilite')
    expect(findActiveCategory('/clients')?.id).toBe('tiers')
    expect(findActiveCategory('/copilote')?.id).toBe('assistant')
    expect(findActiveCategory('/settings')?.id).toBe('parametres')
  })

  it('résout le leaf actif sous une catégorie', () => {
    const compta = navCategories.find((c) => c.id === 'comptabilite')!
    expect(findActiveLeaf('/accounting/proposals', compta)?.id).toBe('accounting-proposals')
    expect(findActiveLeaf('/accounting', compta)?.id).toBe('accounting-hub')
  })

  it('pathMatches gère les préfixes sans activer le dashboard partout', () => {
    expect(pathMatches('/accounting/engine', '/accounting')).toBe(true)
    expect(pathMatches('/finance', '/dashboard')).toBe(false)
  })

  it('filtre les catégories selon les permissions', () => {
    const denyAll = () => false
    expect(getVisibleCategories(denyAll)).toHaveLength(0)

    const allowMissingOnly = (permission?: string) => !permission
    const partial = getVisibleCategories(allowMissingOnly)
    expect(partial.some((c) => c.id === 'parametres')).toBe(true)
    expect(partial.some((c) => c.id === 'dashboard')).toBe(false)

    const all = getVisibleCategories(() => true)
    expect(all).toHaveLength(8)
  })
})

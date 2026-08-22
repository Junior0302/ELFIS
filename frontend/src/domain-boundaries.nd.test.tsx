/**
 * NAV.DOMAIN.1 — ND01–ND30 séparation plateforme / domaines métier
 * @vitest-environment jsdom
 */
import { afterEach, describe, expect, it } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter, Navigate, Route, Routes } from 'react-router-dom'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { getFinanceNavTos, navCategories } from './navModel'
import {
  getSalesNavTos,
  SALES_FORBIDDEN_PLATFORM_PATHS,
  SALES_NAV_ITEMS,
  salesNavCategories,
} from './sales/salesNavModel'
import { ProductIndicator } from './platform-shell/ProductIndicator'

afterEach(() => {
  cleanup()
})

const APP_TSX = readFileSync(resolve(__dirname, 'App.tsx'), 'utf8')
const financeTos = getFinanceNavTos()
const salesTos = getSalesNavTos()

describe('NAV.DOMAIN.1 — Finance nav (ND01–ND14)', () => {
  it('ND01 Organisation absent Finance', () => {
    expect(financeTos.some((t) => /organization|organisation/i.test(t))).toBe(false)
  })

  it('ND02 Relations globales absentes Finance', () => {
    expect(financeTos).not.toContain('/platform/relations')
    expect(navCategories.map((c) => c.id)).not.toContain('relations')
  })

  it('ND03 paramètres plateforme absents Finance', () => {
    expect(financeTos).not.toContain('/platform/settings')
    expect(financeTos).not.toContain('/platform/members')
    expect(financeTos).not.toContain('/platform/communications')
  })

  it('ND04 documents génériques absents Finance', () => {
    expect(financeTos).not.toContain('/platform/documents')
    expect(financeTos).not.toContain('/vault')
  })

  it('ND05 paramètres Finance présents', () => {
    const params = navCategories.find((c) => c.id === 'parametres')
    expect(params?.children.some((l) => l.to === '/settings' && l.label === 'Paramètres Finance')).toBe(
      true,
    )
  })

  it('ND06 clients métier accessibles', () => {
    expect(financeTos).toContain('/clients')
  })

  it('ND07 fournisseurs métier accessibles', () => {
    expect(financeTos).toContain('/fournisseurs')
  })

  it('ND08 lien ELFIS Relations (pages métier)', () => {
    const clients = readFileSync(resolve(__dirname, 'pages/ClientsPage.tsx'), 'utf8')
    const fournisseurs = readFileSync(resolve(__dirname, 'pages/FournisseursPage.tsx'), 'utf8')
    expect(clients).toMatch(/Données issues d’ELFIS Relations/)
    expect(clients).toMatch(/\/platform\/relations\?tab=customer/)
    expect(fournisseurs).toMatch(/Données issues d’ELFIS Relations/)
    expect(fournisseurs).toMatch(/\/platform\/relations\?tab=supplier/)
  })

  it('ND09 lien ELFIS Organisation (contextuel FCC)', () => {
    const fcc = readFileSync(
      resolve(__dirname, 'comptapilot/financial-command-center/FinancialCommandCenter.tsx'),
      'utf8',
    )
    expect(fcc).toMatch(/Compléter dans ELFIS/)
    expect(fcc).toMatch(/\/platform\/organization/)
  })

  it('ND10 documents comptables présents', () => {
    expect(financeTos).toContain('/documents')
    expect(navCategories.find((c) => c.id === 'documents')?.label).toBe('Documents comptables')
  })

  it('ND11 facturation présente', () => {
    expect(financeTos).toContain('/facturation')
    expect(financeTos).toContain('/facturation/documents')
    expect(financeTos).toContain('/devis')
  })

  it('ND12 banque présente', () => {
    expect(financeTos).toContain('/banque')
  })

  it('ND13 TVA présente', () => {
    expect(financeTos).toContain('/tva')
  })

  it('ND14 comptabilité présente', () => {
    expect(financeTos).toContain('/accounting')
    expect(financeTos).toContain('/accounting/proposals')
    expect(financeTos).toContain('/accounting/engine')
  })
})

describe('NAV.DOMAIN.1 — Commercial nav (ND15–ND24)', () => {
  it('ND15 Organisation absent Commercial', () => {
    for (const p of SALES_FORBIDDEN_PLATFORM_PATHS) {
      if (/organization|organisation/i.test(p)) {
        expect(salesTos).not.toContain(p)
      }
    }
  })

  it('ND16 Relations = accès contextuel Clients (badge ELFIS), pas org/settings', () => {
    expect(salesTos).toContain('/platform/relations')
    const clients = salesNavCategories.find((c) => c.id === 'clients')
    const relations = clients?.children.find((l) => l.to === '/platform/relations')
    expect(relations?.badge).toBe('ELFIS')
    expect(salesTos).not.toContain('/platform/organization')
    expect(salesTos).not.toContain('/platform/settings')
  })

  it('ND17 paramètres plateforme absents Commercial', () => {
    expect(salesTos).not.toContain('/platform/settings')
    expect(salesTos).not.toContain('/platform/members')
  })

  it('ND18 paramètres Commercial présents', () => {
    expect(salesTos).toContain('/sales/settings')
    expect(SALES_NAV_ITEMS.some((i) => i.label === 'Général' && i.to === '/sales/settings')).toBe(
      true,
    )
  })

  it('ND19 prospects présents', () => {
    expect(salesTos).toContain('/sales/leads')
  })

  it('ND20 entreprises présentes', () => {
    expect(salesTos).toContain('/sales/companies')
  })

  it('ND21 contacts présents', () => {
    expect(salesTos).toContain('/sales/contacts')
  })

  it('ND22 pipeline présent', () => {
    expect(salesTos).toContain('/sales/pipeline')
  })

  it('ND23 propositions présentes', () => {
    expect(salesTos).toContain('/sales/proposals')
  })

  it('ND24 données Relations partagées (copy Sales)', () => {
    const companies = readFileSync(resolve(__dirname, 'pages/sales/SalesCompaniesPage.tsx'), 'utf8')
    expect(companies).toMatch(/ELFIS Relations/)
    expect(salesNavCategories.map((c) => c.id)).toEqual([
      'dashboard',
      'prospection',
      'pipeline',
      'activites',
      'reporting',
      'clients',
      'parametres',
    ])
  })
})

describe('NAV.DOMAIN.1 — routes & chrome (ND25–ND28)', () => {
  it('ND25 routes historiques sûres', () => {
    render(
      <MemoryRouter initialEntries={['/organisation']}>
        <Routes>
          <Route path="organisation" element={<Navigate to="/platform/organization" replace />} />
          <Route path="platform/organization" element={<div>Org OK</div>} />
        </Routes>
      </MemoryRouter>,
    )
    expect(screen.getByText('Org OK')).toBeInTheDocument()
    expect(APP_TSX).toMatch(/path="organisation"/)
    expect(APP_TSX).toMatch(/path="team"/)
    expect(APP_TSX).toMatch(/path="quotes"/)
  })

  it('ND26 deep links domaine + headers Finance/Commercial', () => {
    render(
      <MemoryRouter>
        <ProductIndicator productId="comptapilot" />
        <ProductIndicator productId="salespilot" />
      </MemoryRouter>,
    )
    expect(screen.getByText('Finance')).toBeInTheDocument()
    expect(screen.queryByText('Moteur ComptaPilot')).toBeNull()
    expect(screen.getByText('Commercial')).toBeInTheDocument()
    expect(screen.queryByText('Moteur SalesPilot')).toBeNull()
    expect(APP_TSX).toContain('path="sales/pipeline"')
    expect(APP_TSX).toContain('path="facturation"')
  })

  it('ND27 refresh — chemins exacts nav stables', () => {
    expect(financeTos).toContain('/settings')
    expect(salesTos).toContain('/sales')
    expect(new Set(financeTos).size).toBe(financeTos.length)
  })

  it('ND28 permissions — feuilles Finance gardent permission optionnelle', () => {
    const withPerm = navCategories.flatMap((c) => c.children).filter((l) => l.permission)
    expect(withPerm.length).toBeGreaterThan(5)
    expect(navCategories.find((c) => c.id === 'parametres')?.children[0]?.permission).toBeUndefined()
  })
})

describe('NAV.DOMAIN.1 — ND29–ND30 placeholders (exécutés hors suite via scripts)', () => {
  it('ND29 TypeScript — contrat nav exporté', () => {
    expect(typeof getFinanceNavTos).toBe('function')
    expect(typeof getSalesNavTos).toBe('function')
  })

  it('ND30 build — modules nav importables', () => {
    expect(navCategories.length).toBe(8)
    expect(salesNavCategories.length).toBe(7)
  })
})

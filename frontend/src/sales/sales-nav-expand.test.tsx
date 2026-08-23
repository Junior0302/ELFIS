/**
 * SalesProductNav — parité accordion Finance (expand / collapse / routes).
 * @vitest-environment jsdom
 */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { SalesProductNav } from '../platform-shell/SalesProductNav'
import {
  findActiveSalesCategory,
  salesNavCategories,
  SALES_NAV_ITEMS,
} from './salesNavModel'

afterEach(() => {
  cleanup()
})

function renderNav(path: string, collapsed = false) {
  const onCollapsedChange = vi.fn()
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route
          path="*"
          element={
            <SalesProductNav collapsed={collapsed} onCollapsedChange={onCollapsedChange} />
          }
        />
      </Routes>
    </MemoryRouter>,
  )
}

describe('salesNavModel — hiérarchie Commercial', () => {
  it('expose catégories accordion (parité Finance)', () => {
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

  it('mappe routes réelles uniquement', () => {
    const tos = SALES_NAV_ITEMS.map((i) => i.to)
    expect(tos).toEqual(
      expect.arrayContaining([
        '/sales',
        '/sales/leads',
        '/sales/companies',
        '/sales/contacts',
        '/sales/import',
        '/sales/pipeline',
        '/sales/proposals',
        '/sales/activities',
        '/sales/calendar',
        '/sales/tasks',
        '/sales/journal',
        '/sales/reports',
        '/sales/intelligence',
        '/sales/settings',
      ]),
    )
    expect(tos).not.toContain('/sales/negotiations')
    expect(tos).not.toContain('/sales/calls')
    expect(tos).not.toContain('/sales/emails')
    expect(tos).not.toContain('/sales/automations')
    expect(tos).not.toContain('/sales/team')
  })

  it('findActiveSalesCategory — parent actif sur route enfant', () => {
    expect(findActiveSalesCategory('/sales/proposals')?.id).toBe('pipeline')
    expect(findActiveSalesCategory('/sales/calendar')?.id).toBe('activites')
    expect(findActiveSalesCategory('/sales/intelligence')?.id).toBe('reporting')
    expect(findActiveSalesCategory('/sales')?.id).toBe('dashboard')
  })

  it('préfère Clients sur Entreprises / Contacts partagés', () => {
    expect(findActiveSalesCategory('/sales/companies')?.id).toBe('clients')
    expect(findActiveSalesCategory('/sales/contacts')?.id).toBe('clients')
    expect(findActiveSalesCategory('/sales/leads')?.id).toBe('prospection')
  })
})

describe('SalesProductNav — expand / collapse', () => {
  it('affiche catégories parents avec chevron (pas headers plats)', () => {
    renderNav('/sales')
    expect(screen.getByRole('navigation', { name: 'Navigation Commercial' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Prospection' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Pipeline' })).toBeTruthy()
    expect(screen.queryByText('PROSPECTION')).toBeNull()
  })

  it('déplie Pipeline et montre enfants indentés', () => {
    renderNav('/sales/pipeline')
    const pipelineBtn = screen.getByRole('button', { name: 'Pipeline' })
    expect(pipelineBtn).toHaveAttribute('aria-expanded', 'true')
    const group = pipelineBtn.closest('.nav-group') as HTMLElement
    expect(within(group).getByRole('link', { name: /Vue d’ensemble/i })).toBeTruthy()
    expect(within(group).getByRole('link', { name: 'Propositions' })).toBeTruthy()
  })

  it('toggle collapse d’une catégorie déjà ouverte', () => {
    renderNav('/sales/leads')
    const btn = screen.getByRole('button', { name: 'Prospection' })
    expect(btn).toHaveAttribute('aria-expanded', 'true')
    fireEvent.click(btn)
    expect(btn).toHaveAttribute('aria-expanded', 'false')
  })

  it('mode collapsed : icônes + flyout au survol', () => {
    renderNav('/sales/pipeline', true)
    const nav = screen.getByRole('navigation', { name: 'Navigation Commercial' })
    expect(nav.className).toMatch(/is-collapsed/)
    const group = screen.getByRole('button', { name: 'Pipeline' }).closest('.nav-group')
    expect(group).toBeTruthy()
    fireEvent.mouseEnter(group!)
    const flyout = within(group as HTMLElement).getByRole('menu', { name: 'Pipeline' })
    expect(within(flyout).getByRole('link', { name: 'Propositions' })).toBeTruthy()
  })

  it('Clients Commercial sans lien Relations plateforme', () => {
    renderNav('/sales/companies')
    expect(screen.queryByRole('link', { name: /^Relations$/i })).toBeNull()
    expect(screen.getByRole('link', { name: 'Entreprises' })).toHaveAttribute(
      'href',
      '/sales/companies',
    )
  })

  it('Paramètres → Général', () => {
    renderNav('/sales/settings')
    expect(screen.getByRole('link', { name: 'Général' })).toHaveAttribute('href', '/sales/settings')
  })
})

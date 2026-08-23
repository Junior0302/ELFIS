/**

 * Parcours E2E minimal SalesPilot — sans Playwright (absent du repo).

 * Vérifie que les routes du parcours PR1.1 sont déclarées dans App + nav.

 */

import { describe, expect, it } from 'vitest'

import { readFileSync } from 'node:fs'

import { resolve } from 'node:path'

import { SALES_NAV_ITEMS, salesNavCategories } from './salesNavModel'

import { PRODUCT_ENTRY_ROUTES } from '../app-launcher/productEntryRoutes'



const APP_TSX = readFileSync(resolve(__dirname, '../App.tsx'), 'utf8')



const E2E_ROUTE_SNIPPETS = [

  'path="sales"',

  'path="sales/leads"',

  'path="sales/pipeline"',

  'path="sales/deals/:id"',

  'path="sales/proposals"',

  'path="sales/proposals/new"',

  'path="sales/proposals/:id"',

  'path="sales/workspace/:entity/:id"',

]



describe('SalesPilot E2E navigation minimal (statique)', () => {

  it('Launcher SalesPilot → /sales', () => {

    expect(PRODUCT_ENTRY_ROUTES.salespilot).toBe('/sales')

  })



  it('parcours login→dashboard→lead→pipeline→deal→proposal déclaré dans App', () => {

    for (const snippet of E2E_ROUTE_SNIPPETS) {

      expect(APP_TSX).toContain(snippet)

    }

  })



  it('nav primaires structurée accordion Commercial', () => {

    expect(salesNavCategories.map((c) => c.id)).toEqual([

      'dashboard',

      'prospection',

      'pipeline',

      'activites',

      'reporting',

      'clients',

      'parametres',

    ])

    expect(SALES_NAV_ITEMS.map((i) => i.id)).toEqual([

      'dashboard',

      'leads',

      'companies',

      'contacts',

      'import',

      'pipeline-overview',

      'proposals',

      'activities-overview',

      'calendar',

      'tasks',

      'journal',

      'reports-overview',

      'intelligence',

      'clients-companies',

      'clients-contacts',

      'settings-general',

    ])

  })

})


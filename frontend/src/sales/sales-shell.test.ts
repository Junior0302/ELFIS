/**

 * SalesPilot shell — routing / nav foundation.

 */

import { describe, expect, it } from 'vitest'

import { SALES_NAV_ITEMS, salesNavCategories } from '../sales/salesNavModel'

import { getProductEntryRoute, getKnownSpaRoutes } from '../app-launcher/productEntryRoutes'

import { getProductById } from '../design-system'



describe('SalesPilot shell', () => {

  it('expose la navigation Commercial structurée (NAV.DOMAIN.1)', () => {

    const tos = SALES_NAV_ITEMS.map((i) => i.to)

    expect(salesNavCategories.length).toBe(7)

    expect(SALES_NAV_ITEMS.length).toBeGreaterThanOrEqual(12)

    expect(tos).toEqual(

      expect.arrayContaining([

        '/sales',

        '/sales/intelligence',

        '/sales/leads',

        '/sales/calendar',

        '/sales/import',

        '/sales/journal',

        '/sales/reports',

        '/sales/settings',

      ]),

    )

    expect(tos).not.toContain('/sales/team')

    expect(tos).not.toContain('/sales/collab/views')

    expect(tos).not.toContain('/sales/duplicates')

  })



  it('route d’entrée launcher = /sales', () => {

    expect(getProductEntryRoute('salespilot')).toBe('/sales')

    expect(getKnownSpaRoutes().has('/sales')).toBe(true)

  })



  it('registry: beta en DEV, coming_soon sinon', () => {

    const p = getProductById('salespilot')

    if (import.meta.env.DEV) {

      expect(p.status).toBe('beta')

      expect(p.availableInLauncher).toBe(true)

    } else {

      expect(p.status).toBe('coming_soon')

      expect(p.availableInLauncher).toBe(false)

    }

  })

})


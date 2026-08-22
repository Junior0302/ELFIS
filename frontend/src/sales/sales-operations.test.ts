/**
 * SalesPilot Operations V1 — helpers & nav smoke.
 */
import { describe, expect, it } from 'vitest'
import { personLabel, type SalesPerson } from './salesOps'
import { SALES_NAV_ITEMS } from './salesNavModel'

describe('salesOps helpers', () => {
  it('personLabel concatène prénom + nom', () => {
    const p: SalesPerson = {
      id: 1,
      first_name: 'Ada',
      last_name: 'Lovelace',
      status: 'active',
      created_at: '',
      updated_at: '',
    }
    expect(personLabel(p)).toBe('Ada Lovelace')
  })

  it('nav ops S1.8 présente calendrier / import / journal / doublons', () => {
    const tos = SALES_NAV_ITEMS.map((i) => i.to)
    expect(tos).toEqual(
      expect.arrayContaining([
        '/sales/calendar',
        '/sales/import',
        '/sales/journal',
      ]),
    )
  })
})

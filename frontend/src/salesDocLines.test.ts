import { describe, expect, it } from 'vitest'
import {
  emptySalesLine,
  lineAmountHt,
  linesTotalHt,
  normalizeSalesLines,
  salesLinesFromDoc,
} from './salesDocLines'

describe('salesDocLines', () => {
  it('calcule le total HT des lignes', () => {
    expect(lineAmountHt({ label: 'A', quantity: 2, unit_price: 50 })).toBe(100)
    expect(
      linesTotalHt([
        { label: 'A', quantity: 2, unit_price: 50 },
        { label: 'B', quantity: 1, unit_price: 25.5 },
      ]),
    ).toBe(125.5)
  })

  it('normalise en retirant les lignes sans désignation', () => {
    expect(
      normalizeSalesLines([
        { label: '  Service  ', quantity: 1, unit_price: 10 },
        emptySalesLine(),
      ]),
    ).toEqual([{ label: 'Service', quantity: 1, unit_price: 10, catalog_item_id: null }])
  })

  it('reconstruit une ligne depuis un montant global sans lines_json', () => {
    expect(salesLinesFromDoc(undefined, 120)).toEqual([
      { label: 'Prestation', quantity: 1, unit_price: 120, catalog_item_id: null },
    ])
  })
})

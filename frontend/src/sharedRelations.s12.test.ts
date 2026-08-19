/**
 * SharedRelation ID helpers (frontend mirror of backend opaque IDs).
 * @vitest-environment node
 */
import { describe, expect, it } from 'vitest'

function makeRelationId(source: string, id: number) {
  return `${source}:${id}`
}

function parseRelationId(raw: string): { source: string; id: number } {
  const [source, idPart] = raw.split(':')
  return { source, id: Number(idPart) }
}

describe('S1.2 SharedRelation opaque IDs', () => {
  it('customer / contact / sales_company', () => {
    expect(makeRelationId('customer', 12)).toBe('customer:12')
    expect(makeRelationId('contact', 3)).toBe('contact:3')
    expect(makeRelationId('sales_company', 9)).toBe('sales_company:9')
    expect(parseRelationId('customer:12')).toEqual({ source: 'customer', id: 12 })
  })
})

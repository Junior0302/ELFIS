/**
 * @vitest-environment jsdom
 */
import { beforeEach, describe, expect, it } from 'vitest'
import { getLastProductAt, getLastProductId, setLastProductId } from './lastProduct'

function memoryStorage(): Storage {
  const map = new Map<string, string>()
  return {
    get length() {
      return map.size
    },
    clear: () => map.clear(),
    getItem: (k) => (map.has(k) ? map.get(k)! : null),
    key: (i) => [...map.keys()][i] ?? null,
    removeItem: (k) => {
      map.delete(k)
    },
    setItem: (k, v) => {
      map.set(k, String(v))
    },
  }
}

describe('lastProduct', () => {
  beforeEach(() => {
    Object.defineProperty(globalThis, 'localStorage', {
      value: memoryStorage(),
      configurable: true,
      writable: true,
    })
  })

  it('retourne null sans clé', () => {
    expect(getLastProductId()).toBeNull()
    expect(getLastProductAt()).toBeNull()
  })

  it('persiste comptapilot / salespilot', () => {
    setLastProductId('comptapilot')
    expect(getLastProductId()).toBe('comptapilot')
    expect(getLastProductAt()).toBeTruthy()
    setLastProductId('salespilot')
    expect(getLastProductId()).toBe('salespilot')
  })

  it('ignore une clé inconnue', () => {
    localStorage.setItem('elfis_last_product', 'docpilot')
    expect(getLastProductId()).toBeNull()
  })
})

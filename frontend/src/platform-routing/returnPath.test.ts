import { describe, expect, it } from 'vitest'
import { locationReturnKey, sanitizeReturnPath } from './returnPath'

describe('sanitizeReturnPath', () => {
  it('conserve routes métier', () => {
    expect(sanitizeReturnPath('/dashboard')).toBe('/dashboard')
    expect(sanitizeReturnPath('/finance')).toBe('/finance')
  })

  it('conserve query string', () => {
    expect(sanitizeReturnPath('/facturation/documents/new?type=invoice')).toBe(
      '/facturation/documents/new?type=invoice',
    )
  })

  it('refuse auth et welcome', () => {
    expect(sanitizeReturnPath('/login')).toBe('/home')
    expect(sanitizeReturnPath('/welcome')).toBe('/home')
  })

  it('refuse valeurs invalides', () => {
    expect(sanitizeReturnPath(null)).toBe('/home')
    expect(sanitizeReturnPath('http://x')).toBe('/home')
  })
})

describe('locationReturnKey', () => {
  it('concatène pathname search hash', () => {
    expect(locationReturnKey({ pathname: '/a', search: '?q=1', hash: '#h' })).toBe('/a?q=1#h')
  })
})

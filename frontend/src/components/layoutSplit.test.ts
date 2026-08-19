import { describe, expect, it } from 'vitest'
import { safeAvatarUrl, userInitials } from './layouts/layoutUtils'

describe('layoutUtils', () => {
  it('calcule les initiales', () => {
    expect(userInitials('Chris', 'Martin')).toBe('CM')
    expect(userInitials('', '')).toBe('?')
  })

  it('valide les URLs avatar', () => {
    expect(safeAvatarUrl('https://cdn.example/a.png')).toBe('https://cdn.example/a.png')
    expect(safeAvatarUrl('/avatars/1.png')).toBe('/avatars/1.png')
    expect(safeAvatarUrl('javascript:alert(1)')).toBe('')
  })
})

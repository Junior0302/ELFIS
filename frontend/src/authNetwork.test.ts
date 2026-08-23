/**
 * Auth network helpers — timeout / health / messages login.
 */
import { describe, expect, it, vi } from 'vitest'
import {
  checkBackendHealth,
  getApiRoot,
  resolveApiRoot,
  mapLoginFailure,
  authDevLog,
  isAbortError,
} from './authNetwork'

describe('authNetwork', () => {
  it('getApiRoot en DEV utilise /api (proxy Vite)', () => {
    expect(getApiRoot()).toBe('/api')
  })

  it('resolveApiRoot refuse un build production sans VITE_API_URL', () => {
    expect(() => resolveApiRoot({ isDev: false })).toThrow(/VITE_API_URL/)
    expect(resolveApiRoot({ isDev: false, viteApiUrl: 'https://api.example/api' })).toBe(
      'https://api.example/api',
    )
    expect(resolveApiRoot({ isDev: true })).toBe('/api')
  })

  it('mapLoginFailure — timeout / réseau', () => {
    const abort = new DOMException('Aborted', 'AbortError')
    expect(mapLoginFailure(abort)).toMatch(/ne répond pas/)
    expect(mapLoginFailure(new TypeError('Failed to fetch'))).toMatch(/ne répond pas/)
    expect(
      mapLoginFailure(new Error('Le serveur ELFIS Core ne répond pas. Vérifiez que le backend est démarré.')),
    ).toMatch(/ne répond pas/)
  })

  it('mapLoginFailure — identifiants incorrects', () => {
    expect(mapLoginFailure({ code: 'auth/invalid-credential' })).toMatch(/incorrect/)
    expect(mapLoginFailure(new Error('Email ou mot de passe incorrect.'))).toMatch(/incorrect/)
  })

  it('mapLoginFailure — erreur inconnue générique', () => {
    expect(mapLoginFailure({ code: 'auth/something-weird' })).toMatch(/Impossible de vous connecter/)
    expect(mapLoginFailure(new Error('firebase identity toolkit boom'))).toMatch(
      /Impossible de vous connecter/,
    )
  })

  it('isAbortError détecte AbortError', () => {
    expect(isAbortError(new DOMException('x', 'AbortError'))).toBe(true)
    expect(isAbortError(new Error('nope'))).toBe(false)
  })

  it('checkBackendHealth — available', async () => {
    const fetchImpl = vi.fn().mockResolvedValue({ ok: true, status: 200 })
    await expect(checkBackendHealth(fetchImpl as unknown as typeof fetch, 1000)).resolves.toBe(
      'available',
    )
    expect(fetchImpl).toHaveBeenCalledWith(
      '/api/health',
      expect.objectContaining({ method: 'GET' }),
    )
  })

  it('checkBackendHealth — timeout', async () => {
    const fetchImpl = vi.fn().mockRejectedValue(new DOMException('Aborted', 'AbortError'))
    await expect(checkBackendHealth(fetchImpl as unknown as typeof fetch, 50)).resolves.toBe(
      'timeout',
    )
  })

  it('checkBackendHealth — unavailable', async () => {
    const fetchImpl = vi.fn().mockResolvedValue({ ok: false, status: 500 })
    await expect(checkBackendHealth(fetchImpl as unknown as typeof fetch, 1000)).resolves.toBe(
      'unavailable',
    )
  })

  it('authDevLog ne logge pas password/token', () => {
    const spy = vi.spyOn(console, 'info').mockImplementation(() => undefined)
    authDevLog('test', { password: 'secret', access_token: 'tok', status: 401 })
    expect(spy).toHaveBeenCalled()
    const payload = spy.mock.calls[0]?.[1] as Record<string, unknown>
    expect(payload.password).toBeUndefined()
    expect(payload.access_token).toBeUndefined()
    expect(payload.status).toBe(401)
    spy.mockRestore()
  })
})

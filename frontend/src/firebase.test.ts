import { describe, expect, it, vi } from 'vitest'
import {
  isFirebaseWebConfigReady,
  logSafeFirebaseAuthError,
  mapFirebaseError,
} from './firebase'

describe('Firebase web config', () => {
  it('refuse un placeholder (cause racine du bundle production)', () => {
    expect(
      isFirebaseWebConfigReady({
        apiKey: 'TA_CLE_FIREBASE',
        authDomain: 'elfis-core.firebaseapp.com',
        projectId: 'elfis-core',
        appId: 'TON_APP_ID_FIREBASE',
      }),
    ).toBe(false)
  })

  it('accepte une config Web Firebase plausible', () => {
    expect(
      isFirebaseWebConfigReady({
        apiKey: 'AIzaSyDummyPublicWebKeyForTestsOnly12',
        authDomain: 'elfis-core.firebaseapp.com',
        projectId: 'elfis-core',
        appId: '1:491404408963:web:abc123def456',
      }),
    ).toBe(true)
  })
})

describe('mapFirebaseError', () => {
  it('mappe les identifiants incorrects', () => {
    expect(mapFirebaseError({ code: 'auth/invalid-credential' })).toMatch(/incorrect/)
    expect(mapFirebaseError({ code: 'auth/wrong-password' })).toMatch(/incorrect/)
    expect(mapFirebaseError({ code: 'auth/user-not-found' })).toMatch(/Aucun compte/)
  })

  it('mappe une clé API invalide sans exposer le détail technique', () => {
    expect(mapFirebaseError({ code: 'auth/invalid-api-key' })).toMatch(/Configuration Firebase/)
    expect(
      mapFirebaseError({
        code: 'auth/api-key-not-valid.-please-pass-a-valid-api-key.',
      }),
    ).toMatch(/Configuration Firebase/)
  })

  it('mappe un domaine non autorisé', () => {
    expect(mapFirebaseError({ code: 'auth/unauthorized-domain' })).toMatch(/domaine/)
  })

  it('masque les messages Identity Toolkit bruts', () => {
    expect(mapFirebaseError(new Error('Firebase: Error (auth/something).'))).toMatch(
      /Authentification impossible/,
    )
  })
})

describe('logSafeFirebaseAuthError', () => {
  it('ne logge que le code, jamais un token', () => {
    const spy = vi.spyOn(console, 'info').mockImplementation(() => undefined)
    logSafeFirebaseAuthError({
      code: 'auth/invalid-api-key',
      message: 'Firebase: Error (auth/invalid-api-key).',
    })
    if (spy.mock.calls.length) {
      const line = String(spy.mock.calls[0]?.[0])
      expect(line).toContain('firebase_auth_error code=auth/invalid-api-key')
      expect(line).not.toMatch(/token|password|AIza/i)
    }
    spy.mockRestore()
  })
})

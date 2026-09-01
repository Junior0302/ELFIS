import { describe, expect, it } from 'vitest'
import {
  EXPECTED_PRODUCTION_API_ROOT,
  assertProductionFrontendEnv,
  isPlaceholderEnvValue,
  isUsableFirebaseApiKey,
  isUsableFirebaseAppId,
} from './buildEnv'

describe('assertProductionFrontendEnv', () => {
  const valid = {
    VITE_API_URL: EXPECTED_PRODUCTION_API_ROOT,
    VITE_FIREBASE_API_KEY: 'AIzaSyDummyPublicWebKeyForTestsOnly12',
    VITE_FIREBASE_AUTH_DOMAIN: 'elfis-core.firebaseapp.com',
    VITE_FIREBASE_PROJECT_ID: 'elfis-core',
    VITE_FIREBASE_APP_ID: '1:491404408963:web:abc123def456',
  }

  it('accepte un jeu HTTPS complet et des identifiants Web Firebase plausibles', () => {
    expect(() => assertProductionFrontendEnv(valid)).not.toThrow()
  })

  it('échoue sans VITE_API_URL', () => {
    expect(() => assertProductionFrontendEnv({ ...valid, VITE_API_URL: '' })).toThrow(
      /VITE_API_URL/,
    )
  })

  it('refuse localhost ou :8000', () => {
    expect(() =>
      assertProductionFrontendEnv({ ...valid, VITE_API_URL: 'https://localhost:8000/api' }),
    ).toThrow(/localhost|:8000/)
  })

  it('refuse /api/api', () => {
    expect(() =>
      assertProductionFrontendEnv({
        ...valid,
        VITE_API_URL: 'https://elfis-core-api-4lul.onrender.com/api/api',
      }),
    ).toThrow(/api\/api/)
  })

  it('refuse les placeholders Firebase utilisés par erreur au build', () => {
    expect(isPlaceholderEnvValue('TA_CLE_FIREBASE')).toBe(true)
    expect(isPlaceholderEnvValue('TON_APP_ID_FIREBASE')).toBe(true)
    expect(isUsableFirebaseApiKey('TA_CLE_FIREBASE')).toBe(false)
    expect(isUsableFirebaseAppId('TON_APP_ID_FIREBASE')).toBe(false)
    expect(() =>
      assertProductionFrontendEnv({ ...valid, VITE_FIREBASE_API_KEY: 'TA_CLE_FIREBASE' }),
    ).toThrow(/VITE_FIREBASE_API_KEY/)
    expect(() =>
      assertProductionFrontendEnv({ ...valid, VITE_FIREBASE_APP_ID: 'TON_APP_ID_FIREBASE' }),
    ).toThrow(/VITE_FIREBASE_APP_ID/)
  })
})

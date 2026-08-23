import { describe, expect, it } from 'vitest'
import { assertProductionFrontendEnv } from './buildEnv'

describe('assertProductionFrontendEnv', () => {
  const valid = {
    VITE_API_URL: 'https://elfis-core-api.example/api',
    VITE_FIREBASE_API_KEY: 'public-web-key',
    VITE_FIREBASE_AUTH_DOMAIN: 'example.firebaseapp.com',
    VITE_FIREBASE_PROJECT_ID: 'example',
    VITE_FIREBASE_APP_ID: '1:1:web:abc',
  }

  it('accepte un jeu HTTPS complet', () => {
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
})

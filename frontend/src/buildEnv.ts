export const REQUIRED_PRODUCTION_VITE_KEYS = [
  'VITE_API_URL',
  'VITE_FIREBASE_API_KEY',
  'VITE_FIREBASE_AUTH_DOMAIN',
  'VITE_FIREBASE_PROJECT_ID',
  'VITE_FIREBASE_APP_ID',
] as const

export function assertProductionFrontendEnv(
  env: Record<string, string | undefined>,
): void {
  const missing = REQUIRED_PRODUCTION_VITE_KEYS.filter((key) => !(env[key] || '').trim())
  if (missing.length) {
    throw new Error(
      `Build production incomplet : variables manquantes ${missing.join(', ')}. ` +
        'Définir VITE_API_URL (https://…/api) et les VITE_FIREBASE_* avant npm run build.',
    )
  }
  const api = (env.VITE_API_URL || '').trim()
  if (!/^https:\/\//i.test(api)) {
    throw new Error('VITE_API_URL doit être une URL HTTPS (ex. https://api.example/api).')
  }
  if (/localhost|127\.0\.0\.1|:8000(\/|$)/i.test(api)) {
    throw new Error(
      'VITE_API_URL ne doit pas utiliser localhost ni le port 8000 pour un build production.',
    )
  }
}

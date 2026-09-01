export const REQUIRED_PRODUCTION_VITE_KEYS = [
  'VITE_API_URL',
  'VITE_FIREBASE_API_KEY',
  'VITE_FIREBASE_AUTH_DOMAIN',
  'VITE_FIREBASE_PROJECT_ID',
  'VITE_FIREBASE_APP_ID',
] as const

/** URL API production attendue (build-time). Jamais un fallback runtime. */
export const EXPECTED_PRODUCTION_API_ROOT = 'https://elfis-core-api-4lul.onrender.com/api'

const PLACEHOLDER_VALUES = new Set([
  'ta_cle_firebase',
  'ton_app_id_firebase',
  'your_firebase_api_key',
  'your_firebase_app_id',
  'changeme',
  'change_me',
  'placeholder',
  'dummy',
  'todo',
  'xxx',
  'xxxx',
])

export function isPlaceholderEnvValue(value: string | undefined): boolean {
  const v = (value || '').trim()
  if (!v) return true
  const lower = v.toLowerCase()
  if (PLACEHOLDER_VALUES.has(lower)) return true
  return /^(your[_-]|ton[_-]|ta[_-]|change[_-]?me|xxx+|todo|placeholder|dummy|replace[_-])/i.test(v)
}

export function isUsableFirebaseApiKey(value: string | undefined): boolean {
  return /^AIza[0-9A-Za-z_-]{20,}$/.test((value || '').trim())
}

export function isUsableFirebaseAppId(value: string | undefined): boolean {
  return /^\d+:\d+:web:[0-9A-Za-z]+$/.test((value || '').trim())
}

export function isUsableFirebaseProjectId(value: string | undefined): boolean {
  const v = (value || '').trim()
  return Boolean(v) && !isPlaceholderEnvValue(v) && /^[a-z0-9][a-z0-9-]*[a-z0-9]$/i.test(v)
}

export function isUsableFirebaseAuthDomain(value: string | undefined): boolean {
  const v = (value || '').trim()
  return Boolean(v) && !isPlaceholderEnvValue(v) && v.includes('.') && !/\s/.test(v)
}

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
  if (/\/api\/api\/?$/i.test(api)) {
    throw new Error('VITE_API_URL ne doit pas se terminer par /api/api.')
  }
  if (isPlaceholderEnvValue(env.VITE_FIREBASE_API_KEY) || !isUsableFirebaseApiKey(env.VITE_FIREBASE_API_KEY)) {
    throw new Error(
      'VITE_FIREBASE_API_KEY invalide : coller la clé Web Firebase réelle (préfixe AIza), pas un placeholder.',
    )
  }
  if (isPlaceholderEnvValue(env.VITE_FIREBASE_APP_ID) || !isUsableFirebaseAppId(env.VITE_FIREBASE_APP_ID)) {
    throw new Error(
      'VITE_FIREBASE_APP_ID invalide : format attendu 1:<project-number>:web:<id>.',
    )
  }
  if (!isUsableFirebaseProjectId(env.VITE_FIREBASE_PROJECT_ID)) {
    throw new Error('VITE_FIREBASE_PROJECT_ID invalide ou placeholder.')
  }
  if (!isUsableFirebaseAuthDomain(env.VITE_FIREBASE_AUTH_DOMAIN)) {
    throw new Error('VITE_FIREBASE_AUTH_DOMAIN invalide ou placeholder.')
  }
}

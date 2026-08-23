import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { execSync } from 'node:child_process'
import path from 'node:path'
import { assertProductionFrontendEnv } from './src/buildEnv.js'

// Dev : le frontend appelle "/api/*" (same-origin).
// Ce proxy relaie vers le backend local — port unique aligné avec start-backend.bat.
const API_TARGET = process.env.VITE_DEV_API_PROXY || 'http://127.0.0.1:8000'
const DEV_PORT = 5173

function git(cmd: string): string {
  try {
    return execSync(cmd, { stdio: ['ignore', 'pipe', 'ignore'] })
      .toString()
      .trim()
  } catch {
    return 'unknown'
  }
}

const GIT_SHA = process.env.VITE_APP_GIT_SHA || git('git rev-parse --short HEAD')
const GIT_BRANCH = process.env.VITE_APP_GIT_BRANCH || git('git rev-parse --abbrev-ref HEAD')
const BUILT_AT = process.env.VITE_APP_BUILT_AT || new Date().toISOString()
const FRONTEND_ROOT = path.resolve(__dirname)

// Preuve console au démarrage Vite (dev server / build)
// eslint-disable-next-line no-console
console.info(
  `[ComptaPilot] Vite · branch=${GIT_BRANCH} · sha=${GIT_SHA} · root=${FRONTEND_ROOT} · port=${DEV_PORT} · builtAt=${BUILT_AT}`,
)

export default defineConfig(({ command, mode }) => {
  if (command === 'build' && mode === 'production') {
    assertProductionFrontendEnv(process.env)
  }
  return {
    plugins: [react()],
    define: {
      'import.meta.env.VITE_APP_GIT_SHA': JSON.stringify(GIT_SHA),
      'import.meta.env.VITE_APP_GIT_BRANCH': JSON.stringify(GIT_BRANCH),
      'import.meta.env.VITE_APP_BUILT_AT': JSON.stringify(BUILT_AT),
      'import.meta.env.VITE_APP_FRONTEND_ROOT': JSON.stringify(FRONTEND_ROOT),
      'import.meta.env.VITE_APP_DEV_PORT': JSON.stringify(String(DEV_PORT)),
    },
    server: {
      host: true,
      port: DEV_PORT,
      strictPort: true,
      proxy: {
        '/api': {
          target: API_TARGET,
          changeOrigin: true,
          secure: false,
        },
      },
    },
  }
})

/**
 * Identité du build frontend — injectée par Vite au démarrage.
 * Visible en développement uniquement pour confirmer le bon build servi.
 */
export type AppBuildInfo = {
  sha: string
  branch: string
  builtAt: string
  mode: string
  frontendRoot: string
  portHint: string
}

declare global {
  interface ImportMetaEnv {
    readonly VITE_APP_GIT_SHA?: string
    readonly VITE_APP_GIT_BRANCH?: string
    readonly VITE_APP_BUILT_AT?: string
    readonly VITE_APP_FRONTEND_ROOT?: string
    readonly VITE_APP_DEV_PORT?: string
  }
}

export function getAppBuildInfo(): AppBuildInfo {
  return {
    sha: import.meta.env.VITE_APP_GIT_SHA || 'unknown',
    branch: import.meta.env.VITE_APP_GIT_BRANCH || 'unknown',
    builtAt: import.meta.env.VITE_APP_BUILT_AT || new Date().toISOString(),
    mode: import.meta.env.MODE || 'unknown',
    frontendRoot: import.meta.env.VITE_APP_FRONTEND_ROOT || 'frontend',
    portHint: import.meta.env.VITE_APP_DEV_PORT || '5173',
  }
}

export function formatBuildBanner(info: AppBuildInfo = getAppBuildInfo()): string {
  return (
    `[ComptaPilot] frontend build · branch=${info.branch} · sha=${info.sha} · ` +
    `root=${info.frontendRoot} · port≈${info.portHint} · mode=${info.mode} · builtAt=${info.builtAt}`
  )
}

export function logBuildBanner(): void {
  // eslint-disable-next-line no-console
  console.info(formatBuildBanner())
}

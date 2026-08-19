/**
 * Design System theme sandbox — development only.
 */

export function isDesignSystemSandboxEnabled(): boolean {
  try {
    return import.meta.env.DEV === true
  } catch {
    return false
  }
}

export const DESIGN_SYSTEM_THEME_SANDBOX_PATH = '/dev/design-system/themes'

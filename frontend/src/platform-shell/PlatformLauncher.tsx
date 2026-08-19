import { AppLauncher } from '../app-launcher'
import { cx } from '../design-system'

type PlatformLauncherProps = {
  compact?: boolean
  className?: string
}

/**
 * Launcher plateforme — unique point d’entrée shell.
 * Délègue à AppLauncher Premium V1 (registry, routes, lastProduct).
 */
export function PlatformLauncher({ compact, className }: PlatformLauncherProps) {
  return (
    <div className={cx('ps-launcher', className)}>
      <AppLauncher compactTrigger={compact} />
    </div>
  )
}

import { CommandCenter } from '../platform-command'
import { cx } from '../design-system'

type PlatformSearchProps = {
  compact?: boolean
  className?: string
}

/**
 * Topbar search entry — opens ELFIS Command Center (P2.4).
 * Ctrl/Cmd+K registered by CommandCenter; does not steal Ctrl/Cmd+Shift+A (Launcher).
 */
export function PlatformSearch({ compact, className }: PlatformSearchProps) {
  return <CommandCenter compactTrigger={compact} className={cx(className)} />
}

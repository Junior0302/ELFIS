/**
 * Design System 1.0 certification matrix (E1.7).
 * Evidence-based Ready / Partially Ready / Not Ready — do not invent statuses.
 */

export type CertificationStatus = 'ready' | 'partially_ready' | 'not_ready'

export type CertificationRow = {
  id: string
  label: string
  status: CertificationStatus
  justification: string
}

export const DESIGN_SYSTEM_CERTIFICATION: readonly CertificationRow[] = [
  {
    id: 'architecture',
    label: 'Architecture',
    status: 'ready',
    justification: 'Single package under src/design-system + app-launcher; no parallel DS.',
  },
  {
    id: 'theme',
    label: 'Theme',
    status: 'ready',
    justification: 'Theme Engine resolve/apply/validate + ProductThemeProvider certified E1.2–E1.3.',
  },
  {
    id: 'accessibility',
    label: 'Accessibility',
    status: 'partially_ready',
    justification: 'Overlays/Launcher/FormField solid; no axe CI; legacy pages remain weak.',
  },
  {
    id: 'components',
    label: 'Components',
    status: 'ready',
    justification: 'V1 set documented, tested; Stable/Preview maturity registered.',
  },
  {
    id: 'overlay',
    label: 'Overlay',
    status: 'ready',
    justification: 'Provider, stack, focus trap, Escape, ConfirmDialog/Drawer/Tooltip/Popover.',
  },
  {
    id: 'launcher',
    label: 'Launcher',
    status: 'ready',
    justification: 'App Launcher V1 integrated in WorkspaceLayout; analytics + sandbox preview.',
  },
  {
    id: 'registry',
    label: 'Registry',
    status: 'ready',
    justification: 'Product registry is the single source for Pilot identity and themes.',
  },
  {
    id: 'governance',
    label: 'Governance',
    status: 'ready',
    justification: 'Maturity registry, quality gates, contributing, versioning docs (E1.6–E1.7).',
  },
  {
    id: 'qa',
    label: 'QA',
    status: 'partially_ready',
    justification: 'Manual + unit QA documented; no visual regression / axe CI yet (roadmap 1.1).',
  },
  {
    id: 'responsive',
    label: 'Responsive',
    status: 'partially_ready',
    justification: 'Shell + launcher OK; dense legacy tables fragile at high zoom.',
  },
  {
    id: 'documentation',
    label: 'Documentation',
    status: 'ready',
    justification: 'E1.1–E1.7 docs complete including manifesto and release notes 1.0.',
  },
  {
    id: 'migration',
    label: 'Migration',
    status: 'partially_ready',
    justification: 'Path defined; large .btn / confirm / HEX debt remains by design.',
  },
  {
    id: 'legacy',
    label: 'Legacy',
    status: 'not_ready',
    justification: 'Legacy not eliminated; control rules exist but suppression waves pending.',
  },
] as const

export function certificationReadyCount(): { ready: number; partial: number; notReady: number } {
  let ready = 0
  let partial = 0
  let notReady = 0
  for (const row of DESIGN_SYSTEM_CERTIFICATION) {
    if (row.status === 'ready') ready += 1
    else if (row.status === 'partially_ready') partial += 1
    else notReady += 1
  }
  return { ready, partial, notReady }
}

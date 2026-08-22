import type { ReactNode, RefObject } from 'react'
import type { ProductId } from '../design-system'
import {
  PlatformSidebar,
  PlatformTopBar,
  WorkspaceViewport,
} from '../platform-shell/PlatformTopBar'
import {
  PlatformShell,
  type PlatformShellProps,
  type PlatformShellSidebarApi,
} from '../platform-shell/PlatformShell'
import type { ProductShellChromeOptions } from '../platform-shell/productShellConfig'
import { cx } from '../design-system'
import { isUnifiedPlatformUiEnabled } from './featureFlag'
import { resolvePilotTheme } from './PilotTheme'
import './unified-platform.css'

export type { PlatformShellSidebarApi }

/** Alias public Vague 1 — topbar globale (hamburger ELFIS unique, navy, pastille Pilot). */
export function GlobalTopbar(props: {
  productId: ProductId
  onMenuClick?: () => void
  menuOpen?: boolean
  menuButtonRef?: RefObject<HTMLButtonElement | null>
  className?: string
  chrome?: Partial<ProductShellChromeOptions>
}) {
  return <PlatformTopBar {...props} />
}

/** Alias public — rail produit (dimensions UI.P1 via shell). */
export function PilotSidebar(props: {
  children: ReactNode
  className?: string
  title?: string
}) {
  return <PlatformSidebar {...props} />
}

/** Alias public — viewport contenu. */
export function PilotContentLayout(props: {
  children: ReactNode
  className?: string
}) {
  return <WorkspaceViewport {...props} />
}

export type ElfisUnifiedShellProps = Omit<PlatformShellProps, 'productId'> & {
  /** Alias productId — contrat wrappers métier. */
  pilotId: ProductId
  /** Title sidebar / aria. */
  title?: string
}

/**
 * Shell unifié ELFIS — consolidation PlatformShell (pas un 2e chrome).
 * GlobalTopbar + PilotSidebar + PilotContentLayout via PlatformShell interne.
 * UI.P1 collapse / UI.P2 un hamburger préservés.
 */
export function ElfisUnifiedShell({
  pilotId,
  title,
  sidebarTitle,
  className,
  sidebarClassName,
  ...rest
}: ElfisUnifiedShellProps) {
  const unified = isUnifiedPlatformUiEnabled()

  return (
    <PlatformShell
      productId={pilotId}
      sidebarTitle={title ?? sidebarTitle}
      className={cx('up-shell', unified && 'up-shell--unified', className)}
      sidebarClassName={cx('up-sidebar', sidebarClassName)}
      {...rest}
    />
  )
}

/**
 * Wrapper métier minimal — pilotId, nav, title ; accents via PilotTheme.
 * Pas de dimensions / chrome custom par Pilot.
 */
export type PilotWorkspaceProps = {
  pilotId: ProductId
  nav?: PlatformShellProps['sidebar']
  title?: string
  chrome?: PlatformShellProps['chrome']
  sidebarCollapsed?: boolean
  /** Si true (défaut), applique classes accent PilotTheme. */
  applyPilotAccent?: boolean
  /** Pose data-workspace sur le shell (tokens Phase 2). */
  dataWorkspace?: string
  className?: string
  sidebarClassName?: string
  children: ReactNode
}

export function PilotWorkspace({
  pilotId,
  nav,
  title,
  chrome,
  sidebarCollapsed,
  applyPilotAccent = true,
  dataWorkspace,
  className,
  sidebarClassName,
  children,
}: PilotWorkspaceProps) {
  const theme = resolvePilotTheme(pilotId)
  return (
    <ElfisUnifiedShell
      pilotId={pilotId}
      title={title}
      chrome={chrome}
      sidebar={nav}
      sidebarCollapsed={sidebarCollapsed}
      dataWorkspace={dataWorkspace}
      className={cx(applyPilotAccent && theme.shellAccentClass, className)}
      sidebarClassName={cx(
        applyPilotAccent && 'ps-sidebar--product',
        applyPilotAccent && theme.sidebarAccentClass,
        sidebarClassName,
      )}
    >
      {children}
    </ElfisUnifiedShell>
  )
}

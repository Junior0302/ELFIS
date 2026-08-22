/**
 * Adapter Finance — WorkspaceSidebar + financeWorkspaceConfig.
 * Trial lock + footer admin conservés.
 */

import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../auth'
import { trackProductEvent } from '../productEvents'
import { isTrialOnboardingMode } from '../subscription'
import { useSubscription } from '../subscriptionContext'
import { TRIAL_LOCK_MESSAGE } from '../trialOnboarding'
import { COMPTA_PRODUCT_NAV_ID } from './productSidebarCollapse'
import { WorkspaceSidebar } from '../workspaces/WorkspaceSidebar'
import { financeWorkspaceConfig } from '../workspaces'
import type { WorkspaceNavGroup } from '../workspaces'

type ComptaProductNavProps = {
  onNavigate?: () => void
  collapsed: boolean
  onCollapsedChange: (collapsed: boolean | ((prev: boolean) => boolean)) => void
}

export function ComptaProductNav({
  onNavigate,
  collapsed,
  onCollapsedChange,
}: ComptaProductNavProps) {
  const { user, memberships, orgId } = useAuth()
  const { subscription, loading: subLoading } = useSubscription()
  const location = useLocation()
  const [lockHint, setLockHint] = useState<string | null>(null)

  const activeMembership = memberships.find((m) => m.organization_id === orgId)
  const can = useCallback(
    (permission?: string) =>
      !permission ||
      Boolean(
        activeMembership?.permissions.includes('*') ||
          activeMembership?.permissions.includes(permission),
      ),
    [activeMembership],
  )

  const trialOnboarding =
    !subLoading &&
    isTrialOnboardingMode(subscription, {
      isPlatformAdmin: Boolean(user?.is_platform_admin),
    })

  useEffect(() => {
    setLockHint(null)
  }, [location.pathname])

  const isGroupLocked = useCallback(
    (group: WorkspaceNavGroup) => trialOnboarding && group.id !== 'dashboard',
    [trialOnboarding],
  )

  const onLockedActivate = useCallback((group: WorkspaceNavGroup, el?: HTMLElement | null) => {
    trackProductEvent('locked_nav_item_clicked', { label: group.label, to: group.to })
    setLockHint(TRIAL_LOCK_MESSAGE)
    if (el) {
      el.classList.remove('nav-locked-shake')
      void el.offsetWidth
      el.classList.add('nav-locked-shake')
      window.setTimeout(() => el.classList.remove('nav-locked-shake'), 420)
    }
  }, [])

  const footer = useMemo(() => {
    if (!user?.is_platform_admin) return null
    return (
      <Link to="/elfadmin" className="lan-hint sidebar-admin-link" onClick={onNavigate}>
        ELF Admin
      </Link>
    )
  }, [user?.is_platform_admin, onNavigate])

  const banner: ReactNode = lockHint ? (
    <div className="trial-nav-lock-toast" role="status">
      {lockHint}
    </div>
  ) : null

  return (
    <WorkspaceSidebar
      workspace={financeWorkspaceConfig}
      navId={COMPTA_PRODUCT_NAV_ID}
      ariaLabel="Navigation Finance"
      collapsed={collapsed}
      onCollapsedChange={onCollapsedChange}
      onNavigate={onNavigate}
      can={can}
      isGroupLocked={isGroupLocked}
      lockedMessage={TRIAL_LOCK_MESSAGE}
      onLockedActivate={onLockedActivate}
      banner={banner}
      footer={footer}
      className="ps-product-nav--compta compta-product-nav"
    />
  )
}

/** Exposé pour que le layout parent sache si le trial masque le chrome. */
export function useComptaTrialOnboarding(): boolean {
  const { user } = useAuth()
  const { subscription, loading } = useSubscription()
  return (
    !loading &&
    isTrialOnboardingMode(subscription, {
      isPlatformAdmin: Boolean(user?.is_platform_admin),
    })
  )
}

import { useEffect } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../../auth'
import { cx } from '../../design-system'
import PageGuide from '../PageGuide'
import SubscriptionBanner from '../SubscriptionBanner'
import { isPathAllowedDuringTrialOnboarding } from '../../trialOnboarding'
import { ComptaProductNav, useComptaTrialOnboarding } from '../../platform-shell/ComptaProductNav'
import { getProductShellConfiguration, withChromeOverrides } from '../../platform-shell/productShellConfig'
import { useProductSidebarCollapsed } from '../../platform-shell/useProductSidebarCollapsed'
import { PilotWorkspace, WorkspacePageFrame } from '../../unified-platform'

/** Composer création document — modal sous Documents (plus de page Focus shell). */
export function isComposerFullFocusPath(pathname: string): boolean {
  // Conservé pour tests / compat ; le flux nominal est modal (retourne false).
  void pathname
  return false
}

/** Détecte l’URL modale Composer (Documents reste monté). */
export function isComposerModalPath(pathname: string): boolean {
  return (
    pathname === '/facturation/documents/new' ||
    pathname.startsWith('/facturation/documents/new/')
  )
}

/**
 * ComptaPilot — navigation métier + Platform Shell (chrome unifié).
 * Thème via RuntimeThemeSync (route) — pas de setCurrentProduct ici.
 */
export default function WorkspaceLayout() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const trialOnboarding = useComptaTrialOnboarding()
  const fullFocus = isComposerFullFocusPath(location.pathname)
  const { collapsed: sidebarCollapsed, setCollapsed: setSidebarCollapsed } =
    useProductSidebarCollapsed()
  const base = getProductShellConfiguration('comptapilot')
  const config = withChromeOverrides(base, {
    showLauncher: Boolean(user) && !trialOnboarding,
    showSearch: Boolean(user) && !trialOnboarding && !fullFocus,
    showNotifications: Boolean(user) && !trialOnboarding,
  })

  useEffect(() => {
    if (!trialOnboarding) return
    if (!isPathAllowedDuringTrialOnboarding(location.pathname)) {
      navigate('/dashboard', { replace: true })
    }
  }, [trialOnboarding, location.pathname, navigate])

  useEffect(() => {
    if (fullFocus) {
      document.body.dataset.fpFullFocus = 'true'
    } else {
      delete document.body.dataset.fpFullFocus
    }
    return () => {
      delete document.body.dataset.fpFullFocus
    }
  }, [fullFocus])

  return (
    <PilotWorkspace
      pilotId={config.productId}
      dataWorkspace="finance"
      chrome={config.chrome}
      sidebarCollapsed={!fullFocus && sidebarCollapsed}
      className={cx(
        trialOnboarding && 'trial-onboarding-shell',
        fullFocus && 'ps-shell--composer-focus',
      )}
      nav={
        fullFocus
          ? undefined
          : ({ closeMobileNav }) => (
              <ComptaProductNav
                onNavigate={closeMobileNav}
                collapsed={sidebarCollapsed}
                onCollapsedChange={setSidebarCollapsed}
              />
            )
      }
    >
      <WorkspacePageFrame disabled={fullFocus}>
        {!fullFocus ? <SubscriptionBanner compactTrialOnboarding={trialOnboarding} /> : null}
        {!trialOnboarding && !fullFocus ? <PageGuide /> : null}
        <Outlet />
      </WorkspacePageFrame>
    </PilotWorkspace>
  )
}

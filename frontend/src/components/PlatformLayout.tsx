import { useCallback, useEffect, useMemo, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import PlatformSidebar from './platform/PlatformSidebar'
import PlatformTopbar from './platform/PlatformTopbar'
import {
  aggregateGlobalHealth,
  detectPlatformEnvironment,
  resolvePlatformPageTitle,
} from './platform/platformMeta'

export default function PlatformLayout() {
  const { user, token, logout } = useAuth()
  const location = useLocation()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [lastSync, setLastSync] = useState<Date | null>(null)
  const [healthStatuses, setHealthStatuses] = useState<string[]>([])
  const [criticalCount, setCriticalCount] = useState(0)

  const pageTitle = resolvePlatformPageTitle(location.pathname)
  const env = detectPlatformEnvironment()

  const refreshShell = useCallback(async () => {
    if (!token) return
    setRefreshing(true)
    try {
      const [health, incidents] = await Promise.all([
        api.platformHealthServices(token).catch(() => null),
        api.platformIncidents(token).catch(() => null),
      ])
      if (health?.services) {
        setHealthStatuses(health.services.map((s) => s.status))
      }
      if (incidents?.incidents) {
        setCriticalCount(
          incidents.incidents.filter((i) => {
            const sev = (i.severity || '').toLowerCase()
            const st = (i.status || '').toLowerCase()
            return (
              (sev.includes('critical') || sev.includes('high')) &&
              !st.includes('resolved') &&
              !st.includes('ignored')
            )
          }).length,
        )
      }
      setLastSync(new Date())
    } finally {
      setRefreshing(false)
    }
  }, [token])

  useEffect(() => {
    void refreshShell()
  }, [refreshShell])

  useEffect(() => {
    setMobileOpen(false)
  }, [location.pathname])

  const globalHealth = useMemo(() => aggregateGlobalHealth(healthStatuses), [healthStatuses])

  return (
    <div className="platform-shell platform-cockpit platform-cockpit-v2">
      <PlatformSidebar
        user={user}
        mobileOpen={mobileOpen}
        onCloseMobile={() => setMobileOpen(false)}
      />
      <div className="pc-workspace">
        <PlatformTopbar
          pageTitle={pageTitle}
          env={env}
          healthTone={globalHealth.tone}
          healthLabel={globalHealth.label}
          lastSync={lastSync}
          criticalCount={criticalCount}
          user={user}
          refreshing={refreshing}
          onRefresh={() => void refreshShell()}
          onOpenNav={() => setMobileOpen(true)}
        />
        <main className="pc-main">
          <Outlet />
        </main>
        <footer className="pc-footer">
          <button type="button" className="pc-btn pc-btn-ghost" onClick={logout}>
            Déconnexion
          </button>
        </footer>
      </div>
    </div>
  )
}

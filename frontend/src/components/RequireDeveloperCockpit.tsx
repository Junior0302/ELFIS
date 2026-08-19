import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../auth'
import { canAccessDeveloperCockpit } from '../developerCockpitNav'
import BootstrapLoadingScreen from '../platform-routing/BootstrapLoadingScreen'

/** Gate Cockpit Développeur : platform admin (flag) ou permissions techniques explicites. */
export default function RequireDeveloperCockpit() {
  const { user, loading } = useAuth()

  if (loading) {
    return <BootstrapLoadingScreen message="Vérification accès développeur…" />
  }
  if (!user) return <Navigate to="/login" replace />
  if (
    !canAccessDeveloperCockpit({
      isPlatformAdmin: Boolean(user.is_platform_admin),
    })
  ) {
    return <Navigate to="/dashboard" replace />
  }
  return <Outlet />
}

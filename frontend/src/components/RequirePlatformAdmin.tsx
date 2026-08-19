import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../auth'
import BootstrapLoadingScreen from '../platform-routing/BootstrapLoadingScreen'

export default function RequirePlatformAdmin() {
  const { user, loading } = useAuth()

  if (loading) {
    return <BootstrapLoadingScreen message="Vérification des droits plateforme…" />
  }
  if (!user) return <Navigate to="/login" replace />
  if (!user.is_platform_admin) return <Navigate to="/dashboard" replace />

  return <Outlet />
}

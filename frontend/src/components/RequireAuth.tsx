import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../auth'
import BootstrapLoadingScreen from '../platform-routing/BootstrapLoadingScreen'
import { locationReturnKey } from '../platform-routing/returnPath'

export default function RequireAuth() {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return <BootstrapLoadingScreen message="Chargement de votre session…" />
  }

  // Jamais !user → /home pendant restore : login + from = route demandée (path+query).
  if (!user) {
    return (
      <Navigate to="/login" replace state={{ from: locationReturnKey(location) }} />
    )
  }

  return <Outlet />
}

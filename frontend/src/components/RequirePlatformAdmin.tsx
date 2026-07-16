import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../auth'

export default function RequirePlatformAdmin() {
  const { user, loading } = useAuth()

  if (loading) return <div className="auth-boot">Vérification des droits plateforme…</div>
  if (!user) return <Navigate to="/login" replace />
  if (!user.is_platform_admin) return <Navigate to="/dashboard" replace />

  return <Outlet />
}

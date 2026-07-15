import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../auth'

export default function RequireAuth() {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return <div className="auth-boot">Chargement de votre session…</div>
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  return <Outlet />
}

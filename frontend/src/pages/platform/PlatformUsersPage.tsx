import { useEffect, useState } from 'react'
import { api, type PlatformUser } from '../../api'
import { useAuth } from '../../auth'

export default function PlatformUsersPage() {
  const { token } = useAuth()
  const [items, setItems] = useState<PlatformUser[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) return
    api.platformUsers(token)
      .then((result) => setItems(result.users))
      .catch((reason) => setError(reason instanceof Error ? reason.message : 'Liste indisponible'))
      .finally(() => setLoading(false))
  }, [token])

  return (
    <>
      <div className="platform-title">
        <span>Administration</span>
        <h1>Utilisateurs</h1>
        <p>{items.length} compte(s) enregistré(s).</p>
      </div>
      {error && <div className="platform-alert">{error}</div>}
      {loading ? <div className="platform-loading">Chargement…</div> : (
        <div className="platform-table-wrap">
          <table className="platform-table">
            <thead><tr><th>Utilisateur</th><th>Email</th><th>Organisations</th><th>Statut</th></tr></thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td>
                    <strong>{item.display_name || item.email}</strong>
                    <small>#{item.id}{item.is_platform_admin ? ' · super-admin' : ''}</small>
                  </td>
                  <td>{item.email}</td>
                  <td>{item.organization_count}</td>
                  <td><span className="platform-pill">{item.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
          {!items.length && <p className="platform-empty">Aucun utilisateur.</p>}
        </div>
      )}
    </>
  )
}

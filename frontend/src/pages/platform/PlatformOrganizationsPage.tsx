import { useEffect, useState } from 'react'
import { api, type PlatformOrganization } from '../../api'
import { useAuth } from '../../auth'
import { subscriptionLabels, subscriptionTone } from '../../subscription'

export default function PlatformOrganizationsPage() {
  const { token } = useAuth()
  const [items, setItems] = useState<PlatformOrganization[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) return
    api.platformOrganizations(token)
      .then((result) => setItems(result.organizations))
      .catch((reason) => setError(reason instanceof Error ? reason.message : 'Liste indisponible'))
      .finally(() => setLoading(false))
  }, [token])

  return (
    <>
      <div className="platform-title">
        <span>ELF Admin</span>
        <h1>Organisations</h1>
        <p>{items.length} organisation(s) sur la plateforme.</p>
      </div>
      {error && <div className="platform-alert">{error}</div>}
      {loading ? <div className="platform-loading">Chargement…</div> : (
        <div className="platform-table-wrap">
          <table className="platform-table">
            <thead><tr><th>Organisation</th><th>Pays</th><th>Utilisateurs</th><th>Abonnement</th></tr></thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td><strong>{item.legal_name || item.name}</strong><small>#{item.id}</small></td>
                  <td>{item.country}</td>
                  <td>{item.member_count}</td>
                  <td>
                    <span className={`subscription-badge ${subscriptionTone(item.subscription.status)}`}>
                      {subscriptionLabels[item.subscription.status]}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!items.length && <p className="platform-empty">Aucune organisation.</p>}
        </div>
      )}
    </>
  )
}

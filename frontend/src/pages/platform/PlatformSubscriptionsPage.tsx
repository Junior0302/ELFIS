import { useEffect, useState } from 'react'
import { api, formatEuro, type PlatformOrganization } from '../../api'
import { useAuth } from '../../auth'
import { formatDate, subscriptionLabels, subscriptionTone } from '../../subscription'

export default function PlatformSubscriptionsPage() {
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
        <h1>Abonnements</h1>
        <p>Suivi consolidé des essais, abonnements actifs et incidents de paiement.</p>
      </div>
      {error && <div className="platform-alert">{error}</div>}
      {loading ? <div className="platform-loading">Chargement…</div> : (
        <div className="platform-table-wrap">
          <table className="platform-table">
            <thead><tr><th>Organisation</th><th>Offre</th><th>Statut</th><th>Prix</th><th>Échéance</th></tr></thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td><strong>{item.legal_name || item.name}</strong><small>#{item.id}</small></td>
                  <td>{item.subscription.plan}</td>
                  <td>
                    <span className={`subscription-badge ${subscriptionTone(item.subscription.status)}`}>
                      {subscriptionLabels[item.subscription.status]}
                    </span>
                  </td>
                  <td>{formatEuro(item.subscription.price_eur)} / mois</td>
                  <td>
                    {formatDate(
                      item.subscription.status === 'trialing'
                        ? item.subscription.trial_end
                        : item.subscription.current_period_end,
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!items.length && <p className="platform-empty">Aucun abonnement.</p>}
        </div>
      )}
    </>
  )
}

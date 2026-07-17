import { useEffect, useState } from 'react'
import { api, formatEuro, type PlatformOrganization, type SubscriptionInfo } from '../../api'
import { useAuth } from '../../auth'
import { formatDate, subscriptionLabels, subscriptionTone } from '../../subscription'

export default function PlatformSubscriptionsPage() {
  const { token } = useAuth()
  const [items, setItems] = useState<PlatformOrganization[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [busyId, setBusyId] = useState<number | null>(null)
  const [aiSummary, setAiSummary] = useState('')

  const reload = () => {
    if (!token) return
    return api
      .platformOrganizations(token)
      .then((result) => setItems(result.organizations))
      .catch((reason) => setError(reason instanceof Error ? reason.message : 'Liste indisponible'))
  }

  useEffect(() => {
    if (!token) return
    reload()?.finally(() => setLoading(false))
  }, [token])

  const patchLocal = (organizationId: number, subscription: SubscriptionInfo) => {
    setItems((current) =>
      current.map((row) =>
        row.id === organizationId ? { ...row, subscription } : row,
      ),
    )
  }

  const runAction = async (
    organizationId: number,
    kind: 'sync' | 'revoke' | 'restore' | 'grant' | 'ai',
  ) => {
    if (!token) return
    setBusyId(organizationId)
    setError('')
    setMessage('')
    setAiSummary('')
    try {
      if (kind === 'sync') {
        const result = await api.platformSyncSubscription(organizationId, token)
        patchLocal(organizationId, result.subscription)
        setMessage(`Organisation #${organizationId} resynchronisée avec Stripe.`)
      } else if (kind === 'revoke') {
        const reason = window.prompt('Motif public de suspension (visible client) ?')
        if (!reason?.trim()) return
        const internal = window.prompt('Note interne (optionnelle) ?') || ''
        const result = await api.platformRevokeSubscription(
          organizationId,
          { reason_public: reason.trim(), reason_internal: internal },
          token,
        )
        patchLocal(organizationId, result.subscription)
        setMessage('Accès révoqué.')
      } else if (kind === 'restore') {
        if (!window.confirm('Restaurer l’accès interne pour cette organisation ?')) return
        const result = await api.platformRestoreSubscription(organizationId, {}, token)
        patchLocal(organizationId, result.subscription)
        setMessage('Accès restauré.')
      } else if (kind === 'grant') {
        const reason = window.prompt('Motif de réattribution d’essai (obligatoire) ?')
        if (!reason?.trim()) return
        const result = await api.platformGrantTrial(organizationId, { reason: reason.trim() }, token)
        patchLocal(organizationId, result.subscription)
        setMessage('Essai réattribué (admin_granted).')
      } else {
        const result = await api.platformAiSubscriptionSummary(organizationId, token)
        setAiSummary(
          `${result.summary}\n\nSuggestions (confirmation humaine requise) :\n- ${result.suggestions.join('\n- ') || 'Aucune'}`,
        )
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Action impossible')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <>
      <div className="platform-title">
        <span>ELF Admin</span>
        <h1>Abonnements</h1>
        <p>Suivi, resync Stripe, révocation, essai exceptionnel et résumé IA (lecture seule).</p>
      </div>
      {error && <div className="platform-alert">{error}</div>}
      {message && <div className="platform-alert platform-alert-ok">{message}</div>}
      {aiSummary && (
        <div className="platform-alert platform-alert-ok" style={{ whiteSpace: 'pre-wrap' }}>
          {aiSummary}
        </div>
      )}
      {loading ? (
        <div className="platform-loading">Chargement…</div>
      ) : (
        <div className="platform-table-wrap">
          <table className="platform-table">
            <thead>
              <tr>
                <th>Organisation</th>
                <th>Offre</th>
                <th>Statut</th>
                <th>Prix</th>
                <th>Échéance</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td>
                    <strong>{item.legal_name || item.name}</strong>
                    <small>#{item.id}</small>
                  </td>
                  <td>{item.subscription.plan}</td>
                  <td>
                    <span
                      className={`subscription-badge ${subscriptionTone(item.subscription.status)}`}
                    >
                      {item.subscription.label || subscriptionLabels[item.subscription.status]}
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
                  <td>
                    <div className="actions" style={{ marginTop: 0, flexWrap: 'wrap' }}>
                      <button
                        className="btn secondary"
                        type="button"
                        disabled={busyId === item.id}
                        onClick={() => void runAction(item.id, 'sync')}
                      >
                        Sync
                      </button>
                      <button
                        className="btn secondary"
                        type="button"
                        disabled={busyId === item.id}
                        onClick={() => void runAction(item.id, 'ai')}
                      >
                        IA
                      </button>
                      <button
                        className="btn secondary"
                        type="button"
                        disabled={busyId === item.id}
                        onClick={() => void runAction(item.id, 'grant')}
                      >
                        Essai
                      </button>
                      {item.subscription.admin_revoked ? (
                        <button
                          className="btn secondary"
                          type="button"
                          disabled={busyId === item.id}
                          onClick={() => void runAction(item.id, 'restore')}
                        >
                          Restaurer
                        </button>
                      ) : (
                        <button
                          className="btn secondary"
                          type="button"
                          disabled={busyId === item.id}
                          onClick={() => void runAction(item.id, 'revoke')}
                        >
                          Révoquer
                        </button>
                      )}
                    </div>
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

import { useEffect, useState } from 'react'
import { api, formatEuro, type PlatformOrganization, type SubscriptionInfo } from '../../api'
import { useAuth } from '../../auth'
import { formatDate, subscriptionLabels, subscriptionTone } from '../../subscription'

function pillClass(status: string) {
  const tone = subscriptionTone(status as never)
  if (tone === 'warn') return 'platform-pill platform-pill-warn'
  if (tone === 'danger') return 'platform-pill platform-pill-danger'
  if (tone === 'neutral') return 'platform-pill platform-pill-neutral'
  return 'platform-pill'
}

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
      current.map((row) => (row.id === organizationId ? { ...row, subscription } : row)),
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
        setMessage(`Organisation #${organizationId} resynchronisée.`)
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

  const trialing = items.filter((i) => i.subscription.status === 'trialing').length
  const active = items.filter((i) => i.subscription.status === 'active').length
  const none = items.filter((i) => i.subscription.status === 'none').length

  return (
    <>
      <div className="platform-title">
        <span>ELF Admin</span>
        <h1>Abonnements</h1>
        <p>Suivi, sync Stripe, essai exceptionnel, révocation et résumé IA.</p>
      </div>

      {error && <div className="platform-alert">{error}</div>}
      {message && <div className="platform-alert platform-alert-ok">{message}</div>}
      {aiSummary && (
        <div className="platform-alert platform-alert-ok platform-alert-pre">{aiSummary}</div>
      )}

      {!loading && (
        <div className="platform-stats" style={{ marginBottom: '1.25rem' }}>
          <article>
            <span>Organisations</span>
            <strong>{items.length}</strong>
          </article>
          <article>
            <span>Essais</span>
            <strong>{trialing}</strong>
          </article>
          <article>
            <span>Actifs</span>
            <strong>{active}</strong>
          </article>
          <article>
            <span>Sans abo</span>
            <strong>{none}</strong>
          </article>
        </div>
      )}

      {loading ? (
        <div className="platform-loading">Chargement…</div>
      ) : items.length === 0 ? (
        <div className="platform-loading platform-empty">Aucun abonnement.</div>
      ) : (
        <div className="platform-request-list">
          {items.map((item) => {
            const busy = busyId === item.id
            const status = item.subscription.status
            const label =
              item.subscription.label || subscriptionLabels[status] || status
            const deadline =
              status === 'trialing'
                ? item.subscription.trial_end
                : item.subscription.current_period_end
            return (
              <article key={item.id} className="platform-request-card">
                <header className="platform-request-head">
                  <div>
                    <h2>{item.legal_name || item.name}</h2>
                    <p>
                      #{item.id} · Offre {item.subscription.plan || 'pro'}
                    </p>
                  </div>
                  <span className={pillClass(status)}>{label}</span>
                </header>

                <dl className="platform-request-meta">
                  <div>
                    <dt>Prix</dt>
                    <dd>{formatEuro(item.subscription.price_eur)} / mois</dd>
                  </div>
                  <div>
                    <dt>Échéance</dt>
                    <dd>{formatDate(deadline) || '—'}</dd>
                  </div>
                  <div>
                    <dt>Membres</dt>
                    <dd>{item.member_count ?? '—'}</dd>
                  </div>
                  <div>
                    <dt>Statut technique</dt>
                    <dd>
                      <code>{status}</code>
                    </dd>
                  </div>
                </dl>

                <footer className="platform-request-actions">
                  <button
                    type="button"
                    className="platform-action platform-action-primary"
                    disabled={busy}
                    onClick={() => void runAction(item.id, 'sync')}
                  >
                    {busy ? '…' : 'Sync'}
                  </button>
                  <button
                    type="button"
                    className="platform-action"
                    disabled={busy}
                    onClick={() => void runAction(item.id, 'ai')}
                  >
                    IA
                  </button>
                  <button
                    type="button"
                    className="platform-action"
                    disabled={busy}
                    onClick={() => void runAction(item.id, 'grant')}
                  >
                    Essai
                  </button>
                  {item.subscription.admin_revoked ? (
                    <button
                      type="button"
                      className="platform-action platform-action-primary"
                      disabled={busy}
                      onClick={() => void runAction(item.id, 'restore')}
                    >
                      Restaurer
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="platform-action platform-action-danger"
                      disabled={busy}
                      onClick={() => void runAction(item.id, 'revoke')}
                    >
                      Révoquer
                    </button>
                  )}
                </footer>
              </article>
            )
          })}
        </div>
      )}
    </>
  )
}

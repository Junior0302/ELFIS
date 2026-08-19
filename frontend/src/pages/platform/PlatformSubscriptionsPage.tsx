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

type RevenueOverview = {
  mrr_eur: number
  arr_eur: number
  subscriptions: Record<string, number>
  subscriptions_total: number
  churn_cancelled_ratio_pct: number
  past_due: number
  trials: number
  note?: string
  source?: string
}

export default function PlatformSubscriptionsPage() {
  const { token } = useAuth()
  const [items, setItems] = useState<PlatformOrganization[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [busyId, setBusyId] = useState<number | null>(null)
  const [aiSummary, setAiSummary] = useState('')
  const [revenue, setRevenue] = useState<RevenueOverview | null>(null)
  const [engineSubs, setEngineSubs] = useState<Array<Record<string, unknown>>>([])
  const [statusFilter, setStatusFilter] = useState('')

  const reload = () => {
    if (!token) return
    return Promise.all([
      api.platformOrganizations(token).then((result) => setItems(result.organizations)),
      api.platformBillingOverview(token).then(setRevenue).catch(() => setRevenue(null)),
      api
        .platformBillingSubscriptionsList(token, {
          status: statusFilter || undefined,
          limit: 100,
        })
        .then((r) => setEngineSubs(r.subscriptions))
        .catch(() => setEngineSubs([])),
    ]).catch((reason) => setError(reason instanceof Error ? reason.message : 'Liste indisponible'))
  }

  useEffect(() => {
    if (!token) return
    reload()?.finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, statusFilter])

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
      await reload()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Action impossible')
    } finally {
      setBusyId(null)
    }
  }

  const runEngineAction = async (subscriptionId: string, kind: 'suspend' | 'restore') => {
    if (!token) return
    setError('')
    setMessage('')
    try {
      if (kind === 'suspend') {
        if (!window.confirm(`Suspendre l’abonnement ${subscriptionId} ?`)) return
        await api.platformBillingSuspend(subscriptionId, token)
        setMessage(`Abonnement ${subscriptionId} suspendu (auditée).`)
      } else {
        await api.platformBillingRestore(subscriptionId, token)
        setMessage(`Abonnement ${subscriptionId} réactivé (auditée).`)
      }
      await reload()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Action engine impossible')
    }
  }

  const trialing = items.filter((i) => i.subscription.status === 'trialing').length
  const active = items.filter((i) => i.subscription.status === 'active').length
  const none = items.filter((i) => i.subscription.status === 'none').length

  return (
    <>
      <div className="platform-title">
        <span>ELF Admin · Billing Cockpit V2</span>
        <h1>Abonnements</h1>
        <p>
          MRR/ARR depuis le Billing Engine · sync Stripe · suspension · essais · historique org.
        </p>
      </div>

      {error && <div className="platform-alert">{error}</div>}
      {message && <div className="platform-alert platform-alert-ok">{message}</div>}
      {aiSummary && (
        <div className="platform-alert platform-alert-ok platform-alert-pre">{aiSummary}</div>
      )}

      {revenue && (
        <div className="platform-stats" style={{ marginBottom: '1.25rem' }}>
          <article>
            <span>MRR</span>
            <strong>{formatEuro(revenue.mrr_eur)}</strong>
          </article>
          <article>
            <span>ARR</span>
            <strong>{formatEuro(revenue.arr_eur)}</strong>
          </article>
          <article>
            <span>Actifs (engine)</span>
            <strong>{revenue.subscriptions.active ?? 0}</strong>
          </article>
          <article>
            <span>Essais</span>
            <strong>{revenue.trials}</strong>
          </article>
          <article>
            <span>Impayés</span>
            <strong>{revenue.past_due}</strong>
          </article>
          <article>
            <span>Churn (proxy)</span>
            <strong>{revenue.churn_cancelled_ratio_pct} %</strong>
          </article>
        </div>
      )}
      {revenue?.note && <p className="muted" style={{ marginBottom: '1rem' }}>{revenue.note}</p>}

      {!loading && (
        <div className="platform-stats" style={{ marginBottom: '1.25rem' }}>
          <article>
            <span>Organisations</span>
            <strong>{items.length}</strong>
          </article>
          <article>
            <span>Essais (legacy vue)</span>
            <strong>{trialing}</strong>
          </article>
          <article>
            <span>Actifs (legacy vue)</span>
            <strong>{active}</strong>
          </article>
          <article>
            <span>Sans abo</span>
            <strong>{none}</strong>
          </article>
        </div>
      )}

      <div style={{ marginBottom: '1rem', display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
        <label className="muted">
          Filtre engine{' '}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            aria-label="Filtrer abonnements engine"
          >
            <option value="">Tous</option>
            <option value="active">active</option>
            <option value="trialing">trialing</option>
            <option value="past_due">past_due</option>
            <option value="suspended">suspended</option>
            <option value="cancelled">cancelled</option>
            <option value="expired">expired</option>
          </select>
        </label>
      </div>

      {engineSubs.length > 0 && (
        <section style={{ marginBottom: '1.5rem' }}>
          <h2 className="platform-section-title">Abonnements Billing Engine</h2>
          <div className="platform-request-list">
            {engineSubs.map((row) => {
              const sid = String(row.subscription_id || '')
              const st = String(row.status || '')
              return (
                <article key={sid} className="platform-request-card">
                  <header className="platform-request-head">
                    <div>
                      <h2>Org #{String(row.organization_id)}</h2>
                      <p>
                        {sid} · plan_id {String(row.plan_id || '—')}
                      </p>
                    </div>
                    <span className={pillClass(st)}>{st}</span>
                  </header>
                  <footer className="platform-request-actions">
                    {st === 'suspended' ? (
                      <button
                        type="button"
                        className="platform-action platform-action-primary"
                        onClick={() => void runEngineAction(sid, 'restore')}
                      >
                        Réactiver
                      </button>
                    ) : (
                      <button
                        type="button"
                        className="platform-action platform-action-danger"
                        onClick={() => void runEngineAction(sid, 'suspend')}
                      >
                        Suspendre
                      </button>
                    )}
                  </footer>
                </article>
              )
            })}
          </div>
        </section>
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

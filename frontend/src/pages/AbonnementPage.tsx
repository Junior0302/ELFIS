import { lazy, Suspense, useCallback, useEffect, useState } from 'react'
import { api, formatEuro, type SubscriptionInfo } from '../api'
import { useAuth } from '../auth'
import { shouldShowDevTrialButton } from '../devTrial'
import { useSubscription } from '../subscriptionContext'
import {
  canOpenSubscriptionPortal,
  canStartSubscriptionCheckout,
  countdownParts,
  formatDate,
  hasProductAccess,
  publicPlanDescription,
  remainingTime,
  subscriptionCheckoutLabel,
  subscriptionDeadline,
  subscriptionLabels,
  subscriptionPlanDisplay,
  subscriptionTone,
} from '../subscription'

/** Exclu du bundle prod : branche morte quand import.meta.env.DEV === false. */
const DevActivateTrialPanel = import.meta.env.DEV
  ? lazy(() => import('../components/DevActivateTrialPanel'))
  : null

type TabId = 'abonnement' | 'consommation' | 'historique' | 'paiements' | 'plans'

type QuotaRow = {
  quota_code?: string
  used_value?: number
  remaining?: number | null
  limit_value?: number | null
  percent_used?: number | null
  allowed?: boolean
}

const FEATURES = [
  'Accès à la plateforme ELFIS Core',
  'Espace Finance et gestion de facturation',
  'Gestion des clients, relations et documents',
  'Tableaux de bord et pilotage de l’activité',
  'Synchronisation bancaire lorsque disponible',
  'Fonctionnalités intelligentes ELFIS selon les modules activés',
  'Gestion de l’organisation, des membres et des permissions',
  'Stockage sécurisé des documents',
]

const TABS: { id: TabId; label: string }[] = [
  { id: 'abonnement', label: 'Mon abonnement' },
  { id: 'consommation', label: 'Consommation' },
  { id: 'historique', label: 'Historique' },
  { id: 'paiements', label: 'Paiements' },
  { id: 'plans', label: 'Changer de plan' },
]

function openBillingUrl(url: string) {
  const target = new URL(url, window.location.origin)
  if (!['http:', 'https:'].includes(target.protocol)) {
    throw new Error('Lien de paiement invalide')
  }
  window.location.assign(target.toString())
}

function statusBadgeLabel(sub: SubscriptionInfo, checkoutReturnPending: boolean) {
  if (sub.platform_bypass) return 'Accès ELF Admin'
  if (checkoutReturnPending) return 'Activation en cours'
  return sub.label || subscriptionLabels[sub.status]
}

function statusDescription(sub: SubscriptionInfo): string {
  switch (sub.status) {
    case 'none':
      return 'Votre compte ELFIS est actif. Démarrez votre essai gratuit pour accéder aux fonctionnalités incluses dans votre formule.'
    case 'checkout_pending':
    case 'incomplete':
      return 'La souscription n’est pas encore confirmée. Finalisez le paiement pour ouvrir l’accès à ELFIS Core.'
    case 'trialing':
      return `Votre essai est actif jusqu’au ${formatDate(sub.trial_end)}.`
    case 'active':
      return `Votre abonnement se renouvelle automatiquement le ${formatDate(sub.current_period_end || sub.next_billing_at)}.`
    case 'cancel_scheduled':
      return `Résiliation enregistrée. Accès conservé jusqu’au ${formatDate(sub.access_ends_at || sub.current_period_end)}.`
    case 'past_due':
      return `Paiement à régulariser. Mettez à jour votre moyen de paiement avant le ${formatDate(sub.grace_until)}.`
    case 'admin_revoked':
      return `Accès suspendu par l’administration. Motif : ${sub.admin_revoked_reason_public || 'non précisé'}.`
    case 'canceled':
    case 'expired':
      return 'Votre abonnement n’est plus actif. Vos données sont conservées ; les fonctions incluses sont désactivées.'
    default:
      return sub.label || subscriptionLabels[sub.status]
  }
}

function formatQuotaLabel(code: string) {
  return code.replace(/\./g, ' · ').replace(/_/g, ' ')
}

function CountdownBoard({
  deadline,
  now,
}: {
  deadline: string | null
  now: number
}) {
  const parts = countdownParts(deadline, now)
  if (!parts) {
    return <p className="muted">Échéance non disponible pour le moment.</p>
  }
  if (parts.ended) {
    return (
      <div className="trial-countdown ended">
        <span className="trial-countdown-label">Temps restant sur l’essai</span>
        <strong>Terminé</strong>
      </div>
    )
  }
  return (
    <div className="trial-countdown">
      <span className="trial-countdown-label">Temps restant sur l’essai</span>
      <div className="trial-countdown-grid" aria-label={remainingTime(deadline, now) || undefined}>
        <div>
          <strong>{parts.days}</strong>
          <span>Jours</span>
        </div>
        <div>
          <strong>{String(parts.hours).padStart(2, '0')}</strong>
          <span>Heures</span>
        </div>
        <div>
          <strong>{String(parts.minutes).padStart(2, '0')}</strong>
          <span>Minutes</span>
        </div>
        <div>
          <strong>{String(parts.seconds).padStart(2, '0')}</strong>
          <span>Secondes</span>
        </div>
      </div>
      <p className="trial-countdown-date">Votre essai ELFIS Core se termine le {formatDate(deadline)}.</p>
    </div>
  )
}

export default function AbonnementPage() {
  const { token, orgId, memberships, user } = useAuth()
  const {
    subscription,
    loading,
    refresh,
    setSubscription,
    setCheckoutReturnPending,
    checkoutReturnPending,
  } = useSubscription()
  const [tab, setTab] = useState<TabId>('abonnement')
  const [action, setAction] = useState<'checkout' | 'portal' | 'sync' | null>(null)
  const [error, setError] = useState('')
  const [returnNotice, setReturnNotice] = useState('')
  const [now, setNow] = useState(Date.now())
  const [renewalOk, setRenewalOk] = useState(false)
  const [termsOk, setTermsOk] = useState(false)
  const [engineOverview, setEngineOverview] = useState<Record<string, unknown> | null>(null)
  const [plans, setPlans] = useState<Array<Record<string, unknown>>>([])
  const [quotas, setQuotas] = useState<Record<string, QuotaRow>>({})
  const [history, setHistory] = useState<Array<Record<string, unknown>>>([])
  const [selectedPlan, setSelectedPlan] = useState('starter')
  const [engineLoading, setEngineLoading] = useState(false)

  const loadEngine = useCallback(async () => {
    if (!token || !orgId) return
    setEngineLoading(true)
    try {
      const [overviewRes, quotasRes, historyRes] = await Promise.all([
        api.saasBillingOverview(token, orgId),
        api.saasBillingQuotas(token, orgId),
        api.saasBillingHistory(token, orgId),
      ])
      setEngineOverview(overviewRes.overview)
      setPlans(overviewRes.plans || [])
      setQuotas((quotasRes.quotas || {}) as Record<string, QuotaRow>)
      setHistory(historyRes.events || [])
    } catch {
      /* legacy subscription reste utilisable si engine indisponible */
    } finally {
      setEngineLoading(false)
    }
  }, [token, orgId])

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    let checkoutReturn: 'success' | 'cancel' | undefined
    const sessionId = params.get('session_id')
    if (params.has('success') || params.get('checkout') === 'success') {
      checkoutReturn = 'success'
    } else if (params.has('canceled') || params.get('checkout') === 'cancel') {
      checkoutReturn = 'cancel'
    }
    if (params.size > 0) window.history.replaceState({}, '', window.location.pathname)

    void (async () => {
      if (checkoutReturn === 'success') {
        setCheckoutReturnPending(true)
        setReturnNotice('Votre abonnement ELFIS est en cours d’activation.')
        setError('')
        let current = await refresh({ syncSessionId: sessionId })
        if (!hasProductAccess(current)) {
          await new Promise((resolve) => window.setTimeout(resolve, 1800))
          current = await refresh({ syncSessionId: sessionId })
        }
        if (hasProductAccess(current)) {
          setReturnNotice('Votre abonnement ELFIS est activé.')
          setCheckoutReturnPending(false)
          const { trackProductEvent } = await import('../productEvents')
          trackProductEvent('trial_activation_completed', { path: '/abonnement' })
        } else {
          setReturnNotice(
            'Votre abonnement ELFIS est en cours d’activation. Cliquez sur Actualiser si l’état n’apparaît pas encore.',
          )
          setCheckoutReturnPending(false)
        }
        await loadEngine()
        return
      }
      if (checkoutReturn === 'cancel') {
        setReturnNotice('Le paiement a été annulé. Aucun abonnement n’a été créé.')
        setCheckoutReturnPending(false)
        await refresh()
        await loadEngine()
        return
      }
      await refresh()
      await loadEngine()
    })()
  }, [refresh, setCheckoutReturnPending, loadEngine])

  useEffect(() => {
    const tickMs =
      subscription?.status === 'trialing' || subscription?.status === 'cancel_scheduled'
        ? 1000
        : 60_000
    const timer = window.setInterval(() => setNow(Date.now()), tickMs)
    return () => window.clearInterval(timer)
  }, [subscription?.status])

  const startAction = async (kind: 'checkout' | 'portal') => {
    if (!token || !orgId) return
    if (kind === 'checkout' && (!renewalOk || !termsOk)) {
      setError('Veuillez accepter le renouvellement automatique et les conditions.')
      return
    }
    setAction(kind)
    setError('')
    try {
      const result =
        kind === 'checkout'
          ? await api.createSubscriptionCheckout(token, orgId, {
              automatic_renewal_accepted: renewalOk,
              terms_accepted: termsOk,
            })
          : await api.createSubscriptionPortal(token, orgId)
      openBillingUrl(result.url)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Redirection paiement impossible')
      setAction(null)
    }
  }

  const statusForActions = (subscription?.status || 'none') as SubscriptionInfo['status']
  const canUsePortal =
    subscription && !subscription.platform_bypass && canOpenSubscriptionPortal(statusForActions)
  const canCheckout =
    subscription &&
    !hasProductAccess(subscription) &&
    !checkoutReturnPending &&
    canStartSubscriptionCheckout(statusForActions)
  const activeMembership = memberships.find((membership) => membership.organization_id === orgId)
  const canManage = Boolean(
    activeMembership?.permissions.includes('*') ||
      activeMembership?.permissions.includes('subscription.manage'),
  )
  const isElfAdmin = Boolean(user?.is_platform_admin || subscription?.platform_bypass)
  const deadline = subscriptionDeadline(subscription)
  const isTrialing = subscription?.status === 'trialing'
  const isActiveAccess = hasProductAccess(subscription)
  const planCode = String(engineOverview?.plan_code || subscription?.plan_code || subscription?.plan || 'starter')
  const planDisplay = subscriptionPlanDisplay(planCode)
  const selectedCatalog = plans.find((plan) => String(plan.plan_code || '') === selectedPlan)
  const catalogPrice = Number(
    selectedCatalog?.price_amount ?? subscription?.price_eur ?? 0,
  )
  const priceLabel = catalogPrice > 0 ? formatEuro(catalogPrice) : null
  const trialDays = Number(selectedCatalog?.trial_days || 14) || 14
  const checkoutCta = subscription
    ? subscriptionCheckoutLabel(subscription.status, subscription.trial_used, priceLabel || undefined)
    : 'Démarrer mon essai gratuit'

  const quotaEntries = Object.entries(quotas)

  return (
    <div className="page elfis-billing-page">
      <div className="page-head">
        <div>
          <p className="home-eyebrow">ELFIS Core</p>
          <h2>Abonnement et facturation</h2>
          <p>
            Gérez votre formule ELFIS Core, votre période d’essai et vos informations de facturation.
          </p>
        </div>
      </div>

      <div className="billing-v2-tabs" role="tablist" aria-label="Sections abonnement">
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={tab === item.id}
            className={tab === item.id ? 'btn' : 'btn secondary'}
            onClick={() => setTab(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>

      {returnNotice && (
        <div className="subscription-return" role="status">
          {returnNotice}
        </div>
      )}
      {isElfAdmin && (
        <div className="subscription-return" role="status">
          Compte ELF Admin : accès complet, sans abonnement requis.
        </div>
      )}
      {error && (
        <div className="auth-alert auth-alert-error" role="alert">
          {error}
        </div>
      )}

      {tab === 'abonnement' && (
        <>
          {loading && !subscription ? (
            <div className="loading">Vérification du statut…</div>
          ) : isActiveAccess && subscription ? (
            <section className="panel subscription-active-panel" aria-labelledby="elfis-sub-title">
              <p className="home-eyebrow">Votre abonnement</p>
              <div className="subscription-status-line">
                <div>
                  <h3 id="elfis-sub-title">{planDisplay.short}</h3>
                  <p className="muted">
                    {planDisplay.brand} · {priceLabel || formatEuro(subscription.price_eur || 0)} / mois
                  </p>
                </div>
                <span className={`subscription-badge ${subscriptionTone(subscription.status)}`}>
                  {statusBadgeLabel(subscription, checkoutReturnPending)}
                </span>
              </div>

              <p className="muted">{statusDescription(subscription)}</p>
              {engineLoading ? <p className="muted">Actualisation…</p> : null}

              {isTrialing ? (
                <CountdownBoard deadline={deadline} now={now} />
              ) : (
                <div className="subscription-active-meta">
                  <p>
                    {subscription.status === 'cancel_scheduled' ? 'Fin d’accès' : 'Prochain renouvellement'}{' '}
                    : <strong>{formatDate(deadline)}</strong>
                  </p>
                  {deadline && <p className="muted">{remainingTime(deadline, now)} restant</p>}
                </div>
              )}

              <div className="subscription-active-actions">
                {canUsePortal && canManage && (
                  <button
                    className="btn"
                    type="button"
                    disabled={Boolean(action)}
                    onClick={() => void startAction('portal')}
                  >
                    {action === 'portal' ? 'Ouverture…' : 'Gérer mon abonnement'}
                  </button>
                )}
                {canManage && (
                  <button
                    className="btn secondary"
                    type="button"
                    disabled={Boolean(action)}
                    onClick={() => {
                      setAction('sync')
                      void (async () => {
                        try {
                          const current = await refresh()
                          if (current) setSubscription(current)
                          await loadEngine()
                          setReturnNotice('Statut à jour.')
                          setCheckoutReturnPending(false)
                        } catch (reason) {
                          setError(
                            reason instanceof Error ? reason.message : 'Actualisation impossible',
                          )
                        } finally {
                          setAction(null)
                        }
                      })()
                    }}
                  >
                    {action === 'sync' ? 'Actualisation…' : 'Actualiser'}
                  </button>
                )}
              </div>
            </section>
          ) : (
            <div className="subscription-grid">
              <section className="panel pricing-card" aria-labelledby="elfis-offer-title">
                <span className="home-eyebrow">Formule</span>
                <p className="elfis-billing-brand">{planDisplay.brand}</p>
                <h3 id="elfis-offer-title">{planDisplay.plan}</h3>
                <div className="pricing-amount">
                  <strong>{priceLabel || '—'}</strong>
                  {priceLabel ? <span>/ mois</span> : null}
                </div>
                <p className="muted">
                  Essai gratuit de {trialDays} jours. Renouvellement mensuel. Sans engagement,
                  résiliable avant le prochain renouvellement.
                </p>
                <p className="elfis-billing-features-title">Inclus dans {planDisplay.short}</p>
                <ul className="pricing-features">
                  {FEATURES.map((item) => (
                    <li key={item}>
                      <span className="elfis-billing-check" aria-hidden="true" />
                      {item}
                    </li>
                  ))}
                </ul>

                {canCheckout && canManage && (
                  <div className="subscription-consents">
                    <label className="checkbox-inline">
                      <input
                        type="checkbox"
                        checked={renewalOk}
                        onChange={(e) => setRenewalOk(e.target.checked)}
                      />
                      J’ai compris que mon essai gratuit se transformera automatiquement en
                      abonnement mensuel au tarif indiqué, sauf résiliation avant la fin de l’essai.
                    </label>
                    <label className="checkbox-inline">
                      <input
                        type="checkbox"
                        checked={termsOk}
                        onChange={(e) => setTermsOk(e.target.checked)}
                      />
                      J’accepte les Conditions générales d’utilisation, les conditions d’abonnement
                      et la Politique de confidentialité.
                    </label>
                    <button
                      className="btn subscription-main-action"
                      type="button"
                      disabled={
                        Boolean(action) ||
                        subscription?.configured === false ||
                        !renewalOk ||
                        !termsOk
                      }
                      onClick={() => void startAction('checkout')}
                    >
                      {action === 'checkout'
                        ? 'Ouverture du paiement sécurisé…'
                        : subscription?.configured === false
                          ? 'Paiement bientôt disponible'
                          : checkoutCta}
                    </button>
                    {subscription?.configured !== false && (
                      <p className="muted elfis-billing-cta-hint">
                        {trialDays} jours gratuits
                        {priceLabel ? ` · puis ${priceLabel}/mois` : ''}
                        {' · résiliable à tout moment'}
                      </p>
                    )}
                  </div>
                )}
                {DevActivateTrialPanel &&
                shouldShowDevTrialButton(subscription?.configured) &&
                canManage ? (
                  <Suspense fallback={null}>
                    <DevActivateTrialPanel />
                  </Suspense>
                ) : null}
                {!canManage && (
                  <p className="muted">
                    Contactez le propriétaire de l’organisation pour modifier l’abonnement.
                  </p>
                )}
              </section>

              <section className="panel subscription-status-card" aria-labelledby="elfis-status-title">
                <p className="home-eyebrow">Votre abonnement</p>
                <h3 id="elfis-status-title">
                  {subscription?.status === 'none' || !subscription
                    ? 'Aucun abonnement actif'
                    : planDisplay.short}
                </h3>
                {subscription ? (
                  <>
                    <div className="subscription-status-line">
                      <span className={`subscription-badge ${subscriptionTone(subscription.status)}`}>
                        {statusBadgeLabel(subscription, checkoutReturnPending)}
                      </span>
                    </div>
                    <p className="muted" style={{ marginTop: '1rem' }}>
                      {checkoutReturnPending
                        ? 'Votre abonnement ELFIS est en cours d’activation.'
                        : statusDescription(subscription)}
                    </p>
                  </>
                ) : (
                  <p className="muted">Statut indisponible.</p>
                )}
              </section>
            </div>
          )}
        </>
      )}

      {tab === 'consommation' && (
        <section className="panel">
          <h3>Consommation</h3>
          <p className="muted">Suivi des volumes utilisés par votre organisation.</p>
          {quotaEntries.length === 0 ? (
            <p className="muted">Aucune donnée de consommation pour le moment.</p>
          ) : (
            <div className="platform-request-list">
              {quotaEntries.map(([code, row]) => {
                const used = Number(row.used_value ?? 0)
                const limit = row.limit_value
                const remaining =
                  row.remaining != null
                    ? row.remaining
                    : limit == null
                      ? null
                      : Math.max(0, Number(limit) - used)
                const pct =
                  row.percent_used != null
                    ? row.percent_used
                    : limit
                      ? Math.min(100, Math.round((used / Number(limit)) * 100))
                      : null
                return (
                  <article key={code} className="platform-request-card">
                    <header className="platform-request-head">
                      <div>
                        <h2>{formatQuotaLabel(code)}</h2>
                        <p>
                          Utilisé {used}
                          {limit != null ? ` / ${limit}` : ' · illimité'}
                          {remaining != null ? ` · restant ${remaining}` : ''}
                          {pct != null ? ` · ${pct} %` : ''}
                        </p>
                      </div>
                    </header>
                  </article>
                )
              })}
            </div>
          )}
        </section>
      )}

      {tab === 'historique' && (
        <section className="panel">
          <h3>Historique</h3>
          <p className="muted">Événements liés à votre abonnement ELFIS.</p>
          {history.length === 0 ? (
            <p className="muted">Aucun événement pour le moment.</p>
          ) : (
            <ul className="pricing-features">
              {history.map((ev) => (
                <li key={String(ev.billing_event_id || ev.event_type)}>
                  <strong>{String(ev.event_type || 'event')}</strong> — {String(ev.status || '—')} —{' '}
                  {String(ev.received_at || '—')}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {tab === 'paiements' && (
        <section className="panel">
          <h3>Paiements</h3>
          <p className="muted">
            Gérez votre carte, vos factures et votre résiliation depuis l’espace de facturation
            sécurisé.
          </p>
          {canManage && (
            <button
              className="btn"
              type="button"
              disabled={Boolean(action) || !canUsePortal}
              onClick={() => void startAction('portal')}
            >
              {action === 'portal' ? 'Ouverture…' : 'Gérer la facturation'}
            </button>
          )}
          {!canUsePortal && (
            <p className="muted" style={{ marginTop: '0.75rem' }}>
              L’espace de facturation sera disponible dès qu’un abonnement sera associé à ce compte.
            </p>
          )}
        </section>
      )}

      {tab === 'plans' && (
        <section className="panel">
          <h3>Changer de plan</h3>
          <p className="muted">Choisissez la formule ELFIS Core adaptée à votre organisation.</p>
          <div className="subscription-grid">
            {plans.map((plan) => {
              const code = String(plan.plan_code || '')
              const display = subscriptionPlanDisplay(code)
              const price = Number(plan.price_amount || 0)
              const purchasable = Boolean(plan.purchasable)
              const interval = String(plan.billing_interval || 'month')
              const intervalLabel = interval === 'month' ? 'mois' : interval
              return (
                <article key={code} className="panel pricing-card">
                  <p className="elfis-billing-brand">{display.brand}</p>
                  <h3>{display.plan}</h3>
                  <div className="pricing-amount">
                    <strong>{price > 0 ? formatEuro(price) : 'Sur devis'}</strong>
                    {price > 0 && <span>/ {intervalLabel}</span>}
                  </div>
                  <p className="muted">
                    {publicPlanDescription(
                      String(plan.description || ''),
                      'Formule ELFIS Core, renouvellement mensuel.',
                    )}
                  </p>
                  {canManage && purchasable && (
                    <button
                      className="btn secondary"
                      type="button"
                      onClick={() => {
                        setSelectedPlan(code)
                        setTab('abonnement')
                        setReturnNotice(`Formule sélectionnée : ${display.short}. Lancez l’essai.`)
                      }}
                    >
                      {planCode === code || planDisplay.code === code
                        ? 'Formule actuelle / sélectionnée'
                        : 'Choisir'}
                    </button>
                  )}
                  {!purchasable && <p className="muted">Contact commercial requis.</p>}
                </article>
              )
            })}
          </div>
          {canCheckout && canManage && (
            <div className="subscription-consents" style={{ marginTop: '1rem' }}>
              <label className="checkbox-inline">
                <input
                  type="checkbox"
                  checked={renewalOk}
                  onChange={(e) => setRenewalOk(e.target.checked)}
                />
                J’ai compris que mon essai gratuit se transformera automatiquement en abonnement
                mensuel au tarif indiqué, sauf résiliation avant la fin de l’essai.
              </label>
              <label className="checkbox-inline">
                <input
                  type="checkbox"
                  checked={termsOk}
                  onChange={(e) => setTermsOk(e.target.checked)}
                />
                J’accepte les Conditions générales d’utilisation, les conditions d’abonnement et la
                Politique de confidentialité.
              </label>
              <button
                className="btn"
                type="button"
                disabled={Boolean(action) || !renewalOk || !termsOk}
                onClick={() => void startAction('checkout')}
              >
                {subscriptionCheckoutLabel(
                  subscription?.status || 'none',
                  subscription?.trial_used,
                  priceLabel || undefined,
                )}
              </button>
            </div>
          )}
        </section>
      )}
    </div>
  )
}

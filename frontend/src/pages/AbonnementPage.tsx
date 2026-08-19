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
  formatDateTime,
  hasProductAccess,
  remainingTime,
  subscriptionCheckoutLabel,
  subscriptionDeadline,
  subscriptionLabels,
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
  'Analyse intelligente de documents comptables',
  'Extraction des informations de factures',
  'Assistance comptable par intelligence artificielle',
  'Gestion des factures, devis, clients et catalogue',
  'Tableaux de bord, historique et exports',
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

function CountdownBoard({
  deadline,
  now,
  label,
}: {
  deadline: string | null
  now: number
  label: string
}) {
  const parts = countdownParts(deadline, now)
  if (!parts) {
    return <p className="muted">Échéance non disponible pour le moment.</p>
  }
  if (parts.ended) {
    return (
      <div className="trial-countdown ended">
        <span className="trial-countdown-label">{label}</span>
        <strong>Terminé</strong>
      </div>
    )
  }
  return (
    <div className="trial-countdown">
      <span className="trial-countdown-label">{label}</span>
      <div className="trial-countdown-grid" aria-label={remainingTime(deadline, now) || undefined}>
        <div>
          <strong>{parts.days}</strong>
          <span>jours</span>
        </div>
        <div>
          <strong>{String(parts.hours).padStart(2, '0')}</strong>
          <span>heures</span>
        </div>
        <div>
          <strong>{String(parts.minutes).padStart(2, '0')}</strong>
          <span>min</span>
        </div>
        <div>
          <strong>{String(parts.seconds).padStart(2, '0')}</strong>
          <span>sec</span>
        </div>
      </div>
      <p className="trial-countdown-date">Jusqu’au {formatDateTime(deadline)}</p>
    </div>
  )
}

function statusDescription(sub: SubscriptionInfo): string {
  switch (sub.status) {
    case 'none':
      return 'Votre compte est actif, mais aucun abonnement ComptaPilot IA n’est associé à cette organisation.'
    case 'checkout_pending':
    case 'incomplete':
      return 'La souscription n’est pas encore confirmée. Finalisez le paiement sécurisé pour ouvrir l’accès.'
    case 'trialing':
      return `Essai actif jusqu’au ${formatDateTime(sub.trial_end)}. Renouvellement automatique ensuite, sauf annulation avant cette date.`
    case 'cancel_scheduled':
      return `Résiliation enregistrée. Accès conservé jusqu’au ${formatDateTime(sub.access_ends_at || sub.current_period_end)}.`
    case 'past_due':
      return `Le renouvellement a échoué. Mettez à jour votre moyen de paiement avant le ${formatDate(sub.grace_until)}.`
    case 'admin_revoked':
      return `Accès suspendu par l’administration. Motif : ${sub.admin_revoked_reason_public || 'non précisé'}.`
    case 'canceled':
    case 'expired':
      return 'Votre abonnement n’est plus actif. Vos données sont conservées ; les fonctions premium sont désactivées.'
    default:
      return sub.label || subscriptionLabels[sub.status]
  }
}

function formatQuotaLabel(code: string) {
  return code.replace(/\./g, ' · ').replace(/_/g, ' ')
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
        setReturnNotice('Vérification du paiement…')
        setError('')
        let current = await refresh({ syncSessionId: sessionId })
        if (!hasProductAccess(current)) {
          await new Promise((resolve) => window.setTimeout(resolve, 1800))
          current = await refresh({ syncSessionId: sessionId })
        }
        if (hasProductAccess(current)) {
          setReturnNotice('Essai activé. Votre accès ComptaPilot IA est ouvert.')
          setCheckoutReturnPending(false)
          const { trackProductEvent } = await import('../productEvents')
          trackProductEvent('trial_activation_completed', { path: '/abonnement' })
        } else {
          setReturnNotice(
            'Le paiement a bien été reçu. L’activation peut prendre quelques instants — cliquez sur Actualiser.',
          )
          setCheckoutReturnPending(false)
        }
        await loadEngine()
        return
      }
      if (checkoutReturn === 'cancel') {
        setReturnNotice('Paiement interrompu. Vous pouvez reprendre quand vous voulez.')
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

  const startAction = async (kind: 'checkout' | 'portal', planCode?: string) => {
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
          ? await api.saasBillingCheckout(
              {
                plan_code: planCode || selectedPlan,
                automatic_renewal_accepted: renewalOk,
                terms_accepted: termsOk,
              },
              token,
              orgId,
            )
          : await api.saasBillingPortal(token, orgId)
      openBillingUrl(result.url)
    } catch (reason) {
      // Fallback legacy si checkout V2 indisponible
      try {
        const fallback =
          kind === 'checkout'
            ? await api.createSubscriptionCheckout(token, orgId, {
                automatic_renewal_accepted: renewalOk,
                terms_accepted: termsOk,
              })
            : await api.createSubscriptionPortal(token, orgId)
        openBillingUrl(fallback.url)
      } catch (fallbackReason) {
        setError(
          fallbackReason instanceof Error
            ? fallbackReason.message
            : reason instanceof Error
              ? reason.message
              : 'Redirection paiement impossible',
        )
        setAction(null)
      }
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
  const planCode = String(engineOverview?.plan_code || subscription?.plan || 'starter')
  const trialDaysLeft =
    typeof engineOverview?.trial_days_remaining === 'number'
      ? engineOverview.trial_days_remaining
      : null

  const quotaEntries = Object.entries(quotas)

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Abonnement et facturation</h2>
          <p>
            Billing System V2 — plans, essai, quotas et droits pilotés par l’Entitlement Engine.
            Stripe synchronise les paiements ; il n’est pas la source de vérité.
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

      {returnNotice && <div className="subscription-return">{returnNotice}</div>}
      {isElfAdmin && (
        <div className="subscription-return">
          Compte ELF Admin : accès complet, sans abonnement requis.
        </div>
      )}
      {error && <div className="auth-alert auth-alert-error">{error}</div>}

      {tab === 'abonnement' && (
        <>
          {engineOverview && (
            <section className="panel" style={{ marginBottom: '1rem' }}>
              <h3>État Billing Engine</h3>
              <p className="muted">
                Plan <strong>{planCode}</strong> · Statut{' '}
                <strong>{String(engineOverview.status || '—')}</strong>
                {engineOverview.is_trial ? (
                  <>
                    {' '}
                    · Essai
                    {trialDaysLeft != null ? ` · ${trialDaysLeft} j restants` : ''}
                  </>
                ) : null}
                {' · '}
                Accès produit : {engineOverview.has_product_access ? 'oui' : 'non'}
                {engineLoading ? ' · Actualisation…' : ''}
              </p>
            </section>
          )}

          {loading && !subscription ? (
            <div className="loading">Vérification du statut…</div>
          ) : isActiveAccess && subscription ? (
            <section className="panel subscription-active-panel">
              <div className="subscription-status-line">
                <span className={`subscription-badge ${subscriptionTone(subscription.status)}`}>
                  {subscription.platform_bypass
                    ? 'Accès ELF Admin'
                    : subscription.label || subscriptionLabels[subscription.status]}
                </span>
                <strong>
                  {planCode} · {formatEuro(subscription.price_eur || 0)} / mois (catalogue)
                </strong>
              </div>

              <p className="muted">{statusDescription(subscription)}</p>

              {isTrialing ? (
                <CountdownBoard deadline={deadline} now={now} label="Temps restant sur l’essai" />
              ) : (
                <div className="subscription-active-meta">
                  <p>
                    {subscription.status === 'cancel_scheduled' ? 'Fin d’accès' : 'Prochaine échéance'}{' '}
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
                    {action === 'portal' ? 'Ouverture…' : 'Gérer la carte, annuler ou factures'}
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
              <section className="panel pricing-card">
                <span className="home-eyebrow">Offre catalogue</span>
                <h3>ComptaPilot IA</h3>
                <p className="muted">
                  Essai gratuit · Renouvellement mensuel · Prix affichés via le catalogue plans (pas
                  codés en dur Stripe).
                </p>
                <ul className="pricing-features">
                  {FEATURES.map((item) => (
                    <li key={item}>{item}</li>
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
                      J’ai compris l’essai gratuit et le renouvellement automatique au tarif du plan
                      choisi, sauf annulation avant la fin de l’essai.
                    </label>
                    <label className="checkbox-inline">
                      <input
                        type="checkbox"
                        checked={termsOk}
                        onChange={(e) => setTermsOk(e.target.checked)}
                      />
                      J’accepte les conditions générales d’utilisation, les conditions de
                      l’abonnement et la politique de confidentialité.
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
                      onClick={() => void startAction('checkout', selectedPlan)}
                    >
                      {action === 'checkout'
                        ? 'Ouverture du paiement sécurisé…'
                        : subscription?.configured === false
                          ? 'Paiement bientôt disponible'
                          : subscriptionCheckoutLabel(
                              subscription!.status,
                              subscription?.trial_used,
                            )}
                    </button>
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

              <section className="panel subscription-status-card">
                <h3>Statut actuel</h3>
                {subscription ? (
                  <>
                    <div className="subscription-status-line">
                      <span className={`subscription-badge ${subscriptionTone(subscription.status)}`}>
                        {checkoutReturnPending
                          ? 'Activation en cours'
                          : subscription.label || subscriptionLabels[subscription.status]}
                      </span>
                    </div>
                    <p className="muted" style={{ marginTop: '1rem' }}>
                      {checkoutReturnPending
                        ? 'Nous confirmons votre paiement.'
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
          <h3>Quotas & consommation</h3>
          <p className="muted">Utilisé · restant · limite · pourcentage — via Entitlement Engine.</p>
          {quotaEntries.length === 0 ? (
            <p className="muted">Aucun quota publié pour cette organisation.</p>
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
          <h3>Historique billing</h3>
          <p className="muted">Événements journalisés (webhooks idempotents inclus).</p>
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
            Cartes, factures Stripe et annulation : portail client. L’état métier reste dans le Billing
            Engine.
          </p>
          {canManage && (
            <button
              className="btn"
              type="button"
              disabled={Boolean(action) || !canUsePortal}
              onClick={() => void startAction('portal')}
            >
              {action === 'portal' ? 'Ouverture…' : 'Ouvrir le portail de paiement'}
            </button>
          )}
          {!canUsePortal && (
            <p className="muted" style={{ marginTop: '0.75rem' }}>
              Portail indisponible pour le statut actuel.
            </p>
          )}
        </section>
      )}

      {tab === 'plans' && (
        <section className="panel">
          <h3>Changer de plan</h3>
          <p className="muted">
            Catalogue public — prix catalogue indicatifs ; facturation réelle via Stripe Price ID
            (configuration serveur).
          </p>
          <div className="subscription-grid">
            {plans.map((plan) => {
              const code = String(plan.plan_code || '')
              const price = Number(plan.price_amount || 0)
              const purchasable = Boolean(plan.purchasable)
              return (
                <article key={code} className="panel pricing-card">
                  <h3>{String(plan.name || code)}</h3>
                  <div className="pricing-amount">
                    <strong>{price > 0 ? formatEuro(price) : 'Sur devis'}</strong>
                    {price > 0 && <span>/ {String(plan.billing_interval || 'month')}</span>}
                  </div>
                  <p className="muted">{String(plan.description || '')}</p>
                  {canManage && purchasable && (
                    <button
                      className="btn secondary"
                      type="button"
                      onClick={() => {
                        setSelectedPlan(code)
                        setTab('abonnement')
                        setReturnNotice(`Plan sélectionné : ${plan.name || code}. Lancez le checkout.`)
                      }}
                    >
                      {planCode === code ? 'Plan actuel / sélectionné' : 'Choisir'}
                    </button>
                  )}
                  {!purchasable && (
                    <p className="muted">Contact commercial requis.</p>
                  )}
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
                Renouvellement automatique accepté
              </label>
              <label className="checkbox-inline">
                <input
                  type="checkbox"
                  checked={termsOk}
                  onChange={(e) => setTermsOk(e.target.checked)}
                />
                Conditions acceptées
              </label>
              <button
                className="btn"
                type="button"
                disabled={Boolean(action) || !renewalOk || !termsOk}
                onClick={() => void startAction('checkout', selectedPlan)}
              >
                Souscrire au plan {selectedPlan}
              </button>
            </div>
          )}
        </section>
      )}
    </>
  )
}

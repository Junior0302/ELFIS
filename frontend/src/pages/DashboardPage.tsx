import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  api,
  formatEuro,
  type BillingOverview,
  type DashboardStats,
  type PilotOverview,
  type SubscriptionInfo,
} from '../api'
import { useAuth } from '../auth'
import {
  NavIconActivities,
  NavIconBilling,
  NavIconCatalog,
  NavIconClients,
  NavIconCopilote,
  NavIconDeposit,
  NavIconOrg,
  NavIconTeam,
} from '../components/NavIcons'
import StatusBadge from '../components/StatusBadge'
import {
  canStartSubscriptionCheckout,
  formatDate,
  remainingTime,
  subscriptionLabels,
  subscriptionTone,
} from '../subscription'
import { cancelSpeech, speakFrench, speechSupported } from '../voice/speech'

const healthLabel: Record<PilotOverview['health'], string> = {
  ok: 'Activité saine',
  attention: 'Points à surveiller',
  critique: 'Action recommandée',
  setup: 'Prêt à démarrer',
}

function isSubscriptionBlock(message: string) {
  const lower = message.toLowerCase()
  return (
    lower.includes('abonnement') ||
    lower.includes('subscription') ||
    lower.includes('essai') ||
    lower.includes('paiement')
  )
}

function greetingHour() {
  const h = new Date().getHours()
  if (h < 12) return 'Bonjour'
  if (h < 18) return 'Bon après-midi'
  return 'Bonsoir'
}

function spokenEuro(value: number) {
  const rounded = Math.round(Math.abs(value))
  return `${rounded.toLocaleString('fr-FR')} euros`
}

function softenPriority(text: string) {
  return text
    .replace(/\s+/g, ' ')
    .replace(/[•·]/g, '')
    .replace(/\bTVA\b/g, 'T V A')
    .trim()
}

/** Texte court, naturel — uniquement les chiffres utiles. */
function buildDashboardRecap(opts: {
  firstName: string
  orgName: string
  ca: number
  unpaid: number
  toReview: number
  alerts: string[]
  recommendations: string[]
}) {
  const name = opts.firstName.trim()
  const hello = name ? `${greetingHour()} ${name}.` : `${greetingHour()}.`
  const parts = [hello, `Pour ${opts.orgName}, voilà l’essentiel.`]

  if (opts.ca > 0) {
    parts.push(`Le chiffre d’affaires est à ${spokenEuro(opts.ca)}.`)
  } else {
    parts.push(`Pas encore de chiffre d’affaires enregistré.`)
  }

  if (opts.unpaid > 0) {
    parts.push(`Il reste ${spokenEuro(opts.unpaid)} d’impayés à suivre.`)
  } else {
    parts.push(`Aucun impayé pour le moment.`)
  }

  if (opts.toReview > 0) {
    parts.push(
      opts.toReview === 1
        ? `Un document attend une relecture.`
        : `${opts.toReview} documents attendent une relecture.`,
    )
  }

  const priority = opts.alerts[0] || opts.recommendations[0]
  if (priority) {
    parts.push(`Le point à regarder : ${softenPriority(priority)}.`)
  }

  return parts.join(' ')
}

export default function DashboardPage() {
  const { token, orgId, user, memberships } = useAuth()
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [pilot, setPilot] = useState<PilotOverview | null>(null)
  const [billing, setBilling] = useState<BillingOverview | null>(null)
  const [subscription, setSubscription] = useState<SubscriptionInfo | null>(null)
  const [error, setError] = useState('')
  const [blocked, setBlocked] = useState(false)
  const [now, setNow] = useState(Date.now())
  const [recapSpeaking, setRecapSpeaking] = useState(false)
  const welcomeRef = useRef<HTMLDivElement>(null)

  const activeMembership = memberships.find((item) => item.organization_id === orgId)
  const canManageSubscription = Boolean(
    activeMembership?.permissions.includes('*') ||
      activeMembership?.permissions.includes('subscription.manage'),
  )
  const isElfAdmin = Boolean(user?.is_platform_admin)
  const firstName = user?.first_name?.trim() || ''

  useEffect(() => {
    if (!token || !orgId) return
    let cancelled = false
    setError('')
    setBlocked(false)
    setStats(null)

    const load = async (attemptSync: boolean) => {
      try {
        if (attemptSync) {
          try {
            await api.syncSubscription(token, orgId)
          } catch {
            /* sync optionnel */
          }
        }
        const [s, p, sub, bill] = await Promise.all([
          api.dashboard(token, orgId),
          api.dashboardPilot(token, orgId).catch(() => null),
          api.currentSubscription(token, orgId).catch(() => null),
          api.billingOverview(token, orgId).catch(() => null),
        ])
        if (cancelled) return
        setStats(s)
        setPilot(p)
        setSubscription(sub)
        setBilling(bill)
        setBlocked(false)
        setError('')
      } catch (e) {
        if (cancelled) return
        const message = e instanceof Error ? e.message : 'Impossible de charger le dashboard'
        setError(message)
        const blockedBySub = !isElfAdmin && isSubscriptionBlock(message)
        setBlocked(blockedBySub)
        void api.currentSubscription(token, orgId).then(setSubscription).catch(() => null)
        if (blockedBySub && !attemptSync) {
          await load(true)
        }
      }
    }

    void load(false)
    return () => {
      cancelled = true
    }
  }, [token, orgId, isElfAdmin])

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 60_000)
    return () => window.clearInterval(timer)
  }, [])

  useEffect(() => {
    return () => cancelSpeech()
  }, [])

  useEffect(() => {
    if (!stats || blocked) return
    const root = welcomeRef.current
    if (!root) return
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    let cancelled = false
    let revert: (() => void) | undefined

    void (async () => {
      const { default: gsap } = await import('gsap')
      if (cancelled || !welcomeRef.current) return
      const ctx = gsap.context(() => {
        if (reduce) {
          gsap.set('.dash-welcome > *, .dash-recap .stat, .dash-reveal', {
            clearProps: 'all',
            opacity: 1,
            y: 0,
          })
          return
        }
        const tl = gsap.timeline({ defaults: { ease: 'power3.out' } })
        tl.from('.dash-welcome-eyebrow', { y: 16, opacity: 0, duration: 0.45 })
          .from('.dash-welcome-title', { y: 22, opacity: 0, duration: 0.55 }, '-=0.2')
          .from('.dash-welcome-lead', { y: 14, opacity: 0, duration: 0.45 }, '-=0.25')
          .from('.dash-recap .stat', { y: 20, opacity: 0, duration: 0.4, stagger: 0.06 }, '-=0.15')
          .from('.dash-reveal', { y: 24, opacity: 0, duration: 0.5, stagger: 0.08 }, '-=0.2')
      }, root)
      revert = () => ctx.revert()
    })()

    return () => {
      cancelled = true
      revert?.()
    }
  }, [stats, blocked])

  if (blocked && !isElfAdmin) {
    const needsCheckout = !subscription || canStartSubscriptionCheckout(subscription.status)
    return (
      <>
        <div className="page-head">
          <div>
            <h2>Tableau de bord</h2>
            <p>Activez votre accès pour piloter l’activité de l’entreprise.</p>
          </div>
        </div>
        <section className="panel dashboard-gate">
          <span className="home-eyebrow">Accès ComptaPilot Pro</span>
          <h3>
            {subscription
              ? subscriptionLabels[subscription.status]
              : 'Essai de 14 jours à démarrer'}
          </h3>
          <p className="muted">
            Le tableau de bord, le dépôt de documents, la facturation et le copilote s’ouvrent après
            activation. Carte demandée au départ, 19 €/mois après l’essai.
          </p>
          {canManageSubscription ? (
            <div className="dashboard-gate-actions">
              <Link className="btn" to="/abonnement">
                {needsCheckout ? 'Activer mon essai' : 'Gérer mon abonnement'}
              </Link>
              <button
                className="btn secondary"
                type="button"
                onClick={() => {
                  if (!token || !orgId) return
                  setError('')
                  setBlocked(false)
                  setStats(null)
                  void (async () => {
                    try {
                      await api.syncSubscription(token, orgId)
                      const [s, p, sub, bill] = await Promise.all([
                        api.dashboard(token, orgId),
                        api.dashboardPilot(token, orgId).catch(() => null),
                        api.currentSubscription(token, orgId).catch(() => null),
                        api.billingOverview(token, orgId).catch(() => null),
                      ])
                      setStats(s)
                      setPilot(p)
                      setSubscription(sub)
                      setBilling(bill)
                    } catch (e) {
                      const message =
                        e instanceof Error ? e.message : 'Impossible de charger le dashboard'
                      setError(message)
                      setBlocked(isSubscriptionBlock(message))
                      void api
                        .currentSubscription(token, orgId)
                        .then(setSubscription)
                        .catch(() => null)
                    }
                  })()
                }}
              >
                Actualiser le statut
              </button>
            </div>
          ) : (
            <p className="muted">Demandez à un administrateur d’activer l’abonnement.</p>
          )}
        </section>
      </>
    )
  }

  if (error) return <div className="panel form-error">{error}</div>
  if (!stats) return <div className="loading">Chargement du dashboard…</div>

  const empty = (pilot?.health === 'setup' || !pilot) && stats.invoice_count === 0
  const trialRemaining =
    subscription?.status === 'trialing' ? remainingTime(subscription.trial_end, now) : null

  const recentSales = (billing?.documents ?? []).slice(0, 4)
  const recentDocs = stats.recent.slice(0, 4)
  const health = pilot?.health || 'setup'
  const unpaidAmount = pilot?.unpaid ?? billing?.stats.unpaid_amount ?? 0

  const playRecap = () => {
    if (!speechSupported()) return
    if (recapSpeaking) {
      cancelSpeech()
      setRecapSpeaking(false)
      return
    }
    const script = buildDashboardRecap({
      firstName,
      orgName: activeMembership?.organization_name || 'votre entreprise',
      ca: pilot?.ca ?? 0,
      unpaid: unpaidAmount,
      toReview: stats.to_review,
      alerts: pilot?.alerts ?? [],
      recommendations: pilot?.recommendations ?? [],
    })
    speakFrench(script, {
      rate: 0.86,
      pitch: 0.84,
      onStart: () => setRecapSpeaking(true),
      onEnd: () => setRecapSpeaking(false),
    })
  }

  return (
    <div className="dashboard-page" ref={welcomeRef}>
      <section className="dash-welcome panel">
        <div className="dash-welcome-head">
          <div>
            <span className="dash-welcome-eyebrow home-eyebrow">Copilote ComptaPilot</span>
            <h2 className="dash-welcome-title">
              {greetingHour()}
              {firstName ? ` ${firstName}` : ''}
            </h2>
          </div>
          <div className="dash-welcome-actions">
            <button
              type="button"
              className={`btn secondary dash-recap-btn ${recapSpeaking ? 'is-hot' : ''}`}
              onClick={playRecap}
              disabled={!speechSupported()}
              title={
                speechSupported()
                  ? 'Écouter un récapitulatif vocal d’environ 10 secondes'
                  : 'Synthèse vocale non disponible sur ce navigateur'
              }
            >
              {recapSpeaking ? 'Stop récap' : 'Écouter le récap'}
            </button>
            <span className={`dash-health-pill ${health}`}>{healthLabel[health]}</span>
          </div>
        </div>
        <p className="dash-welcome-lead muted">
          Voici l’état de {activeMembership?.organization_name || 'votre entreprise'} : chiffre
          d’affaires, impayés, documents et prochaines actions utiles.
        </p>

        <div className="stats dash-recap">
          <div className="stat">
            <span>Chiffre d&apos;affaires</span>
            <strong>{formatEuro(pilot?.ca ?? 0)}</strong>
          </div>
          <div className="stat">
            <span>Impayés clients</span>
            <strong>{formatEuro(unpaidAmount)}</strong>
          </div>
          <div className="stat">
            <span>Documents</span>
            <strong>{stats.invoice_count}</strong>
          </div>
          <div className="stat">
            <span>À relire</span>
            <strong>{stats.to_review}</strong>
          </div>
        </div>
      </section>

      {subscription && subscription.status !== 'none' && (
        <div className={`dashboard-sub-strip ${subscriptionTone(subscription.status)}`}>
          <div>
            <strong>ComptaPilot Pro</strong>
            <span>
              {subscriptionLabels[subscription.status]}
              {trialRemaining ? ` · ${trialRemaining} restant` : ''}
              {subscription.status === 'active' && subscription.current_period_end
                ? ` · prochaine échéance ${formatDate(subscription.current_period_end)}`
                : ''}
            </span>
          </div>
          {canManageSubscription && <Link to="/abonnement">Gérer</Link>}
        </div>
      )}

      {empty ? (
        <section className="panel onboarding-panel dash-reveal">
          <h3>Votre parcours de démarrage</h3>
          <p className="muted">
            Activez l’accès, renseignez l’entreprise, puis nourrissez le copilote avec vos documents
            et clients.
          </p>
          <ol className="onboarding-steps">
            <li>
              <Link to="/settings">1. Paramètres — identité et TVA</Link>
            </li>
            <li>
              <Link to="/clients">2. Clients — premier contact commercial</Link>
            </li>
            <li>
              <Link to="/deposit">3. Déposer — première facture fournisseur</Link>
            </li>
            <li>
              <Link to="/copilote">4. Copilote — première question</Link>
            </li>
          </ol>
        </section>
      ) : (
        pilot &&
        (pilot.alerts.length > 0 || pilot.recommendations.length > 0) && (
          <section className="panel dash-reveal">
            <h3>Priorités</h3>
            <ul className="alert-list">
              {pilot.alerts.map((a) => (
                <li key={a}>{a}</li>
              ))}
              {pilot.recommendations.map((r) => (
                <li key={r} className="muted">
                  → {r}
                </li>
              ))}
            </ul>
          </section>
        )
      )}

      <section className="panel dash-reveal">
        <div className="dashboard-section-head">
          <h3>Que souhaitez-vous faire ?</h3>
        </div>
        <div className="dash-cta-grid">
          <Link className="dash-cta" to="/deposit">
            <span className="dash-cta-icon">
              <NavIconDeposit />
            </span>
            <strong>Déposer un document</strong>
            <span>Scan automatique d’une facture</span>
          </Link>
          <Link className="dash-cta" to="/facturation">
            <span className="dash-cta-icon">
              <NavIconBilling />
            </span>
            <strong>Créer une facture</strong>
            <span>Devis ou facture client</span>
          </Link>
          <Link className="dash-cta" to="/clients">
            <span className="dash-cta-icon">
              <NavIconClients />
            </span>
            <strong>Ajouter un client</strong>
            <span>Fiche contact & TVA</span>
          </Link>
          <Link className="dash-cta" to="/catalogue">
            <span className="dash-cta-icon">
              <NavIconCatalog />
            </span>
            <strong>Ajouter un produit</strong>
            <span>Catalogue prix HT</span>
          </Link>
          <Link className="dash-cta" to="/copilote">
            <span className="dash-cta-icon">
              <NavIconCopilote />
            </span>
            <strong>Poser une question</strong>
            <span>Chat avec le copilote IA</span>
          </Link>
        </div>
      </section>

      <div className="dashboard-work-grid dash-reveal">
        <section className="panel">
          <div className="dashboard-section-head">
            <h3>Modifications récentes</h3>
            <Link to="/history">Comptabilité</Link>
          </div>
          {recentDocs.length === 0 && recentSales.length === 0 ? (
            <div className="empty">Aucune activité récente.</div>
          ) : (
            <div className="list">
              {recentDocs.map((inv) => (
                <Link key={`doc-${inv.id}`} to={`/result/${inv.id}`} className="list-item">
                  <div>
                    <strong>{inv.supplier || inv.filename}</strong>
                    <span>Document · {inv.invoice_date || '—'}</span>
                  </div>
                  <div>{formatEuro(inv.amount_ht)}</div>
                  <div>
                    <StatusBadge needsReview={inv.needs_review} status={inv.status} />
                  </div>
                </Link>
              ))}
              {recentSales.map((doc) => (
                <Link key={`sale-${doc.id}`} to="/facturation" className="list-item">
                  <div>
                    <strong>
                      {doc.number} — {doc.customer_name}
                    </strong>
                    <span>
                      {doc.doc_type} · {doc.issue_date || '—'}
                    </span>
                  </div>
                  <div>{formatEuro(doc.amount_ttc)}</div>
                  <div>
                    <span className="badge">{doc.status}</span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </section>

        <aside className="panel dashboard-shortcuts">
          <h3>Raccourcis</h3>
          <div className="dashboard-shortcut-list">
            <Link to="/activites">
              <span className="dash-cta-icon">
                <NavIconActivities />
              </span>
              <strong>Activités</strong>
              <span>Agenda commercial</span>
            </Link>
            <Link to="/organisation">
              <span className="dash-cta-icon">
                <NavIconOrg />
              </span>
              <strong>Organisation</strong>
              <span>Siège & coordonnées</span>
            </Link>
            <Link to="/admin/equipe">
              <span className="dash-cta-icon">
                <NavIconTeam />
              </span>
              <strong>Équipe</strong>
              <span>Comptes et droits</span>
            </Link>
          </div>
        </aside>
      </div>
    </div>
  )
}

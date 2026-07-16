import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  api,
  formatEuro,
  type DashboardStats,
  type PilotOverview,
  type SubscriptionInfo,
} from '../api'
import { useAuth } from '../auth'
import StatusBadge from '../components/StatusBadge'
import {
  canStartSubscriptionCheckout,
  formatDate,
  remainingTime,
  subscriptionLabels,
  subscriptionTone,
} from '../subscription'

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

export default function DashboardPage() {
  const { token, orgId, user, memberships } = useAuth()
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [pilot, setPilot] = useState<PilotOverview | null>(null)
  const [subscription, setSubscription] = useState<SubscriptionInfo | null>(null)
  const [error, setError] = useState('')
  const [blocked, setBlocked] = useState(false)
  const [now, setNow] = useState(Date.now())

  const activeMembership = memberships.find((item) => item.organization_id === orgId)
  const canManageSubscription = Boolean(
    activeMembership?.permissions.includes('*') ||
      activeMembership?.permissions.includes('subscription.manage'),
  )

  useEffect(() => {
    if (!token || !orgId) return
    setError('')
    setBlocked(false)
    setStats(null)

    Promise.all([
      api.dashboard(token, orgId),
      api.dashboardPilot(token, orgId).catch(() => null),
      api.currentSubscription(token, orgId).catch(() => null),
    ])
      .then(([s, p, sub]) => {
        setStats(s)
        setPilot(p)
        setSubscription(sub)
      })
      .catch((e) => {
        const message = e instanceof Error ? e.message : 'Impossible de charger le dashboard'
        setError(message)
        setBlocked(isSubscriptionBlock(message))
        void api.currentSubscription(token, orgId).then(setSubscription).catch(() => null)
      })
  }, [token, orgId])

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 60_000)
    return () => window.clearInterval(timer)
  }, [])

  if (blocked) {
    const needsCheckout =
      !subscription || canStartSubscriptionCheckout(subscription.status)
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
            Le tableau de bord, l’OCR, la facturation et le copilote s’ouvrent après activation de
            l’abonnement. Carte demandée au départ, 19 €/mois après l’essai.
          </p>
          {canManageSubscription ? (
            <Link className="btn" to="/abonnement">
              {needsCheckout ? 'Activer mon essai' : 'Gérer mon abonnement'}
            </Link>
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
    subscription?.status === 'trialing'
      ? remainingTime(subscription.trial_end, now)
      : null

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Tableau de bord</h2>
          <p>
            {user
              ? `Bonjour ${user.first_name} — vue d’ensemble de votre activité.`
              : 'Pilotage de votre activité réelle.'}
          </p>
        </div>
        <div className="actions" style={{ marginTop: 0 }}>
          <Link className="btn" to="/deposit">
            Déposer une facture
          </Link>
          <Link className="btn secondary" to="/copilote">
            Parler au copilote
          </Link>
        </div>
      </div>

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
          {canManageSubscription && (
            <Link to="/abonnement">Gérer</Link>
          )}
        </div>
      )}

      {empty ? (
        <section className="panel onboarding-panel">
          <h3>Votre parcours de démarrage</h3>
          <p className="muted">
            Une seule logique : activer l’accès, renseigner l’entreprise, puis nourrir le copilote
            avec vos documents réels.
          </p>
          <ol className="onboarding-steps">
            <li>
              <Link to="/settings">1. Paramètres — identité et TVA de l’entreprise</Link>
            </li>
            <li>
              <Link to="/deposit">2. Déposer — première facture fournisseur (OCR)</Link>
            </li>
            <li>
              <Link to="/facturation">3. Facturation — premier devis ou facture client</Link>
            </li>
            <li>
              <Link to="/copilote">4. Copilote — poser votre première question</Link>
            </li>
          </ol>
          <div className="dashboard-next-links">
            <Link to="/organisation">Équipe & droits</Link>
            <Link to="/abonnement">Abonnement</Link>
          </div>
        </section>
      ) : (
        <>
          {pilot && (
            <>
              <div className={`health-banner health-${pilot.health}`}>
                <strong>Santé activité — {healthLabel[pilot.health]}</strong>
                {pilot.alerts[0] ? <span>{pilot.alerts[0]}</span> : <span>Aucune alerte</span>}
              </div>

              <div className="stats">
                <div className="stat">
                  <span>Chiffre d&apos;affaires</span>
                  <strong>{formatEuro(pilot.ca)}</strong>
                </div>
                <div className="stat">
                  <span>Bénéfice estimé</span>
                  <strong>{formatEuro(pilot.benefice)}</strong>
                </div>
                <div className="stat">
                  <span>Marge</span>
                  <strong>{pilot.marge_pct}%</strong>
                </div>
                <div className="stat">
                  <span>Impayés clients</span>
                  <strong>{formatEuro(pilot.unpaid)}</strong>
                </div>
              </div>

              {(pilot.alerts.length > 0 || pilot.recommendations.length > 0) && (
                <section className="panel" style={{ marginBottom: '1rem' }}>
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
              )}
            </>
          )}

          <div className="dashboard-work-grid">
            <section className="panel">
              <div className="dashboard-section-head">
                <h3>Comptabilité fournisseur</h3>
                <Link to="/history">Voir tout</Link>
              </div>
              <div className="stats dashboard-mini-stats">
                <div className="stat">
                  <span>Documents</span>
                  <strong>{stats.invoice_count}</strong>
                </div>
                <div className="stat">
                  <span>HT</span>
                  <strong>{formatEuro(stats.total_ht)}</strong>
                </div>
                <div className="stat">
                  <span>TVA</span>
                  <strong>{formatEuro(stats.recoverable_vat)}</strong>
                </div>
                <div className="stat">
                  <span>À vérifier</span>
                  <strong>{stats.to_review}</strong>
                </div>
              </div>
              {stats.recent.length === 0 ? (
                <div className="empty">
                  Aucun document.
                  <div style={{ marginTop: '1rem' }}>
                    <Link className="btn" to="/deposit">
                      Déposer une facture
                    </Link>
                  </div>
                </div>
              ) : (
                <div className="list">
                  {stats.recent.slice(0, 5).map((inv) => (
                    <Link key={inv.id} to={`/result/${inv.id}`} className="list-item">
                      <div>
                        <strong>{inv.supplier || inv.filename}</strong>
                        <span>
                          {inv.invoice_number || 'Sans numéro'} · {inv.invoice_date || '—'}
                        </span>
                      </div>
                      <div>{formatEuro(inv.amount_ht)}</div>
                      <div>{formatEuro(inv.amount_tva)}</div>
                      <div>
                        <StatusBadge needsReview={inv.needs_review} status={inv.status} />
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </section>

            <aside className="panel dashboard-shortcuts">
              <h3>Continuer</h3>
              <p className="muted">Les prochaines actions utiles, dans l’ordre du produit.</p>
              <div className="dashboard-shortcut-list">
                <Link to="/deposit">
                  <strong>Déposer</strong>
                  <span>Importer une facture PDF ou photo</span>
                </Link>
                <Link to="/facturation">
                  <strong>Facturation</strong>
                  <span>Créer un devis ou une facture client</span>
                </Link>
                <Link to="/copilote">
                  <strong>Copilote IA</strong>
                  <span>Demander une explication sur vos chiffres</span>
                </Link>
                <Link to="/organisation">
                  <strong>Organisation</strong>
                  <span>Équipe, rôles et droits</span>
                </Link>
              </div>
            </aside>
          </div>
        </>
      )}
    </>
  )
}

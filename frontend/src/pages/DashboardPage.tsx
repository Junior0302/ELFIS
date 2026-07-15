import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, formatEuro, type DashboardStats, type PilotOverview } from '../api'
import { useAuth } from '../auth'
import StatusBadge from '../components/StatusBadge'

const healthLabel: Record<PilotOverview['health'], string> = {
  ok: 'Trésorerie stable',
  attention: 'Sous surveillance',
  critique: 'Tension de cash',
  setup: 'Prêt à démarrer',
}

export default function DashboardPage() {
  const { token, orgId, user } = useAuth()
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [pilot, setPilot] = useState<PilotOverview | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([api.dashboard(token, orgId), api.dashboardPilot(token, orgId).catch(() => null)])
      .then(([s, p]) => {
        setStats(s)
        setPilot(p)
      })
      .catch((e) => setError(e.message || 'Impossible de charger le dashboard'))
  }, [token, orgId])

  if (error) return <div className="panel form-error">{error}</div>
  if (!stats) return <div className="loading">Chargement du dashboard…</div>

  const empty = (pilot?.health === 'setup' || !pilot) && stats.invoice_count === 0

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Tableau de bord</h2>
          <p>
            {user
              ? `Bonjour ${user.first_name} — pilotage de votre activité réelle.`
              : 'Pilotage financier — CA, marge, trésorerie et alertes IA.'}
          </p>
        </div>
        <div className="actions" style={{ marginTop: 0 }}>
          <Link className="btn" to="/deposit">
            Déposer une facture
          </Link>
          <Link className="btn secondary" to="/banque">
            Connecter la banque
          </Link>
        </div>
      </div>

      {empty ? (
        <section className="panel onboarding-panel">
          <h3>Commencez réellement</h3>
          <p className="muted">
            Aucune donnée fictive. Connectez votre activité pour activer le copilote financier.
          </p>
          <ol className="onboarding-steps">
            <li>
              <Link to="/deposit">1. Déposez votre première facture PDF</Link>
            </li>
            <li>
              <Link to="/banque">2. Connectez votre compte bancaire</Link>
            </li>
            <li>
              <Link to="/facturation">3. Créez votre première facture client</Link>
            </li>
            <li>
              <Link to="/copilote">4. Posez une question au Finance Agent</Link>
            </li>
          </ol>
        </section>
      ) : (
        <>
          {pilot && (
            <>
              <div className={`health-banner health-${pilot.health}`}>
                <strong>Santé entreprise — {healthLabel[pilot.health]}</strong>
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
                  <span>Trésorerie</span>
                  <strong>{formatEuro(pilot.tresorerie)}</strong>
                </div>
              </div>

              {(pilot.alerts.length > 0 || pilot.recommendations.length > 0) && (
                <section className="panel" style={{ marginBottom: '1rem' }}>
                  <h3>Attention & recommandations</h3>
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

          <div className="stats">
            <div className="stat">
              <span>Factures fournisseur</span>
              <strong>{stats.invoice_count}</strong>
            </div>
            <div className="stat">
              <span>Montant HT</span>
              <strong>{formatEuro(stats.total_ht)}</strong>
            </div>
            <div className="stat">
              <span>TVA récupérable</span>
              <strong>{formatEuro(stats.recoverable_vat)}</strong>
            </div>
            <div className="stat">
              <span>À vérifier</span>
              <strong>{stats.to_review}</strong>
            </div>
          </div>

          <section className="panel">
            <h3>Dernières importations</h3>
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
                {stats.recent.map((inv) => (
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
                    <div className="muted">#{inv.id}</div>
                  </Link>
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </>
  )
}

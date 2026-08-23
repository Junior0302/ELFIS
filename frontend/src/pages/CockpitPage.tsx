import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import {
  mapOverviewToHome,
  type DashboardHomeView,
} from '../dashboardHome'
import { migrationApi } from '../services/migrationApi'
import { financialApi } from '../services/financialApi'
import { useSync } from '../sync/SyncProvider'
import { EmptyState, ErrorState, Skeleton, UiBadge } from '../ui/UiStates'

/**
 * Cockpit ops client — distinct de /dashboard (accueil) et /finance (analyse).
 * Chiffres financiers uniquement via Financial Engine (aucun /dashboard/stats).
 */
export default function CockpitPage() {
  const { token, orgId, user } = useAuth()
  const { unreadNotifications, mode, refresh } = useSync()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [home, setHome] = useState<DashboardHomeView | null>(null)
  const [migrationActive, setMigrationActive] = useState(0)
  const [proposalsReview, setProposalsReview] = useState(0)

  const load = useCallback(async () => {
    if (!token || orgId == null) return
    setLoading(true)
    setError('')
    try {
      const [overview, migrations, proposals] = await Promise.all([
        financialApi.overview(token, orgId),
        migrationApi.listSessions(token, orgId).catch(() => ({ items: [] })),
        api
          .listAccountingProposals({ requires_review: true, page: 1, page_size: 1 }, token, orgId)
          .catch(() => ({ total: 0, proposals: [] })),
      ])
      setHome(mapOverviewToHome(overview))
      setMigrationActive(
        (migrations.items || []).filter(
          (s) => !['cancelled', 'completed', 'failed'].includes(s.status),
        ).length,
      )
      setProposalsReview(proposals.total || 0)
      await refresh('notifications')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Chargement cockpit impossible')
    } finally {
      setLoading(false)
    }
  }, [token, orgId, refresh])

  useEffect(() => {
    void load()
  }, [load])

  const tresorerie = home?.kpis.find((k) => k.id === 'tresorerie')
  const revenus = home?.kpis.find((k) => k.id === 'revenus')
  const unpaid = home?.kpis.find((k) => k.id === 'factures_impayees')

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Cockpit</h1>
          <p className="muted">
            Ops temps réel (sync {mode}) — notifications, migrations, propositions. Les indicateurs
            financiers viennent du Financial Engine (même source que Accueil / Finance).
          </p>
        </div>
        <button type="button" className="btn secondary" onClick={() => void load()}>
          Rafraîchir
        </button>
      </header>

      {loading ? <Skeleton rows={5} /> : null}
      {error ? <ErrorState message={error} onRetry={() => void load()} /> : null}

      {!loading && !error ? (
        <>
          <div className="stats ui-card-grid">
            <div className="ui-card">
              <p className="muted">Notifications non lues</p>
              <p className="ui-stat">{unreadNotifications}</p>
              <Link to="/notifications">Ouvrir le centre</Link>
            </div>
            <div className="ui-card">
              <p className="muted">Migrations actives</p>
              <p className="ui-stat">{migrationActive}</p>
              <Link to="/migration">Migration Center</Link>
            </div>
            <div className="ui-card">
              <p className="muted">Propositions à revoir</p>
              <p className="ui-stat">{proposalsReview}</p>
              <Link to="/accounting/proposals">Comptabilité</Link>
            </div>
            <div className="ui-card">
              <p className="muted">Documents à traiter</p>
              <p className="ui-stat">{home?.documentsToProcess ?? '—'}</p>
              <Link to="/documents">Documents</Link>
            </div>
          </div>

          <section className="panel" style={{ marginTop: '1.25rem' }}>
            <div className="dashboard-section-head">
              <h2>Santé & alertes (Financial Engine)</h2>
              <Link to="/finance">Analyse détaillée</Link>
            </div>
            {home ? (
              <>
                <p className="muted" style={{ marginBottom: '0.75rem' }}>
                  {home.provenanceLabel}
                  {home.healthScore != null
                    ? ` · Score ${Math.round(home.healthScore)}/100 (${home.healthGrade || '—'})`
                    : null}
                </p>
                <ul className="ui-list">
                  <li>
                    Trésorerie : {tresorerie?.display ?? '—'}{' '}
                    <UiBadge>Financial Engine</UiBadge>
                  </li>
                  <li>Chiffre d’affaires : {revenus?.display ?? '—'}</li>
                  <li>Factures impayées : {unpaid?.display ?? '—'}</li>
                </ul>
                {home.alerts.length > 0 ? (
                  <ul className="ui-list" style={{ marginTop: '1rem' }}>
                    {home.alerts.slice(0, 3).map((a) => (
                      <li key={a.id}>
                        <strong>{a.title}</strong> — {a.message}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="muted" style={{ marginTop: '0.75rem' }}>
                    Aucune alerte financière.
                  </p>
                )}
                <p style={{ marginTop: '1rem' }}>
                  <Link to="/dashboard">Accueil synthèse</Link>
                  {' · '}
                  <Link to="/platform/banking">Banque</Link>
                  {' · '}
                  <Link to="/copilote">Copilote</Link>
                </p>
              </>
            ) : (
              <EmptyState
                title="Pas de snapshot financier"
                description="Le Financial Engine n’a pas renvoyé d’overview."
              />
            )}
          </section>

          <div className="ui-card-grid" style={{ marginTop: '1.25rem' }}>
            <Link className="ui-card ui-card-link" to="/search">
              <h3>Recherche</h3>
              <p className="muted">Documents, clients, propositions, rapports.</p>
            </Link>
            <Link className="ui-card ui-card-link" to="/accounting/intelligence">
              <h3>Intelligence</h3>
              <p className="muted">Recommandations et feedback.</p>
            </Link>
            {user?.is_platform_admin ? (
              <Link className="ui-card ui-card-link" to="/elfadmin">
                <h3>ELF Admin</h3>
                <p className="muted">Cockpit plateforme.</p>
              </Link>
            ) : null}
          </div>
        </>
      ) : null}
    </div>
  )
}

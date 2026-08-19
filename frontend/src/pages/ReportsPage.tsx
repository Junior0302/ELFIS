import { Link } from 'react-router-dom'
import { useAuth } from '../auth'

export default function ReportsPage() {
  const { user } = useAuth()

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Rapports</h1>
          <p className="muted">
            Accès aux bilans et exports déjà branchés aux API — aucun calcul local.
          </p>
        </div>
      </header>

      <div className="ui-card-grid">
        <Link className="ui-card ui-card-link" to="/migration">
          <h3>Rapports Migration</h3>
          <p className="muted">Ouvrez une session puis téléchargez le rapport JSON / CSV.</p>
        </Link>
        <Link className="ui-card ui-card-link" to="/history">
          <h3>Exports comptables</h3>
          <p className="muted">Historique des documents traités et exports période.</p>
        </Link>
        <Link className="ui-card ui-card-link" to="/dashboard">
          <h3>Pilotage</h3>
          <p className="muted">Synthèse Accueil (Financial Engine).</p>
        </Link>
        <Link className="ui-card ui-card-link" to="/cockpit">
          <h3>Cockpit ops</h3>
          <p className="muted">Jobs, notifications, migrations et alertes financières.</p>
        </Link>
        {user?.is_platform_admin ? (
          <Link className="ui-card ui-card-link" to="/elfadmin/audit">
            <h3>Audit plateforme</h3>
            <p className="muted">Journal d’audit administrateur.</p>
          </Link>
        ) : null}
      </div>
    </div>
  )
}

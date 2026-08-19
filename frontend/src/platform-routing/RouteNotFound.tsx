import { Link } from 'react-router-dom'

/**
 * 404 réelle — pas de redirect silencieux vers `/` ou `/home` (F1.3.2.3).
 */
export default function RouteNotFound() {
  return (
    <div className="page" style={{ padding: '2rem', maxWidth: 480 }} data-testid="route-not-found">
      <h1>Page introuvable</h1>
      <p>Cette adresse ne correspond à aucune page de l’application.</p>
      <p style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
        <Link className="btn" to="/home">
          Accueil ELFIS
        </Link>
        <Link className="btn secondary" to="/dashboard">
          Tableau de bord
        </Link>
      </p>
    </div>
  )
}

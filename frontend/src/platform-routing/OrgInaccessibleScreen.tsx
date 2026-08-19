import { Link } from 'react-router-dom'
import { useAuth } from '../auth'

/**
 * Organisation active absente des memberships — erreur explicite, pas Home silencieux.
 */
export default function OrgInaccessibleScreen() {
  const { memberships, setOrgId } = useAuth()

  return (
    <div className="page" style={{ padding: '2rem', maxWidth: 520 }} data-testid="org-inaccessible">
      <h1>Organisation inaccessible</h1>
      <p>
        L’organisation active n’est plus disponible pour votre compte. Choisissez une organisation
        pour continuer — aucun retour automatique à l’accueil.
      </p>
      {memberships.length > 0 ? (
        <ul style={{ listStyle: 'none', padding: 0, display: 'grid', gap: '0.5rem' }}>
          {memberships.map((m) => (
            <li key={m.organization_id}>
              <button
                type="button"
                className="btn"
                onClick={() => setOrgId(m.organization_id)}
              >
                {m.organization_name || `Organisation #${m.organization_id}`}
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p>
          Aucune organisation associée.{' '}
          <Link to="/platform/organization">Gérer l’organisation</Link>
        </p>
      )}
    </div>
  )
}

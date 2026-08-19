import { Link } from 'react-router-dom'

type Props = {
  resolvedAt?: string | null
  lastAction?: string | null
  sourcePath?: string | null
}

export default function DecisionResolutionPanel({ resolvedAt, lastAction, sourcePath }: Props) {
  return (
    <section className="panel decision-resolution-panel" aria-labelledby="decision-resolved-title">
      <h3 id="decision-resolved-title">Décision résolue</h3>
      <p>La cause détectée n’est plus présente.</p>
      {lastAction ? <p className="muted">Dernière action : {lastAction}</p> : null}
      {resolvedAt ? (
        <p className="muted">
          Résolue le{' '}
          {new Intl.DateTimeFormat('fr-FR', { dateStyle: 'short', timeStyle: 'short' }).format(
            new Date(resolvedAt),
          )}
        </p>
      ) : null}
      <div className="actions">
        {sourcePath ? (
          <Link className="btn secondary" to={sourcePath}>
            Voir la ressource
          </Link>
        ) : null}
        <Link className="btn" to="/dashboard">
          Retour au Command Center
        </Link>
        <Link className="btn secondary" to="/decisions">
          Liste des décisions
        </Link>
      </div>
    </section>
  )
}

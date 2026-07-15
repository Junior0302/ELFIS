import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, formatEuro, type TreasuryOverview } from '../api'
import { useAuth } from '../auth'

export default function TresoreriePage() {
  const { token, orgId } = useAuth()
  const [data, setData] = useState<TreasuryOverview | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api
      .treasuryOverview(token, orgId)
      .then(setData)
      .catch((e) => setError(e.message || 'Erreur trésorerie'))
  }, [token, orgId])

  if (error) return <div className="panel form-error">{error}</div>
  if (!data) return <div className="loading">Projection de trésorerie…</div>

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Trésorerie</h2>
          <p>
            Anticipez votre cash à 30, 60 et 90 jours — tensions détectées et conseils d’action.
          </p>
        </div>
        <div className="actions" style={{ marginTop: 0 }}>
          <Link className="btn secondary" to="/banque">
            Banque
          </Link>
          <Link className="btn secondary" to="/copilote">
            Copilote IA
          </Link>
        </div>
      </div>

      <div className="stats">
        <div className="stat">
          <span>Solde actuel</span>
          <strong>{formatEuro(data.current_balance)}</strong>
        </div>
        <div className="stat">
          <span>À 30 jours</span>
          <strong>{formatEuro(data.forecast['30'])}</strong>
        </div>
        <div className="stat">
          <span>À 60 jours</span>
          <strong>{formatEuro(data.forecast['60'])}</strong>
        </div>
        <div className="stat">
          <span>À 90 jours</span>
          <strong>{formatEuro(data.forecast['90'])}</strong>
        </div>
      </div>

      <div className="stats" style={{ gridTemplateColumns: '1fr 1fr 1fr' }}>
        <div className="stat">
          <span>Encaissements</span>
          <strong>{formatEuro(data.encaissements)}</strong>
        </div>
        <div className="stat">
          <span>Décaissements</span>
          <strong>{formatEuro(data.decaissements)}</strong>
        </div>
        <div className="stat">
          <span>Net période</span>
          <strong>{formatEuro(data.net_period)}</strong>
        </div>
      </div>

      <div className="result-grid" style={{ minHeight: 'auto' }}>
        <section className="panel">
          <h3>Tensions détectées</h3>
          {data.tensions.length === 0 ? (
            <p className="muted">Aucune tension critique détectée.</p>
          ) : (
            <ul className="alert-list">
              {data.tensions.map((t) => (
                <li key={t}>{t}</li>
              ))}
            </ul>
          )}
        </section>
        <section className="panel">
          <h3>Recommandations</h3>
          <ul className="reco-list">
            {data.recommendations.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </section>
      </div>
    </>
  )
}

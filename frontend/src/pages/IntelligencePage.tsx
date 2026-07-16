import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api, formatEuro } from '../api'
import { useAuth } from '../auth'
import type { IntelligenceOverview } from '../elfisTypes'

type ChatMessage = { role: 'user' | 'assistant'; text: string; citations?: string[] }

export default function IntelligencePage() {
  const { token, orgId } = useAuth()
  const [period, setPeriod] = useState('month')
  const [data, setData] = useState<IntelligenceOverview | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [question, setQuestion] = useState('')
  const [chat, setChat] = useState<ChatMessage[]>([])
  const [asking, setAsking] = useState(false)

  const load = (nextPeriod = period) => {
    if (!token) return
    setLoading(true)
    setError('')
    api
      .getIntelligence(nextPeriod, token, orgId)
      .then(setData)
      .catch((e) => setError(e.message || 'Intelligence indisponible'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, orgId])

  const onAsk = async (e: FormEvent) => {
    e.preventDefault()
    if (!token || !question.trim()) return
    const q = question.trim()
    setChat((c) => [...c, { role: 'user', text: q }])
    setQuestion('')
    setAsking(true)
    try {
      const res = await api.elfisChat(q, token, orgId)
      setChat((c) => [
        ...c,
        { role: 'assistant', text: res.answer, citations: res.citations },
      ])
    } catch (reason) {
      setChat((c) => [
        ...c,
        {
          role: 'assistant',
          text: reason instanceof Error ? reason.message : 'Réponse impossible',
        },
      ])
    } finally {
      setAsking(false)
    }
  }

  if (error && !data) return <div className="panel form-error">{error}</div>
  if (loading && !data) return <div className="loading">Chargement Intelligence…</div>
  if (!data) return null

  const s = data.company_synthesis

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Intelligence</h2>
          <p>Synthèse d’entreprise, alertes, prévisions prudentes et discussion avec ELFIS.</p>
        </div>
        <select
          value={period}
          onChange={(e) => {
            setPeriod(e.target.value)
            load(e.target.value)
          }}
        >
          <option value="month">Ce mois</option>
          <option value="previous_month">Mois précédent</option>
          <option value="quarter">Trimestre</option>
          <option value="year">Année</option>
        </select>
      </div>

      {error && <div className="auth-alert auth-alert-error">{error}</div>}

      <section className="panel">
        <h3>1. Synthèse de l’entreprise · {data.period_label}</h3>
        <div className="stats">
          <div className="stat">
            <span>CA encaissé</span>
            <strong>{s.revenue != null ? formatEuro(s.revenue) : '—'}</strong>
          </div>
          <div className="stat">
            <span>Dépenses</span>
            <strong>{formatEuro(s.expenses)}</strong>
          </div>
          <div className="stat">
            <span>Résultat estimé</span>
            <strong>{s.estimated_result != null ? formatEuro(s.estimated_result) : '—'}</strong>
          </div>
          <div className="stat">
            <span>TVA estimée</span>
            <strong>{formatEuro(s.estimated_vat)}</strong>
          </div>
          <div className="stat">
            <span>Clients en attente</span>
            <strong>{s.client_invoices_pending}</strong>
          </div>
          <div className="stat">
            <span>Documents analysés</span>
            <strong>{s.documents_analyzed}</strong>
          </div>
          <div className="stat">
            <span>Anomalies ouvertes</span>
            <strong>{s.open_anomalies}</strong>
          </div>
          <div className="stat">
            <span>Trésorerie</span>
            <strong style={{ fontSize: '1rem' }}>
              {s.treasury === 'not_available' ? 'non disponible' : s.treasury}
            </strong>
          </div>
        </div>
      </section>

      <div className="result-grid" style={{ minHeight: 'auto', marginTop: '1rem' }}>
        <section className="panel">
          <h3>2. Alertes prioritaires</h3>
          {data.alerts.length === 0 ? (
            <p className="muted">Aucune alerte prioritaire.</p>
          ) : (
            <ul className="elfis-alert-list">
              {data.alerts.map((a, idx) => (
                <li key={`${a.title}-${idx}`}>
                  <strong>
                    [{a.priority}] {a.title}
                  </strong>
                  <span>{a.description}</span>
                  {a.document_id ? (
                    <Link to={`/result/${a.document_id}`}>Ouvrir {a.document_label || a.document_id}</Link>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="panel">
          <h3>3. Activité récente</h3>
          {data.recent_activity.length === 0 ? (
            <p className="muted">Aucune activité sur la période.</p>
          ) : (
            <div className="list">
              {data.recent_activity.map((item) => (
                <Link
                  key={item.id}
                  className="list-item"
                  to={`/result/${item.id}`}
                  style={{ gridTemplateColumns: '1.4fr 0.7fr 0.6fr' }}
                >
                  <div>
                    <strong>{item.supplier || 'Fournisseur'}</strong>
                    <span>
                      {item.number || `#${item.id}`} · {item.date || '—'}
                    </span>
                  </div>
                  <strong>{item.amount_ttc != null ? formatEuro(item.amount_ttc) : '—'}</strong>
                  <span className="badge">{item.status}</span>
                </Link>
              ))}
            </div>
          )}
        </section>
      </div>

      <div className="result-grid" style={{ minHeight: 'auto', marginTop: '1rem' }}>
        <section className="panel">
          <h3>4–5. Dépenses, revenus & échéances</h3>
          <p>Dépenses période : {formatEuro(s.expenses)}</p>
          <p>Revenus encaissés (factures payées) : {s.revenue != null ? formatEuro(s.revenue) : '—'}</p>
          <p>Factures clients en attente : {formatEuro(s.client_amount_pending)}</p>
          <p>Fournisseurs à traiter : {s.supplier_invoices_to_pay}</p>
        </section>

        <section className="panel">
          <h3>6. Anomalies</h3>
          {data.anomalies.length === 0 ? (
            <p className="muted">Aucune anomalie ouverte.</p>
          ) : (
            <ul className="elfis-alert-list">
              {data.anomalies.slice(0, 12).map((a, idx) => (
                <li key={`an-${idx}`}>
                  <strong>{a.title}</strong>
                  <span>{a.description}</span>
                  {a.document_id ? <Link to={`/result/${a.document_id}`}>Voir</Link> : null}
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <div className="result-grid" style={{ minHeight: 'auto', marginTop: '1rem' }}>
        <section className="panel">
          <h3>7. Prévisions</h3>
          <p className="muted">{data.forecasts.method}</p>
          {data.forecasts.status === 'insufficient_data' ? (
            <p>Prévision indisponible : données insuffisantes.</p>
          ) : (
            <>
              <p>
                Sorties à 30 jours :{' '}
                {data.forecasts.outflows_30d != null
                  ? formatEuro(data.forecasts.outflows_30d)
                  : '—'}
              </p>
              <p>
                Entrées attendues :{' '}
                {data.forecasts.inflows_expected != null
                  ? formatEuro(data.forecasts.inflows_expected)
                  : '—'}
              </p>
              <p>TVA estimée période : {formatEuro(data.forecasts.vat_estimate)}</p>
            </>
          )}
          {data.forecasts.limitations && <p className="muted">{data.forecasts.limitations}</p>}
        </section>

        <section className="panel">
          <h3>8. Opportunités</h3>
          {data.opportunities.length === 0 ? (
            <p className="muted">Aucune opportunité calculée sur les données actuelles.</p>
          ) : (
            <ul className="elfis-alert-list">
              {data.opportunities.map((o, idx) => (
                <li key={`op-${idx}`}>
                  <strong>{o.title}</strong>
                  <span>{o.description}</span>
                  {o.document_id ? <Link to={`/result/${o.document_id}`}>Voir</Link> : null}
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <section className="panel" style={{ marginTop: '1rem' }}>
        <h3>9. Discussion avec ELFIS</h3>
        <p className="muted">
          Réponses basées uniquement sur les données de votre organisation. Aucun chiffre inventé.
        </p>
        <div className="elfis-chat">
          {chat.length === 0 && (
            <p className="muted">
              Exemples : « Combien ai-je dépensé ce mois-ci ? », « Quel est mon fournisseur le plus
              coûteux ? », « Résume mes anomalies. »
            </p>
          )}
          {chat.map((m, idx) => (
            <div key={idx} className={`elfis-chat-bubble ${m.role}`}>
              <p>{m.text}</p>
              {m.citations && m.citations.length > 0 && (
                <small className="muted">Sources : {m.citations.join(' · ')}</small>
              )}
            </div>
          ))}
        </div>
        <form className="elfis-chat-form" onSubmit={onAsk}>
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Posez votre question à ELFIS…"
          />
          <button className="btn" type="submit" disabled={asking}>
            {asking ? '…' : 'Envoyer'}
          </button>
        </form>
      </section>
    </>
  )
}

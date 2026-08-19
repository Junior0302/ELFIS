import { useCallback, useEffect, useRef, useState } from 'react'
import {
  accountingIntelligenceApi,
  type IntelligenceRecommendation,
} from '../services/accountingIntelligenceApi'

type Props = {
  token: string
  orgId: number
  initialPayload?: Record<string, unknown>
}

export default function AccountingIntelligencePanel({
  token,
  orgId,
  initialPayload,
}: Props) {
  const [reco, setReco] = useState<IntelligenceRecommendation | null>(null)
  const [history, setHistory] = useState<Array<Record<string, unknown>>>([])
  const [learned, setLearned] = useState<Array<Record<string, unknown>>>([])
  const [beforeAfter, setBeforeAfter] = useState<Record<string, unknown> | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [comment, setComment] = useState('')
  const startedAt = useRef<number>(Date.now())

  const refreshSide = useCallback(async () => {
    try {
      const [list, learn] = await Promise.all([
        accountingIntelligenceApi.recommendations(token, orgId),
        accountingIntelligenceApi.learning(token, orgId),
      ])
      setHistory((list.items as Array<Record<string, unknown>>) || [])
      setLearned((learn.items as Array<Record<string, unknown>>) || [])
    } catch {
      /* ignore */
    }
  }, [token, orgId])

  useEffect(() => {
    void refreshSide()
  }, [refreshSide])

  async function recommend() {
    if (busy) return
    setBusy(true)
    setError('')
    startedAt.current = Date.now()
    try {
      const prev = reco
      const data = await accountingIntelligenceApi.recommendations(token, orgId, {
        payload: initialPayload,
        generate_proposal: false,
      })
      setReco(data)
      setBeforeAfter({
        before: prev?.recommendation || null,
        after: data.recommendation || null,
      })
      await refreshSide()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Recommandation impossible')
    } finally {
      setBusy(false)
    }
  }

  async function sendFeedback(action: 'accept' | 'modify' | 'reject') {
    if (!reco?.recommendation_id || busy) return
    setBusy(true)
    setError('')
    try {
      const seconds = (Date.now() - startedAt.current) / 1000
      await accountingIntelligenceApi.feedback(token, orgId, {
        action,
        recommendation_id: reco.recommendation_id,
        validation_seconds: seconds,
        comment: comment || undefined,
        modifications:
          action === 'modify'
            ? {
                complete: true,
                accounts: reco.recommendation?.accounts || {},
                journal_code: reco.recommendation?.journal_code,
                vat_rate: reco.recommendation?.vat_rate,
              }
            : undefined,
      })
      setComment('')
      await refreshSide()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Feedback impossible')
    } finally {
      setBusy(false)
    }
  }

  async function retrain() {
    if (busy) return
    setBusy(true)
    try {
      await accountingIntelligenceApi.retrain(token, orgId)
      await refreshSide()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Retrain impossible')
    } finally {
      setBusy(false)
    }
  }

  const score = reco?.confidence?.score ?? reco?.recommendation?.score
  const detail = reco?.confidence?.detail || {}

  return (
    <section className="page-section">
      <header>
        <h1>Intelligence comptable V2</h1>
        <p className="muted">
          Recommandations adaptatives — aucune écriture comptable définitive.
        </p>
      </header>

      <div className="actions" style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
        <button type="button" onClick={() => void recommend()} disabled={busy}>
          {busy ? 'Analyse…' : 'Générer une recommandation'}
        </button>
        <button type="button" className="ghost" onClick={() => void retrain()} disabled={busy}>
          Retrain profil
        </button>
      </div>

      {error ? <p className="error">{error}</p> : null}

      {reco ? (
        <div className="stack" style={{ marginTop: '1.25rem' }}>
          <p>
            <strong>Compte</strong> {reco.recommendation?.account_code || '—'} ·{' '}
            <strong>Journal</strong> {reco.recommendation?.journal_code || '—'} ·{' '}
            <strong>TVA</strong>{' '}
            {reco.recommendation?.vat_rate != null ? `${reco.recommendation.vat_rate} %` : '—'}
          </p>
          <p>
            <strong>Source</strong> {reco.recommendation?.primary_source || '—'} —{' '}
            {reco.recommendation?.reason}
          </p>

          {score != null ? (
            <div>
              <p>
                <strong>Confiance</strong> {(Number(score) * 100).toFixed(0)} %
              </p>
              <div
                style={{
                  height: 8,
                  background: 'var(--border, #ddd)',
                  borderRadius: 4,
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    width: `${Math.round(Number(score) * 100)}%`,
                    height: '100%',
                    background: 'var(--accent, #2a6)',
                  }}
                />
              </div>
              <ul className="muted" style={{ fontSize: '0.9rem' }}>
                {Object.entries(detail).map(([k, v]) => (
                  <li key={k}>
                    {k}: {(Number(v) * 100).toFixed(0)} %
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          <div>
            <h2>Explications</h2>
            <p>{reco.explanation?.narrative}</p>
            <ul>
              <li>{reco.explanation?.why_account}</li>
              <li>{reco.explanation?.why_vat}</li>
              <li>{reco.explanation?.why_journal}</li>
              <li>{reco.explanation?.why_score}</li>
              <li>{reco.explanation?.why_confidence}</li>
            </ul>
          </div>

          {beforeAfter?.before ? (
            <div>
              <h2>Comparaison avant / après</h2>
              <p className="muted">
                Avant : {(beforeAfter.before as { account_code?: string }).account_code} /{' '}
                {(beforeAfter.before as { journal_code?: string }).journal_code}
              </p>
              <p>
                Après : {(beforeAfter.after as { account_code?: string })?.account_code} /{' '}
                {(beforeAfter.after as { journal_code?: string })?.journal_code}
              </p>
            </div>
          ) : null}

          <div>
            <h2>Feedback</h2>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Commentaire (optionnel)"
              rows={2}
              style={{ width: '100%', maxWidth: 480 }}
            />
            <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
              <button type="button" onClick={() => void sendFeedback('accept')} disabled={busy}>
                Accepter
              </button>
              <button type="button" onClick={() => void sendFeedback('modify')} disabled={busy}>
                Modifier & mémoriser
              </button>
              <button
                type="button"
                className="ghost"
                onClick={() => void sendFeedback('reject')}
                disabled={busy}
              >
                Refuser
              </button>
            </div>
          </div>
        </div>
      ) : null}

      <div style={{ marginTop: '2rem', display: 'grid', gap: '1.5rem' }}>
        <div>
          <h2>Historique recommandations</h2>
          {history.length === 0 ? (
            <p className="muted">Aucune recommandation encore.</p>
          ) : (
            <ul>
              {history.slice(0, 8).map((h) => (
                <li key={String(h.id)}>
                  {String(h.party_name || '—')} · {String(h.account_code || '—')} ·{' '}
                  {String(h.journal_code || '—')} · score{' '}
                  {h.score != null ? `${Math.round(Number(h.score) * 100)} %` : '—'}
                </li>
              ))}
            </ul>
          )}
        </div>
        <div>
          <h2>Éléments appris</h2>
          {learned.length === 0 ? (
            <p className="muted">Aucun apprentissage (validation utilisateur requise).</p>
          ) : (
            <ul>
              {learned.slice(0, 8).map((l) => (
                <li key={String(l.id)}>
                  v{String(l.version)} · {String(l.party_name || l.memory_key)} ·{' '}
                  {JSON.stringify(l.preferred_accounts || {})}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </section>
  )
}

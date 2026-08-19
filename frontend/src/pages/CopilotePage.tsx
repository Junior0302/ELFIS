import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import {
  aiAssistantApi,
  confidenceLabel,
  type ChatResponse,
  type HistoryItem,
  type ProposedAction,
  type StructuredAnswer,
} from '../services/aiAssistantApi'

type Msg = {
  role: 'user' | 'assistant'
  text: string
  structured?: StructuredAnswer
  messageId?: string | null
  confidence?: string
  sources?: string[]
  tools?: string[]
  actions?: ProposedAction[]
  feedbackSent?: string
}

function StructuredBubble({
  structured,
  onAction,
}: {
  structured: StructuredAnswer
  onAction: (action: ProposedAction) => void
}) {
  return (
    <div className="assistant-structured">
      {structured.summary ? <p className="assistant-summary">{structured.summary}</p> : null}

      {structured.facts.length ? (
        <section>
          <h4>Faits vérifiés</h4>
          <ul>
            {structured.facts.map((f) => (
              <li key={f}>{f}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {structured.estimates.length ? (
        <section>
          <h4>Estimations</h4>
          <ul>
            {structured.estimates.map((e) => (
              <li key={e}>{e}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {structured.recommendations.length ? (
        <section>
          <h4>Recommandations</h4>
          <ul className="assistant-recs">
            {structured.recommendations.map((r) => (
              <li key={r.text}>
                <strong>{r.text}</strong>
                <p className="muted" style={{ margin: '0.2rem 0 0', fontSize: '0.85rem' }}>
                  Pourquoi ? {r.explanation.why}
                  <br />
                  Données : {r.explanation.data_used.join(', ') || '—'}
                  <br />
                  Calcul : {r.explanation.calculation || '—'}
                  <br />
                  Confiance : {confidenceLabel(r.explanation.confidence)}
                  {r.explanation.data_as_of
                    ? ` · Données au ${new Date(r.explanation.data_as_of).toLocaleString('fr-FR')}`
                    : null}
                </p>
                {r.action ? (
                  <button
                    type="button"
                    className="btn secondary"
                    style={{ marginTop: '0.35rem' }}
                    onClick={() => onAction(r.action!)}
                  >
                    {r.action.label}
                    {r.action.requires_confirmation ? ' (confirmation)' : ''}
                  </button>
                ) : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {structured.missing.length ? (
        <section>
          <h4>Informations manquantes</h4>
          <ul>
            {structured.missing.map((m) => (
              <li key={m}>{m}</li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  )
}

export default function CopilotePage() {
  const { token, orgId, user } = useAuth()
  const navigate = useNavigate()
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [question, setQuestion] = useState('')
  const threadRef = useRef<HTMLDivElement>(null)
  const [messages, setMessages] = useState<Msg[]>([])
  const [history, setHistory] = useState<HistoryItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [toolsCount, setToolsCount] = useState(0)

  const runAction = useCallback(
    (action: ProposedAction) => {
      if (action.requires_confirmation) {
        const ok = window.confirm(
          `${action.label}\n\n${action.description || 'Cette action nécessite une confirmation.'}`,
        )
        if (!ok) return
      }
      navigate(action.href)
    },
    [navigate],
  )

  const ask = useCallback(
    async (q: string) => {
      const clean = q.trim()
      if (clean.length < 1 || !token || orgId == null) return
      setError('')
      setLoading(true)
      setMessages((m) => [...m, { role: 'user', text: clean }])
      setQuestion('')
      try {
        const res: ChatResponse = await aiAssistantApi.chat(token, orgId, clean)
        setMessages((m) => [
          ...m,
          {
            role: 'assistant',
            text: res.answer,
            structured: res.structured,
            messageId: res.message_id,
            confidence: res.confidence,
            sources: res.sources,
            tools: res.tools_used,
            actions: res.actions,
          },
        ])
        const hist = await aiAssistantApi.history(token, orgId, 8)
        setHistory(hist.items)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Réponse IA indisponible')
      } finally {
        setLoading(false)
      }
    },
    [orgId, token],
  )

  const sendFeedback = useCallback(
    async (messageId: string, kind: 'useful' | 'useless' | 'incorrect') => {
      if (!token || orgId == null) return
      try {
        await aiAssistantApi.feedback(token, orgId, messageId, kind)
        setMessages((msgs) =>
          msgs.map((m) => (m.messageId === messageId ? { ...m, feedbackSent: kind } : m)),
        )
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Feedback impossible')
      }
    },
    [orgId, token],
  )

  useEffect(() => {
    const first = user?.first_name || 'vous'
    setMessages([
      {
        role: 'assistant',
        text:
          `Bonjour ${first}. Je suis votre AI Financial Assistant. ` +
          `Je m'appuie uniquement sur vos moteurs internes (Financial, Banking, Vault) — ` +
          `je n'invente jamais de données. Posez une question sur la trésorerie, les impayés, la TVA ou la santé financière.`,
      },
    ])
    if (!token || orgId == null) return

    let cancelled = false
    Promise.all([
      aiAssistantApi.history(token, orgId, 8),
      aiAssistantApi.suggestions(token, orgId),
      aiAssistantApi.tools(token, orgId),
    ])
      .then(([hist, sug, tools]) => {
        if (cancelled) return
        setHistory(hist.items)
        setSuggestions(sug.suggestions)
        setToolsCount(tools.tools.length)
      })
      .catch(() => {
        if (!cancelled) {
          setSuggestions([
            'Que peux-tu faire ?',
            'Quel est l’état de ma trésorerie ?',
            'Résume ma santé financière',
            'Quels clients sont en retard ?',
          ])
        }
      })
    return () => {
      cancelled = true
    }
  }, [orgId, token, user?.first_name])

  useEffect(() => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, loading])

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    void ask(question)
  }

  return (
    <div className="copilot-page">
      <div className="page-head">
        <div>
          <h2>Assistant financier</h2>
          <p>
            Copilote ComptaPilot — TVA, trésorerie, écritures. Le LLM explique, les moteurs
            calculent. Réponses structurées, explicables, avec sources et actions proposées.
          </p>
          <p className="muted">
            <Link to="/platform/aura">Ouvrir Aura dans ELFIS Core</Link>
          </p>
        </div>
        {!user && (
          <Link className="btn secondary" to="/login">
            Se connecter
          </Link>
        )}
      </div>

      <div className="copilot-layout copilot-layout-wide">
        <section className="panel copilot-chat">
          <div className="copilot-chat-head">
            <div className="copilot-avatar" aria-hidden>
              FA
            </div>
            <div>
              <strong>Assistant financier</strong>
              <span className="muted">
                Decision Engine · {toolsCount} outil(s) · jamais de données inventées
              </span>
            </div>
          </div>

          <div className="copilot-thread" ref={threadRef}>
            {messages.map((m, i) => (
              <div key={i} className={`copilot-bubble ${m.role}`}>
                <span className="copilot-role">{m.role === 'user' ? 'Vous' : 'Assistant'}</span>
                {m.role === 'assistant' && m.structured ? (
                  <StructuredBubble structured={m.structured} onAction={runAction} />
                ) : (
                  <p style={{ whiteSpace: 'pre-wrap' }}>{m.text}</p>
                )}

                {m.role === 'assistant' && m.sources?.length ? (
                  <div className="assistant-meta muted" style={{ fontSize: '0.8rem', marginTop: '0.5rem' }}>
                    <div>
                      Confiance : <strong>{confidenceLabel(m.confidence || 'medium')}</strong>
                    </div>
                    <div>Sources : {m.sources.join(', ')}</div>
                    {m.tools?.length ? <div>Outils : {m.tools.join(', ')}</div> : null}
                  </div>
                ) : null}

                {m.role === 'assistant' && m.actions?.length ? (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem', marginTop: '0.5rem' }}>
                    {m.actions.map((a) => (
                      <button
                        key={a.id}
                        type="button"
                        className="btn secondary"
                        onClick={() => runAction(a)}
                      >
                        {a.label}
                        {a.requires_confirmation ? ' *' : ''}
                      </button>
                    ))}
                  </div>
                ) : null}

                {m.role === 'assistant' && m.messageId ? (
                  <div style={{ display: 'flex', gap: '0.35rem', marginTop: '0.5rem', flexWrap: 'wrap' }}>
                    {m.feedbackSent ? (
                      <span className="badge ok">Feedback : {m.feedbackSent}</span>
                    ) : (
                      <>
                        <button
                          type="button"
                          className="btn secondary"
                          onClick={() => void sendFeedback(m.messageId!, 'useful')}
                        >
                          Utile
                        </button>
                        <button
                          type="button"
                          className="btn secondary"
                          onClick={() => void sendFeedback(m.messageId!, 'useless')}
                        >
                          Inutile
                        </button>
                        <button
                          type="button"
                          className="btn secondary"
                          onClick={() => void sendFeedback(m.messageId!, 'incorrect')}
                        >
                          Incorrect
                        </button>
                      </>
                    )}
                  </div>
                ) : null}
              </div>
            ))}
            {loading && (
              <div className="copilot-bubble assistant copilot-typing">
                <span className="copilot-role">Assistant</span>
                <p>Consultation des moteurs internes…</p>
              </div>
            )}
          </div>

          {error && <div className="auth-alert auth-alert-error">{error}</div>}

          <form className="copilot-compose" onSubmit={onSubmit}>
            <textarea
              rows={2}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  void ask(question)
                }
              }}
              placeholder="Écrivez votre question… Ex. Où en est ma trésorerie ?"
              disabled={loading}
            />
            <div className="copilot-compose-actions">
              <button className="btn" type="submit" disabled={loading || !question.trim()}>
                Envoyer
              </button>
            </div>
          </form>
        </section>

        <aside className="panel copilot-side">
          <h3>Suggestions</h3>
          <p className="muted copilot-side-lead">
            Cliquez une question — les réponses affichent faits, estimations, recommandations et
            manques.
          </p>
          <div className="suggestion-list">
            {suggestions.map((s) => (
              <button
                key={s}
                type="button"
                className="suggestion-btn"
                onClick={() => void ask(s)}
                disabled={loading}
              >
                {s}
              </button>
            ))}
          </div>

          <div className="copilot-side-tips" style={{ marginTop: '1.25rem' }}>
            <h4>Historique</h4>
            {history.length === 0 ? (
              <p className="muted">Aucune conversation récente.</p>
            ) : (
              <ul style={{ listStyle: 'none', margin: 0, padding: 0, fontSize: '0.85rem' }}>
                {history.map((h) => (
                  <li key={h.id} style={{ marginBottom: '0.6rem' }}>
                    <button
                      type="button"
                      className="suggestion-btn"
                      style={{ width: '100%', textAlign: 'left' }}
                      onClick={() => void ask(h.question)}
                    >
                      {h.question.slice(0, 80)}
                      {h.question.length > 80 ? '…' : ''}
                    </button>
                    <span className="muted" style={{ fontSize: '0.75rem' }}>
                      Confiance {confidenceLabel(h.confidence)} ·{' '}
                      {(h.tools_used || []).slice(0, 3).join(', ')}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </aside>
      </div>
    </div>
  )
}

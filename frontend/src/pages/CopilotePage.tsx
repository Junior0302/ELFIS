import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'

type Msg = { role: 'user' | 'assistant'; text: string }

export default function CopilotePage() {
  const { token, orgId, user } = useAuth()
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [question, setQuestion] = useState('')
  const threadRef = useRef<HTMLDivElement>(null)
  const [messages, setMessages] = useState<Msg[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const ask = useCallback(
    async (q: string) => {
      const clean = q.trim()
      if (clean.length < 1) return
      setError('')
      setLoading(true)
      setMessages((m) => [...m, { role: 'user', text: clean }])
      setQuestion('')
      try {
        const res = await api.aiChat(clean, token, orgId)
        setMessages((m) => [...m, { role: 'assistant', text: res.answer }])
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Réponse IA indisponible')
      } finally {
        setLoading(false)
      }
    },
    [orgId, token],
  )

  useEffect(() => {
    const first = user?.first_name || 'vous'
    const welcome: Msg = {
      role: 'assistant',
      text:
        `Bonjour ${first}. Je suis votre Finance Agent. ` +
        `Posez vos questions en texte : trésorerie, impayés, marge, priorités du jour. ` +
        `Les réponses s’appuient sur les données de votre entreprise.`,
    }
    setMessages([welcome])
    if (!token) return

    let cancelled = false
    api
      .aiConversations(token, orgId)
      .then(({ conversations }) => {
        if (cancelled || conversations.length === 0) return
        const history = conversations
          .slice(0, 6)
          .reverse()
          .flatMap<Msg>((conversation) => [
            { role: 'user', text: conversation.question },
            { role: 'assistant', text: conversation.answer },
          ])
        setMessages([welcome, ...history])
      })
      .catch(() => undefined)
    return () => {
      cancelled = true
    }
  }, [orgId, token, user?.first_name])

  useEffect(() => {
    if (!token) return
    api
      .aiSuggestions(token, orgId)
      .then((r) => setSuggestions(r.suggestions))
      .catch(() =>
        setSuggestions([
          'Que peux-tu faire ?',
          'Résume mon activité simplement',
          'Comment se porte ma marge ?',
          'Quels clients sont en retard ?',
        ]),
      )
  }, [token, orgId])

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
          <h2>Copilote IA</h2>
          <p>
            Chat avec votre directeur financier virtuel — réponses claires, basées sur vos données
            d’entreprise.
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
              <strong>Finance Agent</strong>
              <span className="muted">Mode chat · en ligne</span>
            </div>
          </div>

          <div className="copilot-thread" ref={threadRef}>
            {messages.map((m, i) => (
              <div key={i} className={`copilot-bubble ${m.role}`}>
                <span className="copilot-role">{m.role === 'user' ? 'Vous' : 'Finance Agent'}</span>
                <p>{m.text}</p>
              </div>
            ))}
            {loading && (
              <div className="copilot-bubble assistant copilot-typing">
                <span className="copilot-role">Finance Agent</span>
                <p>Je réfléchis…</p>
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
            Cliquez une question pour démarrer, ou tapez librement dans le chat.
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
          <div className="copilot-side-tips">
            <h4>Exemples utiles</h4>
            <ul>
              <li>« Résume mon activité »</li>
              <li>« Quels clients sont en retard ? »</li>
              <li>« Où en est ma TVA ? »</li>
              <li>« Quelles sont mes priorités ? »</li>
            </ul>
          </div>
        </aside>
      </div>
    </div>
  )
}

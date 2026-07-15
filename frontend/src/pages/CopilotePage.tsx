import { useEffect, useRef, useState, type FormEvent } from 'react'
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

  useEffect(() => {
    const first = user?.first_name || 'vous'
    setMessages([
      {
        role: 'assistant',
        text:
          `Bonjour ${first} 👋 Je suis votre Finance Agent, le copilote du dirigeant. ` +
          `Je peux vous expliquer votre CA, votre marge, votre trésorerie ou un investissement. ` +
          `Par où souhaitez-vous commencer ?`,
      },
    ])
  }, [user?.first_name])

  useEffect(() => {
    api
      .aiSuggestions()
      .then((r) => setSuggestions(r.suggestions))
      .catch(() =>
        setSuggestions([
          'Que peux-tu faire ?',
          'Quel est l’état de ma trésorerie ?',
          'Pourquoi ma marge baisse-t-elle ?',
          'Quels clients sont en retard ?',
        ]),
      )
  }, [])

  useEffect(() => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, loading])

  const ask = async (q: string) => {
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
  }

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
            Discutez librement avec votre directeur financier virtuel — explications claires,
            recommandations actionnables.
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
              <span className="muted">En ligne · basé sur vos données d’entreprise</span>
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
              placeholder="Écrivez ici… Ex. Bonjour, où en est ma trésorerie ?"
              disabled={loading}
            />
            <button className="btn" type="submit" disabled={loading || !question.trim()}>
              Envoyer
            </button>
          </form>
        </section>

        <aside className="panel copilot-side">
          <h3>Pour démarrer</h3>
          <p className="muted copilot-side-lead">
            Cliquez une suggestion, ou écrivez comme à un collègue — « Bonjour », « Que peux-tu faire
            ? », ou une question précise.
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
            <h4>Des réponses fiables</h4>
            <ul>
              <li>Connectez un compte dans Banque</li>
              <li>Déposez vos factures fournisseur</li>
              <li>Émettez devis et factures clients</li>
            </ul>
          </div>
        </aside>
      </div>
    </div>
  )
}

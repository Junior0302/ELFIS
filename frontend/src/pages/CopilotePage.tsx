import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import JarvisOrb from '../components/JarvisOrb'
import { useVoiceAssistant } from '../hooks/useVoiceAssistant'

type Msg = { role: 'user' | 'assistant'; text: string; viaVoice?: boolean }

export default function CopilotePage() {
  const { token, orgId, user } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [question, setQuestion] = useState('')
  const threadRef = useRef<HTMLDivElement>(null)
  const [messages, setMessages] = useState<Msg[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const voiceBootRef = useRef(false)

  const {
    supported,
    phase,
    interim,
    error: voiceError,
    setError: setVoiceError,
    autoSpeak,
    setAutoSpeak,
    startListening,
    toggleListening,
    speak,
    stopSpeaking,
    markProcessing,
    markIdle,
  } = useVoiceAssistant({
    onFinalTranscript: (text) => {
      void askVoiceRef.current(text)
    },
  })

  const autoSpeakRef = useRef(autoSpeak)
  autoSpeakRef.current = autoSpeak

  const ask = useCallback(
    async (q: string, opts?: { fromVoice?: boolean }) => {
      const clean = q.trim()
      if (clean.length < 1) return
      setError('')
      setVoiceError('')
      setLoading(true)
      markProcessing()
      stopSpeaking()
      setMessages((m) => [...m, { role: 'user', text: clean, viaVoice: opts?.fromVoice }])
      setQuestion('')
      try {
        const res = await api.aiChat(clean, token, orgId)
        setMessages((m) => [...m, { role: 'assistant', text: res.answer }])
        if (autoSpeakRef.current || opts?.fromVoice) {
          speak(res.answer)
        } else {
          markIdle()
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Réponse IA indisponible')
        markIdle()
      } finally {
        setLoading(false)
      }
    },
    [markIdle, markProcessing, orgId, setVoiceError, speak, stopSpeaking, token],
  )

  const askVoiceRef = useRef<(q: string) => Promise<void>>(async () => {})
  askVoiceRef.current = (q: string) => ask(q, { fromVoice: true })

  useEffect(() => {
    const first = user?.first_name || 'vous'
    const welcome: Msg = {
      role: 'assistant',
      text:
        `Bonjour ${first}. Je suis votre Finance Agent vocal. ` +
        `Parlez-moi naturellement ou écrivez : trésorerie, impayés, marge, priorités du jour. ` +
        `Appuyez sur l’orbe pour activer le mode Jarvis.`,
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
    api
      .aiSuggestions()
      .then((r) => setSuggestions(r.suggestions))
      .catch(() =>
        setSuggestions([
          'Que peux-tu faire ?',
          'Résume mon activité simplement',
          'Comment se porte ma marge ?',
          'Quels clients sont en retard ?',
        ]),
      )
  }, [])

  useEffect(() => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, loading, interim])

  useEffect(() => {
    if (voiceBootRef.current) return
    if (searchParams.get('voice') !== '1') return
    voiceBootRef.current = true
    setSearchParams({}, { replace: true })
    const timer = window.setTimeout(() => {
      if (supported) startListening()
    }, 450)
    return () => window.clearTimeout(timer)
  }, [searchParams, setSearchParams, startListening, supported])

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    void ask(question)
  }

  const statusLine =
    phase === 'listening'
      ? 'Mode Jarvis · écoute active'
      : phase === 'speaking'
        ? 'Mode Jarvis · réponse vocale'
        : phase === 'processing'
          ? 'Mode Jarvis · analyse'
          : supported
            ? 'En ligne · texte & voix'
            : 'En ligne · texte (voix non supportée)'

  return (
    <div className={`copilot-page jarvis-mode ${phase}`}>
      <div className="page-head">
        <div>
          <h2>Copilote IA</h2>
          <p>
            Votre directeur financier virtuel — parlez ou écrivez. Réponses claires, basées sur vos
            données d’entreprise.
          </p>
        </div>
        {!user && (
          <Link className="btn secondary" to="/login">
            Se connecter
          </Link>
        )}
      </div>

      <div className="copilot-layout copilot-layout-wide">
        <section className="panel copilot-chat jarvis-panel">
          <div className="copilot-chat-head">
            <div className={`copilot-avatar jarvis-avatar ${phase}`} aria-hidden>
              FA
            </div>
            <div>
              <strong>Finance Agent</strong>
              <span className="muted">{statusLine}</span>
            </div>
            <label className="jarvis-autospeak">
              <input
                type="checkbox"
                checked={autoSpeak}
                onChange={(e) => setAutoSpeak(e.target.checked)}
              />
              Lecture auto
            </label>
          </div>

          <JarvisOrb
            phase={phase}
            interim={interim}
            onToggle={() => {
              if (phase === 'speaking') {
                stopSpeaking()
                return
              }
              toggleListening()
            }}
            disabled={loading}
          />

          <div className="copilot-thread" ref={threadRef}>
            {messages.map((m, i) => (
              <div key={i} className={`copilot-bubble ${m.role}`}>
                <span className="copilot-role">
                  {m.role === 'user' ? (m.viaVoice ? 'Vous · voix' : 'Vous') : 'Finance Agent'}
                </span>
                <p>{m.text}</p>
                {m.role === 'assistant' && (
                  <button
                    type="button"
                    className="jarvis-speak-btn"
                    onClick={() => {
                      stopSpeaking()
                      speak(m.text)
                    }}
                    disabled={!supported}
                  >
                    Écouter
                  </button>
                )}
              </div>
            ))}
            {loading && (
              <div className="copilot-bubble assistant copilot-typing">
                <span className="copilot-role">Finance Agent</span>
                <p>Je réfléchis…</p>
              </div>
            )}
          </div>

          {(error || voiceError) && (
            <div className="auth-alert auth-alert-error">{error || voiceError}</div>
          )}

          <form className="copilot-compose jarvis-compose" onSubmit={onSubmit}>
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
              placeholder={
                phase === 'listening'
                  ? 'Écoute en cours… ou tapez ici'
                  : 'Écrivez ou parlez… Ex. Où en est ma trésorerie ?'
              }
              disabled={loading}
            />
            <div className="jarvis-compose-actions">
              <button
                type="button"
                className={`btn secondary jarvis-mic-btn ${phase === 'listening' ? 'is-hot' : ''}`}
                onClick={() => toggleListening()}
                disabled={loading || !supported}
                aria-pressed={phase === 'listening'}
              >
                {phase === 'listening' ? 'Stop micro' : 'Parler'}
              </button>
              <button className="btn" type="submit" disabled={loading || !question.trim()}>
                Envoyer
              </button>
            </div>
          </form>
        </section>

        <aside className="panel copilot-side">
          <h3>Mode Jarvis</h3>
          <p className="muted copilot-side-lead">
            Appuyez sur l’orbe, posez votre question à voix haute, puis écoutez la réponse. Chrome
            ou Edge recommandés (micro HTTPS requis).
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
            <h4>Astuces vocales</h4>
            <ul>
              <li>« Résume mon activité »</li>
              <li>« Quels clients sont en retard ? »</li>
              <li>« Où en est ma TVA ? »</li>
              <li>Coupez la lecture auto si besoin</li>
            </ul>
          </div>
        </aside>
      </div>
    </div>
  )
}

import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../auth'
import { mapLoginFailure } from '../authNetwork'
import { sanitizeReturnPath } from '../platform-routing/returnPath'
import { LoginBrandPanel } from './LoginBrandPanel'
import { LoginForm } from './LoginForm'
import './login.css'

function resolveAfterAuthPath(inviteToken: string | null, from: unknown): string {
  if (inviteToken) {
    return `/compte?invite=${encodeURIComponent(inviteToken)}`
  }
  return sanitizeReturnPath(from, '/home')
}

/**
 * Login ELFIS Core V1 — expérience premium alignée Landing.
 * Flux auth inchangé : Firebase → POST /api/auth/firebase → session.
 */
export function LoginPage() {
  const { login, user, firebaseReady } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams] = useSearchParams()
  const inviteToken = searchParams.get('invite')
  const from = (location.state as { from?: string } | null)?.from

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const mountedRef = useRef(true)
  const submittingRef = useRef(false)
  const errorRef = useRef<HTMLDivElement>(null)

  const afterAuthPath = resolveAfterAuthPath(inviteToken, from)

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
    }
  }, [])

  useEffect(() => {
    if (user) navigate(afterAuthPath, { replace: true })
  }, [user, navigate, afterAuthPath])

  useEffect(() => {
    if (error) errorRef.current?.focus()
  }, [error])

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (loading || submittingRef.current || !firebaseReady) return
    submittingRef.current = true
    setLoading(true)
    setError('')
    try {
      await login(email.trim(), password)
      if (mountedRef.current) navigate(afterAuthPath, { replace: true })
    } catch (err) {
      if (mountedRef.current) setError(mapLoginFailure(err))
    } finally {
      submittingRef.current = false
      if (mountedRef.current) setLoading(false)
    }
  }

  const registerTo = inviteToken
    ? `/register?invite=${encodeURIComponent(inviteToken)}`
    : '/register'

  return (
    <div className="elfis-login" data-product="elfis-core">
      <header className="elfis-login__top">
        <Link to="/" className="elfis-login__brand" aria-label="ELFIS Core — accueil">
          <img src="/favicon.svg" alt="" width={40} height={40} decoding="async" />
          <span>
            <strong>ELFIS Core</strong>
            <small>Plateforme</small>
          </span>
        </Link>
        <Link className="elfis-login__back" to="/">
          Retour au site
        </Link>
      </header>

      <div className="elfis-login__grid">
        <LoginBrandPanel />
        <section className="elfis-login__panel" aria-labelledby="elfis-login-title">
          <div className="elfis-login__card">
            <header className="elfis-login__card-head">
              <h1 id="elfis-login-title">Connexion</h1>
              <p>Une seule connexion pour accéder à tout l&apos;écosystème ELFIS.</p>
            </header>

            {!firebaseReady ? (
              <div className="elfis-login__alert" role="alert" aria-live="polite">
                Connexion indisponible pour le moment. Réessayez plus tard ou contactez le support.
              </div>
            ) : null}

            <LoginForm
              email={email}
              password={password}
              loading={loading}
              disabled={!firebaseReady}
              error={error}
              errorRef={errorRef}
              onEmailChange={setEmail}
              onPasswordChange={setPassword}
              onSubmit={onSubmit}
              forgotPasswordTo="/forgot-password"
            />

            <p className="elfis-login__switch">
              Pas encore de compte ? <Link to={registerTo}>Créer un compte</Link>
            </p>
            <p className="elfis-login__home">
              <Link to="/">← Retour à l&apos;accueil</Link>
            </p>
          </div>
        </section>
      </div>
    </div>
  )
}

export default LoginPage

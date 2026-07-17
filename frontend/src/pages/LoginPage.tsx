import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../auth'

export default function LoginPage() {
  const { login, user, firebaseReady } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const inviteToken = searchParams.get('invite')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const afterAuthPath = inviteToken
    ? `/compte?invite=${encodeURIComponent(inviteToken)}`
    : '/dashboard'

  useEffect(() => {
    if (user) navigate(afterAuthPath)
  }, [user, navigate, afterAuthPath])

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      await login(email.trim(), password)
      navigate(afterAuthPath)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Connexion impossible')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-card">
      <div className="auth-card-head">
        <h2>Connexion</h2>
        <p>Accédez à votre espace ComptaPilot avec votre email et mot de passe.</p>
      </div>

      {!firebaseReady && (
        <div className="auth-alert auth-alert-error">
          Connexion indisponible pour le moment. Réessayez plus tard ou contactez le support.
        </div>
      )}

      <form className="auth-form" onSubmit={onSubmit}>
        <div className="field">
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            placeholder="vous@entreprise.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>
        <div className="field">
          <div className="auth-field-heading">
            <label htmlFor="password">Mot de passe</label>
            <Link to="/forgot-password">Mot de passe oublié ?</Link>
          </div>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            placeholder="Votre mot de passe"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>

        {error && <div className="auth-alert auth-alert-error">{error}</div>}

        <button className="btn auth-submit" type="submit" disabled={loading || !firebaseReady}>
          {loading ? 'Connexion…' : 'Se connecter'}
        </button>
      </form>

      <p className="auth-switch">
        Pas encore de compte ?{' '}
        <Link to={inviteToken ? `/register?invite=${encodeURIComponent(inviteToken)}` : '/register'}>
          Créer un compte
        </Link>
      </p>
      <p className="auth-home-link">
        <Link to="/">← Retour à l&apos;accueil</Link>
      </p>
    </div>
  )
}

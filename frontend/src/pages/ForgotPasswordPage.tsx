import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { mapFirebaseError, resetFirebasePassword } from '../firebase'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [sent, setSent] = useState(false)

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      await resetFirebasePassword(email.trim())
      setSent(true)
    } catch (reason) {
      setError(mapFirebaseError(reason))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-card">
      <div className="auth-card-head">
        <h2>Mot de passe oublié</h2>
        <p>Recevez un lien Firebase sécurisé pour choisir un nouveau mot de passe.</p>
      </div>

      {sent ? (
        <div className="password-reset-success">
          <div className="password-reset-icon" aria-hidden>
            ✓
          </div>
          <h3>Consultez votre boîte mail</h3>
          <p>
            Si un compte existe pour <strong>{email}</strong>, vous recevrez le lien de
            réinitialisation dans quelques instants.
          </p>
          <Link className="btn auth-submit" to="/login">
            Retour à la connexion
          </Link>
        </div>
      ) : (
        <form className="auth-form" onSubmit={onSubmit}>
          <div className="field">
            <label htmlFor="reset_email">Adresse email</label>
            <input
              id="reset_email"
              type="email"
              autoComplete="email"
              placeholder="vous@entreprise.com"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </div>
          {error && <div className="auth-alert auth-alert-error">{error}</div>}
          <button className="btn auth-submit" type="submit" disabled={loading}>
            {loading ? 'Envoi…' : 'Envoyer le lien'}
          </button>
        </form>
      )}

      {!sent && (
        <p className="auth-switch">
          <Link to="/login">← Retour à la connexion</Link>
        </p>
      )}
    </div>
  )
}

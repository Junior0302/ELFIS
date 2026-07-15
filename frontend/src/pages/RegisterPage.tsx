import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

export default function RegisterPage() {
  const { register, user, firebaseReady } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({
    first_name: '',
    last_name: '',
    email: '',
    password: '',
    organization_name: '',
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (user) navigate('/')
  }, [user, navigate])

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (form.password.length < 8) {
      setError('Le mot de passe doit contenir au moins 8 caractères.')
      return
    }
    setLoading(true)
    setError('')
    try {
      await register({
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        email: form.email.trim(),
        password: form.password,
        organization_name: form.organization_name.trim() || undefined,
      })
      navigate('/')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Inscription impossible')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-card">
      <div className="auth-card-head">
        <h2>Créer un compte</h2>
        <p>Compte Firebase + organisation ComptaPilot en une étape.</p>
      </div>

      {!firebaseReady && (
        <div className="auth-alert auth-alert-error">
          Firebase n&apos;est pas configuré. Renseignez les variables{' '}
          <code>VITE_FIREBASE_*</code> dans <code>frontend/.env</code>.
        </div>
      )}

      <form className="auth-form" onSubmit={onSubmit}>
        <div className="form-grid auth-form-grid">
          <div className="field">
            <label htmlFor="first_name">Prénom</label>
            <input
              id="first_name"
              value={form.first_name}
              onChange={(e) => setForm({ ...form, first_name: e.target.value })}
              required
            />
          </div>
          <div className="field">
            <label htmlFor="last_name">Nom</label>
            <input
              id="last_name"
              value={form.last_name}
              onChange={(e) => setForm({ ...form, last_name: e.target.value })}
              required
            />
          </div>
        </div>
        <div className="field">
          <label htmlFor="reg_email">Email</label>
          <input
            id="reg_email"
            type="email"
            autoComplete="email"
            placeholder="vous@entreprise.com"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            required
          />
        </div>
        <div className="field">
          <label htmlFor="reg_password">Mot de passe</label>
          <input
            id="reg_password"
            type="password"
            autoComplete="new-password"
            placeholder="8 caractères minimum"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            required
            minLength={8}
          />
        </div>
        <div className="field">
          <label htmlFor="org">Nom de l&apos;entreprise</label>
          <input
            id="org"
            placeholder="Mon Entreprise SAS"
            value={form.organization_name}
            onChange={(e) => setForm({ ...form, organization_name: e.target.value })}
            required
          />
        </div>

        {error && <div className="auth-alert auth-alert-error">{error}</div>}

        <button className="btn auth-submit" type="submit" disabled={loading || !firebaseReady}>
          {loading ? 'Création…' : 'Créer mon compte'}
        </button>
      </form>

      <p className="auth-switch">
        Déjà inscrit ? <Link to="/login">Se connecter</Link>
      </p>
    </div>
  )
}

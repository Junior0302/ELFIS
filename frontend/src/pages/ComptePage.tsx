import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import {
  mapFirebaseError,
  saveFirestoreProfile,
  updateFirebaseUserPassword,
} from '../firebase'

export default function ComptePage() {
  const { token, orgId, user, memberships, setUser } = useAuth()
  const [form, setForm] = useState({
    first_name: '',
    last_name: '',
    phone: '',
    password: '',
    password_confirm: '',
  })
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [avatarFile, setAvatarFile] = useState<File | null>(null)
  const [avatarPreview, setAvatarPreview] = useState('')

  useEffect(() => {
    if (!user) return
    setForm((f) => ({
      ...f,
      first_name: user.first_name || '',
      last_name: user.last_name || '',
      phone: user.phone || '',
    }))
  }, [user])

  useEffect(() => {
    if (!avatarFile) {
      setAvatarPreview(user?.avatar || '')
      return
    }
    const url = URL.createObjectURL(avatarFile)
    setAvatarPreview(url)
    return () => URL.revokeObjectURL(url)
  }, [avatarFile, user?.avatar])

  if (!user || !token) {
    return (
      <div className="panel account-gate">
        <h2>Mon compte</h2>
        <p className="muted">
          Votre profil, vos organisations et la sécurité du compte — connectez-vous pour y accéder.
        </p>
        <Link className="btn" to="/login">
          Se connecter
        </Link>
      </div>
    )
  }

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setMessage('')
    setError('')
    if (form.password && form.password !== form.password_confirm) {
      setError('Les mots de passe ne correspondent pas.')
      return
    }
    if (form.password && form.password.length < 8) {
      setError('Le mot de passe doit contenir au moins 8 caractères.')
      return
    }
    setSaving(true)
    try {
      let avatar = user.avatar || ''
      if (avatarFile) {
        const uploaded = await api.uploadAvatar(avatarFile, token, orgId)
        avatar = uploaded.user.avatar || ''
      }
      const payload = {
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        phone: form.phone.trim(),
        avatar,
      }
      const res = await api.updateProfile(payload, token, orgId)
      if (form.password) await updateFirebaseUserPassword(form.password)
      await saveFirestoreProfile(res.user)
      setUser(res.user)
      setAvatarFile(null)
      setForm((f) => ({ ...f, password: '', password_confirm: '' }))
      setMessage('Profil et photo synchronisés avec Firebase.')
    } catch (err) {
      setError(mapFirebaseError(err))
    } finally {
      setSaving(false)
    }
  }

  const initials = `${user.first_name?.[0] || ''}${user.last_name?.[0] || ''}`.toUpperCase() || '?'

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Mon compte</h2>
          <p>
            Mettez à jour votre identité, votre téléphone et votre mot de passe. Vos appartenances
            multi-entreprises apparaissent juste en dessous.
          </p>
        </div>
      </div>

      <div className="account-grid">
        <section className="panel account-card">
          <div className="account-hero">
            <div className="account-avatar" aria-hidden>
              {avatarPreview ? <img src={avatarPreview} alt="" /> : initials}
            </div>
            <div>
              <h3>
                {user.first_name} {user.last_name}
              </h3>
              <p className="muted">{user.email}</p>
              <span className={`badge ${user.status === 'active' ? '' : 'warn'}`}>{user.status}</span>
            </div>
          </div>

          <div className="account-photo-field">
            <label className="btn secondary" htmlFor="account_avatar">
              Choisir une photo
            </label>
            <input
              id="account_avatar"
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={(event) => setAvatarFile(event.target.files?.[0] || null)}
            />
            <span className="muted">JPG, PNG ou WebP · 5 Mo maximum</span>
          </div>

          <form className="account-form" onSubmit={onSubmit}>
            <div className="form-grid">
              <div className="field">
                <label htmlFor="acc_first">Prénom</label>
                <input
                  id="acc_first"
                  value={form.first_name}
                  onChange={(e) => setForm({ ...form, first_name: e.target.value })}
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="acc_last">Nom</label>
                <input
                  id="acc_last"
                  value={form.last_name}
                  onChange={(e) => setForm({ ...form, last_name: e.target.value })}
                  required
                />
              </div>
              <div className="field full">
                <label htmlFor="acc_email">Email</label>
                <input id="acc_email" type="email" value={user.email} disabled />
                <small className="field-hint">L&apos;email sert d&apos;identifiant de connexion.</small>
              </div>
              <div className="field full">
                <label htmlFor="acc_phone">Téléphone</label>
                <input
                  id="acc_phone"
                  type="tel"
                  placeholder="+33 6 00 00 00 00"
                  value={form.phone}
                  onChange={(e) => setForm({ ...form, phone: e.target.value })}
                />
              </div>
            </div>

            <h4 className="account-section-title">Sécurité</h4>
            <p className="muted">
              Le nouveau mot de passe est enregistré directement dans Firebase Authentication.
              Une reconnexion récente peut être demandée par sécurité.
            </p>
            <div className="form-grid">
              <div className="field">
                <label htmlFor="acc_pwd">Nouveau mot de passe</label>
                <input
                  id="acc_pwd"
                  type="password"
                  autoComplete="new-password"
                  placeholder="Laisser vide pour ne pas changer"
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                />
              </div>
              <div className="field">
                <label htmlFor="acc_pwd2">Confirmer</label>
                <input
                  id="acc_pwd2"
                  type="password"
                  autoComplete="new-password"
                  value={form.password_confirm}
                  onChange={(e) => setForm({ ...form, password_confirm: e.target.value })}
                />
              </div>
            </div>

            {error && <div className="auth-alert auth-alert-error">{error}</div>}
            {message && <div className="auth-alert auth-alert-ok">{message}</div>}

            <div className="actions">
              <button className="btn" type="submit" disabled={saving}>
                {saving ? 'Enregistrement…' : 'Enregistrer le profil'}
              </button>
            </div>
          </form>
        </section>

        <aside className="panel account-side">
          <h3>Mes organisations</h3>
          <div className="list">
            {memberships.map((m) => (
              <div key={m.membership_id} className="membership-chip">
                <strong>{m.organization_name}</strong>
                <span className="badge">{m.role}</span>
                <span className="muted">
                  {m.country} · accès {m.role}
                </span>
              </div>
            ))}
          </div>
          <Link className="btn secondary" to="/organisation" style={{ marginTop: '1rem', display: 'inline-flex' }}>
            Voir l&apos;organisation
          </Link>
        </aside>
      </div>
    </>
  )
}

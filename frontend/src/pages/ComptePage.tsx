import { useEffect, useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import {
  api,
  type OrgInvitation,
  type ProfessionalEmailRecord,
  type TeamNotificationItem,
} from '../api'
import { useAuth } from '../auth'
import {
  mapFirebaseError,
  saveFirestoreProfile,
  updateFirebaseUserPassword,
} from '../firebase'
import { FEATURE_LABELS_FR, ROLE_LABELS_FR, planIncludesFeature } from '../planFeatures'

export default function ComptePage() {
  const {
    token,
    orgId,
    user,
    memberships,
    setUser,
    setOrgId,
    setMemberships,
    refreshSession,
  } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
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
  const [invitations, setInvitations] = useState<OrgInvitation[]>([])
  const [notifications, setNotifications] = useState<TeamNotificationItem[]>([])
  const [inviteBusy, setInviteBusy] = useState<number | string | null>(null)
  const [proEmails, setProEmails] = useState<ProfessionalEmailRecord[]>([])
  const [proCanRequest, setProCanRequest] = useState(false)
  const [proHasPending, setProHasPending] = useState(false)
  const [proHasActive, setProHasActive] = useState(false)
  const [proBusy, setProBusy] = useState(false)
  const [proMessage, setProMessage] = useState('')
  const [proError, setProError] = useState('')

  useEffect(() => {
    const checkout = new URLSearchParams(location.search).get('checkout')
    if (checkout === 'success' || checkout === 'cancel') {
      navigate(`/abonnement?checkout=${checkout}`, { replace: true })
    }
  }, [location.search, navigate])

  useEffect(() => {
    if (!token) return
    void api.myInvitations(token, orgId).then((data) => setInvitations(data.invitations))
    void api.myNotifications(token, orgId).then((data) => setNotifications(data.notifications))
    void api
      .myProfessionalEmails(token, orgId)
      .then((data) => {
        setProEmails(data.emails)
        setProCanRequest(data.can_request)
        setProHasPending(data.has_pending)
        setProHasActive(data.has_active)
      })
      .catch(() => undefined)
  }, [token, orgId, memberships.length])

  useEffect(() => {
    const inviteToken = new URLSearchParams(location.search).get('invite')
    if (!inviteToken || !token) return
    setInviteBusy(inviteToken)
    void api
      .acceptInvitation({ token: inviteToken }, token, orgId)
      .then(async (result) => {
        setMemberships(result.memberships)
        setInvitations(result.pending_invitations)
        setOrgId(result.organization_id)
        setMessage('Invitation acceptée. Vous êtes membre de l’organisation.')
        navigate('/compte', { replace: true })
        await refreshSession()
      })
      .catch((reason) => {
        setError(reason instanceof Error ? reason.message : 'Invitation invalide')
      })
      .finally(() => setInviteBusy(null))
  }, [location.search, token])

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

  const inviteParam = new URLSearchParams(location.search).get('invite')

  if (!user || !token) {
    return (
      <div className="panel account-gate">
        <h2>Mon compte</h2>
        <p className="muted">
          {inviteParam
            ? 'Connectez-vous ou créez un compte avec l’adresse invitée pour rejoindre l’organisation.'
            : 'Votre profil, vos organisations et la sécurité du compte — connectez-vous pour y accéder.'}
        </p>
        <div className="actions" style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          <Link
            className="btn"
            to={inviteParam ? `/login?invite=${encodeURIComponent(inviteParam)}` : '/login'}
          >
            Se connecter
          </Link>
          <Link
            className="btn secondary"
            to={inviteParam ? `/register?invite=${encodeURIComponent(inviteParam)}` : '/register'}
          >
            Créer un compte
          </Link>
        </div>
      </div>
    )
  }

  const requestProEmail = async () => {
    if (!token) return
    setProBusy(true)
    setProError('')
    setProMessage('')
    try {
      const res = await api.requestProfessionalEmail(token, orgId)
      setProMessage(res.message)
      setProCanRequest(false)
      setProHasPending(true)
      setProEmails((current) => [res.email, ...current])
    } catch (reason) {
      setProError(reason instanceof Error ? reason.message : 'Demande impossible')
    } finally {
      setProBusy(false)
    }
  }

  const acceptInvite = async (payload: { invitation_id?: number; token?: string }) => {
    setInviteBusy(payload.invitation_id ?? payload.token ?? 'x')
    setError('')
    setMessage('')
    try {
      const result = await api.acceptInvitation(payload, token, orgId)
      setMemberships(result.memberships)
      setInvitations(result.pending_invitations)
      setOrgId(result.organization_id)
      setMessage('Invitation acceptée.')
      await refreshSession()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Acceptation impossible')
    } finally {
      setInviteBusy(null)
    }
  }

  const refuseInvite = async (invitationId: number) => {
    setInviteBusy(invitationId)
    try {
      const result = await api.refuseInvitation({ invitation_id: invitationId }, token, orgId)
      setInvitations(result.pending_invitations)
      setMessage('Invitation refusée.')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Refus impossible')
    } finally {
      setInviteBusy(null)
    }
  }

  const leaveOrg = async (organizationId: number, name: string) => {
    if (!window.confirm(`Quitter « ${name} » ? Vous perdrez immédiatement l’accès.`)) return
    try {
      const result = await api.leaveOrganization(organizationId, token, orgId)
      setMemberships(result.memberships)
      if (orgId === organizationId && result.memberships[0]) {
        setOrgId(result.memberships[0].organization_id)
      }
      setMessage(`Vous avez quitté ${name}.`)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Départ impossible')
    }
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
      setMessage('Profil et photo mis à jour.')
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
              Le nouveau mot de passe est enregistré de façon sécurisée. Une reconnexion récente
              peut être demandée.
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

        <section className="panel account-card" aria-label="Adresse e-mail professionnelle">
          <h3>Adresse e-mail professionnelle</h3>
          <p className="muted">
            Pour envoyer devis et factures, vous avez 2 choix : votre e-mail personnel (messagerie),
            ou une adresse fournie par ELFIS Core (ex. jean.dupont@elfis-core.com) pour envoyer
            directement depuis l’outil.
          </p>
          {proHasActive ? (
            <>
              <p>
                Votre adresse ELFIS Core est <strong>active</strong>. Elle apparaît comme expéditeur
                dans Devis / Facturation → Envoyer.
              </p>
              <div className="list">
                {proEmails
                  .filter((row) => row.status === 'active')
                  .map((row) => (
                    <div key={row.id} className="membership-chip">
                      <strong>{row.email}</strong>
                      <span className="badge">Active{row.is_default ? ' · Par défaut' : ''}</span>
                    </div>
                  ))}
              </div>
            </>
          ) : proHasPending ? (
            <div className="email-sender-notice" role="status">
              <strong>Votre demande a bien été envoyée.</strong>
              <p>
                Notre équipe prépare actuellement votre adresse professionnelle (Brevo). Vous
                recevrez vos accès sous 24 heures maximum. Surveillez votre boîte mail.
              </p>
            </div>
          ) : (
            <>
              <p>
                Vous ne possédez pas encore d’adresse ELFIS Core.
              </p>
              <p className="muted">
                Cliquez ci-dessous : aucune saisie. Nous récupérons nom, prénom, e-mail, téléphone,
                société, abonnement et statut depuis votre compte, puis notifions{' '}
                <strong>urequest@elfis-core.com</strong>. Vous recevez aussi un accusé de réception.
              </p>
              <div className="actions">
                <button
                  type="button"
                  className="btn"
                  disabled={proBusy || !proCanRequest}
                  onClick={() => void requestProEmail()}
                >
                  {proBusy ? 'Envoi…' : 'Demander mon adresse'}
                </button>
              </div>
            </>
          )}
          {proError && <p className="form-error">{proError}</p>}
          {proMessage && <p className="muted">{proMessage}</p>}
        </section>

        <aside className="panel account-side">
          {!!invitations.length && (
            <>
              <h3>Invitations reçues</h3>
              <div className="list" style={{ marginBottom: '1.25rem' }}>
                {invitations.map((invite) => (
                  <div key={invite.id} className="membership-chip">
                    <strong>{invite.organization_name || 'Organisation'}</strong>
                    <span className="badge">{ROLE_LABELS_FR[invite.role] || invite.role}</span>
                    <span className="muted">Expire le {invite.expires_at ? new Date(invite.expires_at).toLocaleDateString('fr-FR') : '—'}</span>
                    <div className="admin-actions" style={{ marginTop: '0.5rem' }}>
                      <button
                        className="btn"
                        type="button"
                        disabled={inviteBusy === invite.id}
                        onClick={() => void acceptInvite({ invitation_id: invite.id })}
                      >
                        Accepter
                      </button>
                      <button
                        className="btn secondary"
                        type="button"
                        disabled={inviteBusy === invite.id}
                        onClick={() => void refuseInvite(invite.id)}
                      >
                        Refuser
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}

          <h3>Mes organisations</h3>
          <div className="list">
            {memberships.map((m) => {
              const isActive = m.organization_id === orgId
              const canLeave = m.role !== 'owner'
              const planFeatures = ['document_analysis', 'team_members', 'intelligence_dashboard', 'elfis_chat']
              return (
                <div key={m.membership_id} className="membership-chip">
                  <strong>
                    {m.organization_name}
                    {isActive ? ' · active' : ''}
                  </strong>
                  <span className="badge">{ROLE_LABELS_FR[m.role] || m.role}</span>
                  <span className="muted">
                    Abonnement {m.plan}
                    {m.subscription_status ? ` (${m.subscription_status})` : ''}
                    {m.joined_at
                      ? ` · depuis ${new Date(m.joined_at).toLocaleDateString('fr-FR')}`
                      : ''}
                  </span>
                  <ul className="muted" style={{ margin: '0.4rem 0 0', paddingLeft: '1.1rem' }}>
                    {planFeatures.map((feature) => {
                      const ok = planIncludesFeature(m.plan, feature)
                      return (
                        <li key={feature}>
                          {ok ? '✓' : '✗'} {FEATURE_LABELS_FR[feature] || feature}
                          {!ok ? ' (hors abonnement org.)' : ''}
                        </li>
                      )
                    })}
                  </ul>
                  <div className="admin-actions" style={{ marginTop: '0.6rem' }}>
                    <button
                      className="btn"
                      type="button"
                      disabled={isActive}
                      onClick={() => {
                        setOrgId(m.organization_id)
                        navigate('/dashboard')
                      }}
                    >
                      Accéder
                    </button>
                    {canLeave && (
                      <button
                        className="btn danger-outline"
                        type="button"
                        onClick={() => void leaveOrg(m.organization_id, m.organization_name)}
                      >
                        Quitter
                      </button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>

          {!!notifications.length && (
            <>
              <h3 style={{ marginTop: '1.25rem' }}>Notifications</h3>
              <div className="list">
                {notifications.slice(0, 6).map((note) => (
                  <div key={note.id} className="membership-chip">
                    <strong>{note.title}</strong>
                    <span className="muted">{note.body}</span>
                    {!note.is_read && (
                      <button
                        className="btn secondary"
                        type="button"
                        style={{ marginTop: '0.4rem' }}
                        onClick={() =>
                          void api.markNotificationRead(note.id, token, orgId).then(() =>
                            setNotifications((current) =>
                              current.map((item) =>
                                item.id === note.id ? { ...item, is_read: true } : item,
                              ),
                            ),
                          )
                        }
                      >
                        Marquer lu
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </>
          )}

          <Link className="btn secondary" to="/organisation" style={{ marginTop: '1rem', display: 'inline-flex' }}>
            Voir l&apos;organisation active
          </Link>
        </aside>
      </div>
    </>
  )
}

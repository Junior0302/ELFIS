import { useEffect, useState, type FormEvent } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { api, type OrgInvitation, type OrgMember } from '../api'
import { useAuth } from '../auth'
import { deleteFirestoreOrganizationMember, saveFirestoreOrganizationMember } from '../firebase'
import { ROLE_LABELS_FR } from '../planFeatures'

const ROLE_HELP: Record<string, string> = {
  admin: 'Gère l’équipe, les paramètres et l’abonnement',
  cfo: 'Lit la finance, la banque et le copilote',
  comptable: 'Gère factures, documents et fiscalité',
  employe: 'Crée des devis et consulte les documents',
  auditeur: 'Consultation seule, sans modification',
}

export default function AdminEquipePage() {
  const { token, orgId, memberships, user } = useAuth()
  const [members, setMembers] = useState<OrgMember[]>([])
  const [invitations, setInvitations] = useState<OrgInvitation[]>([])
  const [roles, setRoles] = useState<string[]>([])
  const [roleLabels, setRoleLabels] = useState<Record<string, string>>(ROLE_LABELS_FR)
  const [canManage, setCanManage] = useState(false)
  const [canInvite, setCanInvite] = useState(true)
  const [seatMessage, setSeatMessage] = useState('')
  const [seats, setSeats] = useState({ active: 0, pending_invites: 0, used: 0 })
  const [plan, setPlan] = useState('starter')
  const [loading, setLoading] = useState(true)
  const [memberForm, setMemberForm] = useState({ email: '', role: 'comptable' })
  const [saving, setSaving] = useState(false)
  const [pendingId, setPendingId] = useState<number | null>(null)
  const [lastInviteLink, setLastInviteLink] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const activeMembership = memberships.find((item) => item.organization_id === orgId)
  const allowed =
    Boolean(activeMembership?.permissions.includes('*')) ||
    Boolean(activeMembership?.permissions.includes('users.manage'))

  const load = async () => {
    if (!token || !orgId) return
    setLoading(true)
    setError('')
    try {
      const [data, invites] = await Promise.all([
        api.orgMembers(orgId, token),
        api.orgInvitations(orgId, token).catch(() => ({ invitations: [] as OrgInvitation[] })),
      ])
      setMembers(data.members)
      setRoles(data.roles)
      setCanManage(data.can_manage)
      setCanInvite(data.can_invite !== false)
      setSeatMessage(data.seat_limit_message || '')
      setSeats(data.seats || { active: 0, pending_invites: 0, used: 0 })
      setPlan(data.plan || 'starter')
      if (data.role_labels) setRoleLabels(data.role_labels)
      setInvitations(invites.invitations.filter((item) => item.status === 'pending'))
      if (data.roles.length && !data.roles.includes(memberForm.role)) {
        setMemberForm((current) => ({ ...current, role: data.roles[0] }))
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Chargement impossible')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, orgId])

  if (!allowed) {
    return <Navigate to="/organisation" replace />
  }

  const syncMember = async (member: OrgMember) => {
    if (!orgId || !member.uid) return
    await saveFirestoreOrganizationMember(String(orgId), {
      uid: member.uid,
      email: member.email,
      displayName: member.display_name,
      role: member.role,
      permissions: member.permissions,
      status: member.status,
    })
  }

  const inviteMember = async (event: FormEvent) => {
    event.preventDefault()
    if (!token || !orgId) return
    setSaving(true)
    setError('')
    setMessage('')
    setLastInviteLink('')
    try {
      const result = await api.inviteOrgMember(
        orgId,
        { email: memberForm.email.trim().toLowerCase(), role: memberForm.role },
        token,
      )
      setMemberForm((current) => ({ ...current, email: '' }))
      setMessage(result.message)
      if (result.email_warning) {
        const link = `${window.location.origin}/compte?invite=${result.invite_token}`
        setLastInviteLink(link)
        setMessage(`${result.message} ${result.email_warning}`)
      }
      await load()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Invitation impossible')
    } finally {
      setSaving(false)
    }
  }

  const updateMember = async (member: OrgMember, change: { role?: string; status?: string }) => {
    if (!token || !orgId) return
    setPendingId(member.membership_id)
    setError('')
    setMessage('')
    try {
      const result = await api.updateOrgMember(orgId, member.membership_id, change, token)
      await syncMember(result.member)
      setMembers((current) =>
        current.map((item) =>
          item.membership_id === result.member.membership_id ? result.member : item,
        ),
      )
      setMessage('Droits mis à jour.')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Mise à jour impossible')
    } finally {
      setPendingId(null)
    }
  }

  const removeMember = async (member: OrgMember) => {
    if (!token || !orgId) return
    const confirmed = window.confirm(
      `Retirer ${member.display_name || member.email} de l’organisation ?\nCette personne perdra immédiatement l’accès.`,
    )
    if (!confirmed) return
    setPendingId(member.membership_id)
    setError('')
    setMessage('')
    try {
      const result = await api.deleteOrgMember(orgId, member.membership_id, token)
      if (result.uid) {
        await deleteFirestoreOrganizationMember(String(orgId), result.uid).catch(() => undefined)
      }
      setMembers((current) => current.filter((item) => item.membership_id !== member.membership_id))
      setMessage(`${member.email} a été retiré de l’organisation.`)
      await load()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Suppression impossible')
    } finally {
      setPendingId(null)
    }
  }

  const resendInvite = async (invitation: OrgInvitation) => {
    if (!token || !orgId) return
    setPendingId(invitation.id)
    setError('')
    setMessage('')
    try {
      const result = await api.resendOrgInvitation(orgId, invitation.id, token)
      setMessage('Invitation renvoyée.')
      if (result.email_warning) {
        setLastInviteLink(`${window.location.origin}/compte?invite=${result.invite_token}`)
      }
      await load()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Renvoi impossible')
    } finally {
      setPendingId(null)
    }
  }

  const cancelInvite = async (invitation: OrgInvitation) => {
    if (!token || !orgId) return
    if (!window.confirm(`Annuler l’invitation pour ${invitation.email} ?`)) return
    setPendingId(invitation.id)
    try {
      await api.cancelOrgInvitation(orgId, invitation.id, token)
      setMessage('Invitation annulée.')
      await load()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Annulation impossible')
    } finally {
      setPendingId(null)
    }
  }

  const labelFor = (role: string) => roleLabels[role] || ROLE_LABELS_FR[role] || role

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Admin · Équipe</h2>
          <p>
            Invitez des collaborateurs : ils utilisent l’abonnement de l’organisation, sans
            souscription individuelle. Les droits restent limités par leur rôle.
          </p>
        </div>
        <Link className="btn secondary" to="/organisation">
          Retour organisation
        </Link>
      </div>

      {error && <div className="auth-alert auth-alert-error">{error}</div>}
      {message && <div className="auth-alert auth-alert-ok">{message}</div>}
      {lastInviteLink && (
        <div className="auth-alert">
          Lien d’invitation à transmettre :{' '}
          <a href={lastInviteLink}>{lastInviteLink}</a>
        </div>
      )}

      <section className="panel admin-team-panel">
        <div className="section-heading">
          <div>
            <h3>Inviter un membre</h3>
            <p className="muted">
              Plan {plan} · {seats.active} actif(s) · {seats.pending_invites} invitation(s) en
              attente
            </p>
            {seatMessage && <p className="muted">{seatMessage}</p>}
          </div>
        </div>

        {canManage ? (
          <form className="member-invite admin-invite" onSubmit={inviteMember}>
            <div className="field">
              <label htmlFor="admin_member_email">Email</label>
              <input
                id="admin_member_email"
                type="email"
                required
                placeholder="prenom@entreprise.fr"
                value={memberForm.email}
                onChange={(event) => setMemberForm({ ...memberForm, email: event.target.value })}
              />
            </div>
            <div className="field">
              <label htmlFor="admin_member_role">Rôle</label>
              <select
                id="admin_member_role"
                value={memberForm.role}
                onChange={(event) => setMemberForm({ ...memberForm, role: event.target.value })}
              >
                {roles.map((role) => (
                  <option key={role} value={role}>
                    {labelFor(role)}
                  </option>
                ))}
              </select>
              <small className="muted">{ROLE_HELP[memberForm.role] || ''}</small>
            </div>
            <button className="btn" type="submit" disabled={saving || !canInvite}>
              {saving ? 'Envoi…' : 'Envoyer l’invitation'}
            </button>
          </form>
        ) : (
          <p className="muted">Vous n’avez pas la permission users.manage.</p>
        )}
      </section>

      {!!invitations.length && (
        <section className="panel" style={{ marginTop: '1rem' }}>
          <h3>Invitations en attente</h3>
          <div className="admin-member-table-wrap">
            <table className="admin-member-table">
              <thead>
                <tr>
                  <th>Email</th>
                  <th>Rôle</th>
                  <th>Expire</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {invitations.map((invite) => (
                  <tr key={invite.id}>
                    <td>{invite.email}</td>
                    <td>
                      <span className="badge">{labelFor(invite.role)}</span>
                    </td>
                    <td className="muted">
                      {invite.expires_at
                        ? new Date(invite.expires_at).toLocaleDateString('fr-FR')
                        : '—'}
                    </td>
                    <td>
                      <div className="admin-actions">
                        <button
                          className="btn secondary"
                          type="button"
                          disabled={pendingId === invite.id}
                          onClick={() => void resendInvite(invite)}
                        >
                          Renvoyer
                        </button>
                        <button
                          className="btn danger-outline"
                          type="button"
                          disabled={pendingId === invite.id}
                          onClick={() => void cancelInvite(invite)}
                        >
                          Annuler
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <section className="panel" style={{ marginTop: '1rem' }}>
        <div className="section-heading">
          <div>
            <h3>Comptes et droits</h3>
            <p className="muted">
              {activeMembership?.organization_name || 'Organisation'} · {members.length} compte(s)
            </p>
          </div>
        </div>

        {loading ? (
          <div className="loading">Chargement de l’équipe…</div>
        ) : (
          <div className="admin-member-table-wrap">
            <table className="admin-member-table">
              <thead>
                <tr>
                  <th>Utilisateur</th>
                  <th>Rôle</th>
                  <th>Statut</th>
                  <th>Adhésion</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {members.map((member) => {
                  const isSelf = member.user_id === user?.id
                  const isOwner = member.role === 'owner'
                  const busy = pendingId === member.membership_id
                  return (
                    <tr key={member.membership_id}>
                      <td>
                        <div className="member-identity">
                          <div className="member-avatar">
                            {member.avatar ? (
                              <img src={member.avatar} alt="" />
                            ) : (
                              `${member.first_name[0] || ''}${member.last_name[0] || ''}`.toUpperCase()
                            )}
                          </div>
                          <div>
                            <strong>
                              {member.display_name || member.email}
                              {isSelf ? ' (vous)' : ''}
                            </strong>
                            <span className="muted">{member.email}</span>
                          </div>
                        </div>
                      </td>
                      <td>
                        {canManage && !isOwner && !isSelf ? (
                          <select
                            value={member.role}
                            disabled={busy}
                            aria-label={`Rôle de ${member.display_name}`}
                            onChange={(event) =>
                              void updateMember(member, { role: event.target.value })
                            }
                          >
                            {roles.map((role) => (
                              <option key={role} value={role}>
                                {labelFor(role)}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <span className="badge">{labelFor(member.role)}</span>
                        )}
                        {!isOwner && ROLE_HELP[member.role] && (
                          <small className="muted admin-role-help">{ROLE_HELP[member.role]}</small>
                        )}
                      </td>
                      <td>
                        <span className={`badge ${member.status === 'active' ? '' : 'warn'}`}>
                          {member.status === 'active' ? 'Actif' : 'Suspendu'}
                        </span>
                      </td>
                      <td className="muted">
                        {member.joined_at
                          ? new Date(member.joined_at).toLocaleDateString('fr-FR')
                          : '—'}
                      </td>
                      <td>
                        {canManage && !isOwner && !isSelf ? (
                          <div className="admin-actions">
                            <button
                              className="btn secondary"
                              type="button"
                              disabled={busy}
                              onClick={() =>
                                void updateMember(member, {
                                  status: member.status === 'active' ? 'suspended' : 'active',
                                })
                              }
                            >
                              {member.status === 'active' ? 'Suspendre' : 'Réactiver'}
                            </button>
                            <button
                              className="btn danger-outline"
                              type="button"
                              disabled={busy}
                              onClick={() => void removeMember(member)}
                            >
                              Retirer
                            </button>
                          </div>
                        ) : (
                          <span className="muted">
                            {isOwner ? 'Propriétaire protégé' : isSelf ? 'Votre compte' : '—'}
                          </span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
            {!members.length && <p className="platform-empty">Aucun membre.</p>}
          </div>
        )}
      </section>

      <section className="panel admin-roles-legend" style={{ marginTop: '1rem' }}>
        <h3>Signification des rôles</h3>
        <div className="admin-role-grid">
          {Object.entries(ROLE_HELP).map(([role, help]) => (
            <article key={role}>
              <strong>{labelFor(role)}</strong>
              <p>{help}</p>
            </article>
          ))}
        </div>
      </section>
    </>
  )
}

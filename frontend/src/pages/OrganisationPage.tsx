import { useEffect, useState, type FormEvent } from 'react'
import { api, type OrgDetail, type OrgMember } from '../api'
import { useAuth } from '../auth'
import { saveFirestoreOrganizationMember } from '../firebase'

export default function OrganisationPage() {
  const { token, orgId, memberships, user } = useAuth()
  const [detail, setDetail] = useState<OrgDetail | null>(null)
  const [members, setMembers] = useState<OrgMember[]>([])
  const [roles, setRoles] = useState<string[]>([])
  const [canManage, setCanManage] = useState(false)
  const [memberForm, setMemberForm] = useState({ email: '', role: 'comptable' })
  const [savingMember, setSavingMember] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    if (!orgId) return
    if (!token) return
    Promise.all([api.orgDetail(orgId, token), api.orgMembers(orgId, token)])
      .then(([organization, memberData]) => {
        setDetail(organization)
        setMembers(memberData.members)
        setRoles(memberData.roles)
        setCanManage(memberData.can_manage)
      })
      .catch((e) => setError(e.message || 'Erreur organisation'))
  }, [orgId, token])

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

  const addMember = async (event: FormEvent) => {
    event.preventDefault()
    if (!orgId || !token) return
    setSavingMember(true)
    setError('')
    setMessage('')
    try {
      const result = await api.addOrgMember(orgId, memberForm, token)
      await syncMember(result.member)
      setMembers((current) => [...current, result.member])
      setMemberForm((current) => ({ ...current, email: '' }))
      setMessage('Utilisateur ajouté et droits synchronisés avec Firestore.')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Ajout impossible')
    } finally {
      setSavingMember(false)
    }
  }

  const updateMember = async (
    member: OrgMember,
    change: { role?: string; status?: string },
  ) => {
    if (!orgId || !token) return
    setError('')
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
    }
  }

  if (!user) {
    return (
      <div className="panel">
        <h2>Organisation</h2>
        <p className="muted">
          Retrouvez ici la structure de votre entreprise : filiales, équipes, abonnement et agents
          IA.
        </p>
      </div>
    )
  }

  if (error && !detail) return <div className="panel form-error">{error}</div>
  if (!detail) return <div className="loading">Chargement organisation…</div>

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Organisation</h2>
          <p>
            {detail.organization.legal_name || detail.organization.name} ·{' '}
            {detail.organization.country}. Structure multi-entreprises, équipes et rôles.
          </p>
        </div>
      </div>

      <div className="panel" style={{ marginBottom: '1rem' }}>
        <h3 style={{ marginTop: 0 }}>{detail.organization.name}</h3>
        <p className="muted" style={{ margin: 0 }}>
          Vue consolidée de l’entreprise active sélectionnée dans la barre latérale.
        </p>
      </div>

      {error && <div className="auth-alert auth-alert-error">{error}</div>}
      {message && <div className="auth-alert auth-alert-ok">{message}</div>}

      <div className="stats">
        <div className="stat">
          <span>SIREN</span>
          <strong style={{ fontSize: '1.1rem' }}>{detail.organization.siren || '—'}</strong>
        </div>
        <div className="stat">
          <span>Utilisateurs</span>
          <strong>{members.length}</strong>
        </div>
        <div className="stat">
          <span>Équipes</span>
          <strong>{detail.teams.length}</strong>
        </div>
        <div className="stat">
          <span>Agents IA</span>
          <strong>{detail.ai_agents.length}</strong>
        </div>
      </div>

      <div className="result-grid" style={{ minHeight: 'auto' }}>
        <section className="panel">
          <h3>Filiales / Companies</h3>
          {detail.companies.length === 0 ? (
            <p className="muted">Aucune filiale rattachée à cette org.</p>
          ) : (
            <div className="list">
              {detail.companies.map((c) => (
                <div key={c.id} className="list-item" style={{ gridTemplateColumns: '1fr 0.5fr 0.5fr' }}>
                  <strong>{c.name}</strong>
                  <span>{c.country}</span>
                  <span className="muted">{c.parent_company_id ? `fils de #${c.parent_company_id}` : 'siège'}</span>
                </div>
              ))}
            </div>
          )}
        </section>
        <section className="panel">
          <h3>Équipes & Agents IA</h3>
          <p>
            <strong>Teams :</strong> {detail.teams.map((t) => t.name).join(', ') || '—'}
          </p>
          <div className="list" style={{ marginTop: '0.75rem' }}>
            {detail.ai_agents.map((a) => (
              <div key={a.id} className="list-item" style={{ gridTemplateColumns: '1fr 0.6fr 0.5fr' }}>
                <strong>{a.name}</strong>
                <span>{a.type}</span>
                <span className="badge">{a.status}</span>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section className="panel" style={{ marginTop: '1rem' }}>
        <div className="section-heading">
          <div>
            <h3>Utilisateurs et droits</h3>
            <p className="muted">
              Les accès sont contrôlés côté API et répliqués dans Cloud Firestore.
            </p>
          </div>
          <span className="badge">{members.length} utilisateur(s)</span>
        </div>

        {canManage && (
          <form className="member-invite" onSubmit={addMember}>
            <div className="field">
              <label htmlFor="member_email">Email du compte existant</label>
              <input
                id="member_email"
                type="email"
                required
                placeholder="prenom@entreprise.fr"
                value={memberForm.email}
                onChange={(event) => setMemberForm({ ...memberForm, email: event.target.value })}
              />
            </div>
            <div className="field">
              <label htmlFor="member_role">Rôle</label>
              <select
                id="member_role"
                value={memberForm.role}
                onChange={(event) => setMemberForm({ ...memberForm, role: event.target.value })}
              >
                {roles.map((role) => (
                  <option key={role} value={role}>
                    {role}
                  </option>
                ))}
              </select>
            </div>
            <button className="btn" type="submit" disabled={savingMember}>
              {savingMember ? 'Ajout…' : 'Ajouter'}
            </button>
          </form>
        )}

        <div className="member-list">
          {members.map((member) => (
            <div className="member-row" key={member.membership_id}>
              <div className="member-identity">
                <div className="member-avatar">
                  {member.avatar ? (
                    <img src={member.avatar} alt="" />
                  ) : (
                    `${member.first_name[0] || ''}${member.last_name[0] || ''}`.toUpperCase()
                  )}
                </div>
                <div>
                  <strong>{member.display_name || member.email}</strong>
                  <span className="muted">{member.email}</span>
                </div>
              </div>
              {canManage && member.role !== 'owner' ? (
                <select
                  value={member.role}
                  aria-label={`Rôle de ${member.display_name}`}
                  onChange={(event) => void updateMember(member, { role: event.target.value })}
                >
                  {roles.map((role) => (
                    <option key={role} value={role}>
                      {role}
                    </option>
                  ))}
                </select>
              ) : (
                <span className="badge">{member.role}</span>
              )}
              {canManage && member.role !== 'owner' ? (
                <button
                  className="btn secondary"
                  type="button"
                  onClick={() =>
                    void updateMember(member, {
                      status: member.status === 'active' ? 'suspended' : 'active',
                    })
                  }
                >
                  {member.status === 'active' ? 'Suspendre' : 'Réactiver'}
                </button>
              ) : (
                <span className={`badge ${member.status === 'active' ? '' : 'warn'}`}>
                  {member.status}
                </span>
              )}
            </div>
          ))}
        </div>
      </section>

      <section className="panel" style={{ marginTop: '1rem' }}>
        <h3>Mes appartenances</h3>
        <div className="list">
          {memberships.map((m) => (
            <div key={m.membership_id} className="membership-chip">
              <strong>{m.organization_name}</strong>
              <span className="badge">{m.role}</span>
              <span className="muted">{m.country}</span>
            </div>
          ))}
        </div>
      </section>
    </>
  )
}

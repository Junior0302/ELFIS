import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, formatEuro, type OrgDetail, type OrgMember, type SubscriptionInfo } from '../api'
import { useAuth } from '../auth'
import {
  canOpenSubscriptionPortal,
  formatDate,
  subscriptionLabels,
  subscriptionTone,
} from '../subscription'

export default function OrganisationPage() {
  const { token, orgId, memberships, user } = useAuth()
  const [detail, setDetail] = useState<OrgDetail | null>(null)
  const [members, setMembers] = useState<OrgMember[]>([])
  const [canManage, setCanManage] = useState(false)
  const [error, setError] = useState('')
  const [subscription, setSubscription] = useState<SubscriptionInfo | null>(null)
  const [subscriptionError, setSubscriptionError] = useState('')
  const [openingPortal, setOpeningPortal] = useState(false)
  const activeMembership = memberships.find((item) => item.organization_id === orgId)
  const canManageSubscription = Boolean(
    activeMembership?.permissions.includes('*') ||
      activeMembership?.permissions.includes('subscription.manage'),
  )
  const canOpenPortal = Boolean(
    subscription && canOpenSubscriptionPortal(subscription.status),
  )

  useEffect(() => {
    if (!orgId) return
    if (!token) return
    setSubscription(null)
    setSubscriptionError('')
    Promise.all([api.orgDetail(orgId, token), api.orgMembers(orgId, token)])
      .then(([organization, memberData]) => {
        setDetail(organization)
        setMembers(memberData.members)
        setCanManage(memberData.can_manage)
      })
      .catch((e) => setError(e.message || 'Erreur organisation'))
    api
      .currentSubscription(token, orgId)
      .then(setSubscription)
      .catch((reason) => {
        setSubscriptionError(reason instanceof Error ? reason.message : 'Abonnement indisponible')
      })
  }, [orgId, token])

  const openPortal = async () => {
    if (!token || !orgId) return
    setOpeningPortal(true)
    setSubscriptionError('')
    try {
      const { url } = await api.createSubscriptionPortal(token, orgId)
      const target = new URL(url, window.location.origin)
      if (!['http:', 'https:'].includes(target.protocol)) throw new Error('URL Stripe invalide')
      window.location.assign(target.toString())
    } catch (reason) {
      setSubscriptionError(reason instanceof Error ? reason.message : 'Portail Stripe indisponible')
      setOpeningPortal(false)
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

      <section className="panel organisation-subscription">
        <div>
          <span className="home-eyebrow">Abonnement</span>
          <h3>ComptaPilot {subscription?.plan || detail.subscription?.plan || 'Pro'}</h3>
          {subscription ? (
            <p className="muted">
              {formatEuro(subscription.price_eur || 19)} / mois · échéance{' '}
              {formatDate(
                subscription.status === 'trialing'
                  ? subscription.trial_end
                  : subscription.current_period_end,
              )}
            </p>
          ) : (
            <p className="muted">
              {detail.subscription
                ? `${formatEuro(detail.subscription.price)} / mois`
                : 'Statut détaillé indisponible'}
            </p>
          )}
          {subscriptionError && <small className="form-error">{subscriptionError}</small>}
        </div>
        <div className="organisation-subscription-actions">
          {subscription && (
            <span className={`subscription-badge ${subscriptionTone(subscription.status)}`}>
              {subscriptionLabels[subscription.status]}
            </span>
          )}
          {canManageSubscription && canOpenPortal && (
            <button
              className="btn secondary"
              type="button"
              disabled={openingPortal}
              onClick={() => void openPortal()}
            >
              {openingPortal ? 'Ouverture…' : 'Ouvrir le portail Stripe'}
            </button>
          )}
          {canManageSubscription && !canOpenPortal && (
            <Link className="btn secondary" to="/abonnement">
              Choisir l’abonnement
            </Link>
          )}
        </div>
      </section>

      <div className="result-grid" style={{ minHeight: 'auto' }}>
        <section className="panel">
          <h3>Filiales / Companies</h3>
          {detail.companies.length === 0 ? (
            <p className="muted">Aucune filiale rattachée à cette org.</p>
          ) : (
            <div className="list">
              {detail.companies.map((c) => (
                <div
                  key={c.id}
                  className="list-item"
                  style={{ gridTemplateColumns: '1fr 0.5fr 0.5fr' }}
                >
                  <strong>{c.name}</strong>
                  <span>{c.country}</span>
                  <span className="muted">
                    {c.parent_company_id ? `fils de #${c.parent_company_id}` : 'siège'}
                  </span>
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
              <div
                key={a.id}
                className="list-item"
                style={{ gridTemplateColumns: '1fr 0.6fr 0.5fr' }}
              >
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
              {members.length} compte(s) dans l’organisation. La gestion complète (ajout, rôles,
              suppression) se fait dans l’espace admin.
            </p>
          </div>
          {canManage ? (
            <Link className="btn" to="/admin/equipe">
              Gérer l’équipe
            </Link>
          ) : (
            <span className="badge">{members.length} utilisateur(s)</span>
          )}
        </div>

        <div className="member-list">
          {members.map((member) => (
            <div className="member-row member-row-readonly" key={member.membership_id}>
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
              <span className="badge">{member.role}</span>
              <span className={`badge ${member.status === 'active' ? '' : 'warn'}`}>
                {member.status === 'active' ? 'Actif' : 'Suspendu'}
              </span>
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

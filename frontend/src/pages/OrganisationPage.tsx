import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api, formatEuro, type OrgDetail, type SubscriptionInfo } from '../api'
import { useAuth } from '../auth'
import {
  canOpenSubscriptionPortal,
  formatDate,
  remainingTime,
  subscriptionDeadline,
  subscriptionLabels,
  subscriptionTone,
} from '../subscription'

const emptyForm = {
  name: '',
  legal_name: '',
  siren: '',
  vat_number: '',
  address: '',
  postal_code: '',
  city: '',
  phone: '',
  email: '',
  website: '',
  iban: '',
  bic: '',
  share_capital: '',
  legal_form: '',
  legal_mentions: '',
  logo: '',
  industry: '',
  country: 'FR',
  currency: 'EUR',
}

export default function OrganisationPage() {
  const { token, orgId, memberships, user } = useAuth()
  const [detail, setDetail] = useState<OrgDetail | null>(null)
  const [form, setForm] = useState(emptyForm)
  const [canEdit, setCanEdit] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [saving, setSaving] = useState(false)
  const [subscription, setSubscription] = useState<SubscriptionInfo | null>(null)
  const [subscriptionError, setSubscriptionError] = useState('')
  const [openingPortal, setOpeningPortal] = useState(false)
  const [now, setNow] = useState(Date.now())
  const activeMembership = memberships.find((item) => item.organization_id === orgId)
  const canManageSubscription = Boolean(
    activeMembership?.permissions.includes('*') ||
      activeMembership?.permissions.includes('subscription.manage'),
  )
  const canOpenPortal = Boolean(subscription && canOpenSubscriptionPortal(subscription.status))
  const canManageTeam = Boolean(
    activeMembership?.permissions.includes('*') ||
      activeMembership?.permissions.includes('users.manage'),
  )

  useEffect(() => {
    if (!orgId || !token) return
    setSubscription(null)
    setSubscriptionError('')
    setError('')
    api
      .orgDetail(orgId, token)
      .then((organization) => {
        setDetail(organization)
        setCanEdit(Boolean(organization.can_edit))
        const org = organization.organization
        setForm({
          name: org.name || '',
          legal_name: org.legal_name || '',
          siren: org.siren || '',
          vat_number: org.vat_number || '',
          address: org.address || '',
          postal_code: org.postal_code || '',
          city: org.city || '',
          phone: org.phone || '',
          email: org.email || '',
          website: org.website || '',
          iban: org.iban || '',
          bic: org.bic || '',
          share_capital: org.share_capital || '',
          legal_form: org.legal_form || '',
          legal_mentions: org.legal_mentions || '',
          logo: org.logo || '',
          industry: org.industry || '',
          country: org.country || 'FR',
          currency: org.currency || 'EUR',
        })
      })
      .catch((e) => setError(e.message || 'Erreur organisation'))
    api
      .currentSubscription(token, orgId)
      .then(setSubscription)
      .catch((reason) => {
        setSubscriptionError(reason instanceof Error ? reason.message : 'Abonnement indisponible')
      })
  }, [orgId, token])

  useEffect(() => {
    const tickMs = subscription?.status === 'trialing' ? 1000 : 60_000
    const timer = window.setInterval(() => setNow(Date.now()), tickMs)
    return () => window.clearInterval(timer)
  }, [subscription?.status])

  const openPortal = async () => {
    if (!token || !orgId) return
    setOpeningPortal(true)
    setSubscriptionError('')
    try {
      const { url } = await api.createSubscriptionPortal(token, orgId)
      const target = new URL(url, window.location.origin)
      if (!['http:', 'https:'].includes(target.protocol)) throw new Error('Lien de facturation invalide')
      window.location.assign(target.toString())
    } catch (reason) {
      setSubscriptionError(reason instanceof Error ? reason.message : 'Espace facturation indisponible')
      setOpeningPortal(false)
    }
  }

  const onSave = async (e: FormEvent) => {
    e.preventDefault()
    if (!token || !orgId || !canEdit) return
    setSaving(true)
    setMessage('')
    setError('')
    try {
      const { organization } = await api.updateOrganization(orgId, form, token)
      setDetail((current) => (current ? { ...current, organization } : current))
      setMessage('Informations de l’entreprise enregistrées.')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Enregistrement impossible')
    } finally {
      setSaving(false)
    }
  }

  if (!user) {
    return (
      <div className="panel">
        <h2>Organisation</h2>
        <p className="muted">
          Retrouvez ici les informations de votre entreprise : identité légale, coordonnées et
          paramètres.
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
          <h2>Entreprise</h2>
          <p>
            Identité et coordonnées de l’entreprise. TVA, e-mails de documents et préférences sont
            dans Paramètres.
          </p>
        </div>
        <div className="actions" style={{ margin: 0, flexWrap: 'wrap' }}>
          <Link className="btn secondary" to="/settings">
            TVA & e-mails
          </Link>
          {canManageTeam && (
            <Link className="btn secondary" to="/admin/equipe">
              Équipe
            </Link>
          )}
        </div>
      </div>

      {error && <div className="auth-alert auth-alert-error">{error}</div>}
      {message && <p className="muted">{message}</p>}

      <div className="stats">
        <div className="stat">
          <span>SIREN / SIRET</span>
          <strong style={{ fontSize: '1.1rem' }}>{detail.organization.siren || '—'}</strong>
        </div>
        <div className="stat">
          <span>TVA</span>
          <strong style={{ fontSize: '1.1rem' }}>{detail.organization.vat_number || '—'}</strong>
        </div>
        <div className="stat">
          <span>Pays</span>
          <strong>{detail.organization.country}</strong>
        </div>
        <div className="stat">
          <span>Devise</span>
          <strong>{detail.organization.currency}</strong>
        </div>
      </div>

      <section className="panel organisation-subscription">
        <div>
          <span className="home-eyebrow">Abonnement</span>
          <h3>ComptaPilot {subscription?.plan || detail.subscription?.plan || 'Pro'}</h3>
          {subscription ? (
            <p className="muted">
              {formatEuro(subscription.price_eur || 19)} / mois
              {subscription.status === 'trialing' ? (
                <>
                  {' '}
                  · essai ·{' '}
                  <strong>{remainingTime(subscriptionDeadline(subscription), now) ?? '—'}</strong>{' '}
                  restant
                </>
              ) : (
                <> · échéance {formatDate(subscriptionDeadline(subscription))}</>
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
              {openingPortal ? 'Ouverture…' : 'Gérer la carte et les factures'}
            </button>
          )}
          {canManageSubscription && !canOpenPortal && (
            <Link className="btn secondary" to="/abonnement">
              Choisir l’abonnement
            </Link>
          )}
        </div>
      </section>

      <form className="panel" onSubmit={onSave} style={{ marginTop: '1rem' }}>
        <div className="section-heading">
          <div>
            <h3>Entreprise</h3>
            <p className="muted">Identité légale, adresse, TVA et logo affichés sur vos documents.</p>
          </div>
        </div>
        <div className="form-grid">
          <div className="field">
            <label>Nom commercial</label>
            <input
              value={form.name}
              disabled={!canEdit}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              required
            />
          </div>
          <div className="field">
            <label>Raison sociale</label>
            <input
              value={form.legal_name}
              disabled={!canEdit}
              onChange={(e) => setForm({ ...form, legal_name: e.target.value })}
            />
          </div>
          <div className="field">
            <label>SIREN / SIRET</label>
            <input
              value={form.siren}
              disabled={!canEdit}
              onChange={(e) => setForm({ ...form, siren: e.target.value })}
            />
          </div>
          <div className="field">
            <label>N° TVA</label>
            <input
              value={form.vat_number}
              disabled={!canEdit}
              onChange={(e) => setForm({ ...form, vat_number: e.target.value })}
            />
          </div>
          <div className="field">
            <label>Secteur</label>
            <input
              value={form.industry}
              disabled={!canEdit}
              onChange={(e) => setForm({ ...form, industry: e.target.value })}
            />
          </div>
          <div className="field">
            <label>Pays</label>
            <input
              value={form.country}
              disabled={!canEdit}
              onChange={(e) => setForm({ ...form, country: e.target.value })}
            />
          </div>
          <div className="field">
            <label>Devise</label>
            <input
              value={form.currency}
              disabled={!canEdit}
              onChange={(e) => setForm({ ...form, currency: e.target.value })}
            />
          </div>
          <div className="field">
            <label>Logo</label>
            <div className="brand-logo-row compact">
              <div className="brand-logo-preview small" aria-hidden>
                {form.logo ? <img src={form.logo} alt="" /> : <span>—</span>}
              </div>
              {canEdit && (
                <div className="brand-logo-actions">
                  <label className="btn secondary" htmlFor="org_logo">
                    Importer
                  </label>
                  <input
                    id="org_logo"
                    type="file"
                    accept="image/png,image/jpeg,image/jpg,image/svg+xml,.png,.jpg,.jpeg,.svg"
                    onChange={(e) => {
                      const file = e.target.files?.[0]
                      e.currentTarget.value = ''
                      if (!file || !token || !orgId) return
                      void api
                        .uploadOrganizationLogo(orgId, file, token)
                        .then((res) => {
                          setForm((f) => ({ ...f, logo: res.organization.logo || '' }))
                          setMessage('Logo mis à jour.')
                        })
                        .catch((err) =>
                          setError(err instanceof Error ? err.message : 'Upload impossible'),
                        )
                    }}
                  />
                  {form.logo ? (
                    <button
                      type="button"
                      className="btn secondary"
                      onClick={() => {
                        if (!token || !orgId) return
                        void api
                          .deleteOrganizationLogo(orgId, token)
                          .then((res) => {
                            setForm((f) => ({ ...f, logo: res.organization.logo || '' }))
                            setMessage('Logo supprimé.')
                          })
                          .catch((err) =>
                            setError(err instanceof Error ? err.message : 'Suppression impossible'),
                          )
                      }}
                    >
                      Supprimer
                    </button>
                  ) : null}
                </div>
              )}
            </div>
          </div>
          <div className="field full">
            <label>Adresse</label>
            <textarea
              rows={2}
              value={form.address}
              disabled={!canEdit}
              onChange={(e) => setForm({ ...form, address: e.target.value })}
            />
          </div>
          <div className="field">
            <label>Code postal</label>
            <input
              value={form.postal_code}
              disabled={!canEdit}
              onChange={(e) => setForm({ ...form, postal_code: e.target.value })}
            />
          </div>
          <div className="field">
            <label>Ville</label>
            <input
              value={form.city}
              disabled={!canEdit}
              onChange={(e) => setForm({ ...form, city: e.target.value })}
            />
          </div>
          <div className="field">
            <label>Téléphone</label>
            <input
              value={form.phone}
              disabled={!canEdit}
              onChange={(e) => setForm({ ...form, phone: e.target.value })}
            />
          </div>
          <div className="field">
            <label>E-mail</label>
            <input
              type="email"
              value={form.email}
              disabled={!canEdit}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />
          </div>
          <div className="field">
            <label>Site internet</label>
            <input
              value={form.website}
              disabled={!canEdit}
              onChange={(e) => setForm({ ...form, website: e.target.value })}
            />
          </div>
          <div className="field">
            <label>IBAN</label>
            <input
              value={form.iban}
              disabled={!canEdit}
              onChange={(e) => setForm({ ...form, iban: e.target.value })}
            />
          </div>
          <div className="field">
            <label>BIC</label>
            <input
              value={form.bic}
              disabled={!canEdit}
              onChange={(e) => setForm({ ...form, bic: e.target.value })}
            />
          </div>
          <div className="field">
            <label>Forme juridique</label>
            <input
              value={form.legal_form}
              disabled={!canEdit}
              onChange={(e) => setForm({ ...form, legal_form: e.target.value })}
            />
          </div>
          <div className="field">
            <label>Capital social</label>
            <input
              value={form.share_capital}
              disabled={!canEdit}
              onChange={(e) => setForm({ ...form, share_capital: e.target.value })}
            />
          </div>
          <div className="field full">
            <label>Mentions légales</label>
            <textarea
              rows={2}
              value={form.legal_mentions}
              disabled={!canEdit}
              onChange={(e) => setForm({ ...form, legal_mentions: e.target.value })}
            />
          </div>
        </div>
        {canEdit ? (
          <div className="actions">
            <button className="btn" type="submit" disabled={saving}>
              {saving ? 'Enregistrement…' : 'Enregistrer'}
            </button>
          </div>
        ) : (
          <p className="muted">Lecture seule — demandez un accès paramètres à un administrateur.</p>
        )}
      </form>

      <div className="result-grid" style={{ minHeight: 'auto', marginTop: '1rem' }}>
        <section className="panel">
          <h3>Filiales</h3>
          {detail.companies.length === 0 ? (
            <p className="muted">Aucune filiale rattachée.</p>
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
          <h3>Paramètres</h3>
          <p className="muted">
            Équipes : {detail.teams.map((t) => t.name).join(', ') || '—'}. Agents IA :{' '}
            {detail.ai_agents.length}.
          </p>
          <p style={{ marginTop: '0.75rem' }}>
            Les comptes utilisateurs et les permissions se gèrent uniquement dans{' '}
            <Link to="/admin/equipe">Admin → Équipe</Link>.
          </p>
        </section>
      </div>
    </>
  )
}

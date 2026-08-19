import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api, type CompanySettings, type OrgDetail, type OrgEmailSettings } from '../api'
import { useAuth } from '../auth'

type BrandForm = {
  name: string
  legal_name: string
  siren: string
  vat_number: string
  address: string
  postal_code: string
  city: string
  country: string
  phone: string
  email: string
  website: string
  iban: string
  bic: string
  share_capital: string
  legal_form: string
  legal_mentions: string
  logo: string
}

const emptyBrand: BrandForm = {
  name: '',
  legal_name: '',
  siren: '',
  vat_number: '',
  address: '',
  postal_code: '',
  city: '',
  country: 'FR',
  phone: '',
  email: '',
  website: '',
  iban: '',
  bic: '',
  share_capital: '',
  legal_form: '',
  legal_mentions: '',
  logo: '',
}

const emptySettings: Omit<CompanySettings, 'id'> = {
  company_name: '',
  siret: '',
  vat_number: '',
  default_vat_rate: 20,
  expense_account: '606',
  vat_account: '44566',
  supplier_account: '401',
  accountant_firm: '',
  accountant_email: '',
  confidence_threshold: 0.85,
}

function fromOrg(org: OrgDetail['organization']): BrandForm {
  return {
    name: org.name || '',
    legal_name: org.legal_name || '',
    siren: org.siren || '',
    vat_number: org.vat_number || '',
    address: org.address || '',
    postal_code: org.postal_code || '',
    city: org.city || '',
    country: org.country || 'FR',
    phone: org.phone || '',
    email: org.email || '',
    website: org.website || '',
    iban: org.iban || '',
    bic: org.bic || '',
    share_capital: org.share_capital || '',
    legal_form: org.legal_form || '',
    legal_mentions: org.legal_mentions || '',
    logo: org.logo || '',
  }
}

export default function SettingsPage() {
  const { token, orgId } = useAuth()
  const [brand, setBrand] = useState<BrandForm>(emptyBrand)
  const [form, setForm] = useState(emptySettings)
  const [canEdit, setCanEdit] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [emailSettings, setEmailSettings] = useState<OrgEmailSettings | null>(null)
  const [emailSaving, setEmailSaving] = useState(false)
  const [emailMessage, setEmailMessage] = useState('')
  const [emailError, setEmailError] = useState('')

  useEffect(() => {
    if (!token || !orgId) return
    setLoading(true)
    setError('')
    Promise.all([
      api.getSettings(token, orgId),
      api.orgDetail(orgId, token),
      api.getOrgEmailSettings(token, orgId).catch(() => null),
    ])
      .then(([settings, detail, email]) => {
        setCanEdit(Boolean(detail.can_edit))
        setBrand(fromOrg(detail.organization))
        setForm({
          company_name: settings.company_name || detail.organization.legal_name || detail.organization.name,
          siret: settings.siret || detail.organization.siren || '',
          vat_number: settings.vat_number || detail.organization.vat_number || '',
          default_vat_rate: settings.default_vat_rate,
          expense_account: settings.expense_account,
          vat_account: settings.vat_account,
          supplier_account: settings.supplier_account,
          accountant_firm: settings.accountant_firm,
          accountant_email: settings.accountant_email,
          confidence_threshold: settings.confidence_threshold,
        })
        if (email) {
          setEmailSettings({
            ...email,
            reply_to_email:
              email.reply_to_email || detail.organization.email || '',
            sender_name:
              email.sender_name ||
              detail.organization.legal_name ||
              detail.organization.name ||
              '',
          })
        }
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Chargement impossible'))
      .finally(() => setLoading(false))
  }, [token, orgId])

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!token || !orgId) return
    setMessage('')
    setError('')
    setSaving(true)
    try {
      const legal = brand.legal_name.trim() || brand.name.trim()
      // Identité org gérée via /organisation — ici on synchronise seulement les champs settings métier.
      await api.saveSettings(
        {
          ...form,
          company_name: legal || form.company_name,
          siret: brand.siren || form.siret,
          vat_number: brand.vat_number || form.vat_number,
        },
        token,
        orgId,
      )
      setMessage('Préférences comptables enregistrées.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur')
    } finally {
      setSaving(false)
    }
  }

  const saveEmailSettings = async () => {
    if (!token || !orgId || !canEdit || !emailSettings) return
    setEmailSaving(true)
    setEmailMessage('')
    setEmailError('')
    try {
      const saved = await api.updateOrgEmailSettings(
        {
          sender_mode: emailSettings.sender_mode,
          sender_name: emailSettings.sender_name,
          reply_to_email: emailSettings.reply_to_email,
          reply_to_name: emailSettings.reply_to_name,
          cc_email: emailSettings.cc_email,
          bcc_email: emailSettings.bcc_email,
          invoice_default_subject: emailSettings.invoice_default_subject,
          invoice_default_message: emailSettings.invoice_default_message,
          quote_default_subject: emailSettings.quote_default_subject,
          quote_default_message: emailSettings.quote_default_message,
          email_signature: emailSettings.email_signature,
          send_copy_to_organization: emailSettings.send_copy_to_organization,
          custom_sender_email: emailSettings.custom_sender_email,
          custom_domain: emailSettings.custom_domain,
        },
        token,
        orgId,
      )
      setEmailSettings(saved)
      setEmailMessage('Paramètres d’envoi enregistrés.')
    } catch (err) {
      setEmailError(err instanceof Error ? err.message : 'Enregistrement impossible')
    } finally {
      setEmailSaving(false)
    }
  }

  if (loading) return <div className="loading">Chargement des paramètres…</div>

  const previewName = brand.legal_name || brand.name || 'Raison sociale'
  const previewCity = [brand.postal_code, brand.city].filter(Boolean).join(' ')

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Préférences ComptaPilot</h2>
          <p>
            Réglages comptables et OCR. L’identité légale de l’entreprise se gère dans les paramètres
            ELFIS (Organisation).
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <Link className="btn secondary" to="/platform/settings">
            Paramètres ELFIS
          </Link>
          <Link className="btn secondary" to="/platform/organization">
            Organisation
          </Link>
        </div>
      </div>

      {error && <div className="auth-alert auth-alert-error">{error}</div>}

      <section className="panel" aria-labelledby="settings-org-summary">
        <h3 id="settings-org-summary">Identité entreprise (lecture)</h3>
        <p className="muted">
          Données partagées utilisées sur les PDF — gestion officielle dans{' '}
          <Link to="/platform/organization">Organisation</Link> (ELFIS Core).
        </p>
        <div className="brand-logo-row" style={{ marginBottom: '1rem' }}>
          <div className="brand-logo-preview" aria-hidden>
            {brand.logo ? <img src={brand.logo} alt="" /> : <span>Sans logo</span>}
          </div>
          <div>
            <strong>{previewName}</strong>
            <p className="muted" style={{ margin: '0.25rem 0 0' }}>
              {[brand.siren && `SIRET ${brand.siren}`, brand.vat_number && `TVA ${brand.vat_number}`]
                .filter(Boolean)
                .join(' · ') || 'Complétez l’organisation pour les mentions légales.'}
            </p>
          </div>
        </div>
        <section className="brand-preview-card" aria-label="Aperçu document">
          <h4>Aperçu</h4>
          <div className="brand-preview-sheet">
            <div className="brand-preview-head">
              <div className="brand-preview-logo">
                {brand.logo ? <img src={brand.logo} alt="" /> : <strong>{previewName}</strong>}
              </div>
              <div className="brand-preview-meta">
                <strong>{previewName}</strong>
                {brand.address ? <span>{brand.address}</span> : null}
                {previewCity ? <span>{previewCity}</span> : null}
                {brand.phone ? <span>Tél. {brand.phone}</span> : null}
                {brand.email ? <span>{brand.email}</span> : null}
                {brand.website ? <span>{brand.website}</span> : null}
                {brand.siren ? <span>SIRET {brand.siren}</span> : null}
                {brand.vat_number ? <span>TVA {brand.vat_number}</span> : null}
              </div>
            </div>
            <p className="muted">Couleurs PDF préparées pour une personnalisation ultérieure.</p>
            <div className="brand-preview-swatches" aria-hidden>
              <span className="brand-preview-swatch" style={{ background: 'var(--pilot-primary)' }} title="Principale" />
              <span className="brand-preview-swatch" style={{ background: 'var(--pilot-secondary)' }} title="Secondaire" />
            </div>
          </div>
        </section>
      </section>

      <form className="panel" onSubmit={onSubmit}>
        <h3>Modèles d’e-mail</h3>
        <p className="muted">
          Les devis et factures s’envoient via <strong>SMTP / connexion plateforme</strong> lorsque
          c’est configuré ; sinon via votre messagerie (mailto + PDF à joindre). Préparez ici les
          objets et messages par défaut.
        </p>

        {emailSettings ? (
          <>
            <div className="form-grid">
              <div className="field">
                <label>Nom affiché dans les modèles</label>
                <input
                  value={emailSettings.sender_name}
                  disabled={!canEdit}
                  onChange={(e) =>
                    setEmailSettings({ ...emailSettings, sender_name: e.target.value })
                  }
                />
              </div>
              <div className="field">
                <label>E-mail entreprise (rappel)</label>
                <input
                  type="email"
                  value={emailSettings.reply_to_email}
                  disabled={!canEdit}
                  onChange={(e) =>
                    setEmailSettings({ ...emailSettings, reply_to_email: e.target.value })
                  }
                  placeholder={brand.email || 'contact@entreprise.fr'}
                />
              </div>
              <div className="field">
                <label>Copie (CC) par défaut</label>
                <input
                  type="email"
                  value={emailSettings.cc_email}
                  disabled={!canEdit}
                  onChange={(e) => setEmailSettings({ ...emailSettings, cc_email: e.target.value })}
                />
              </div>
              <div className="field">
                <label>Copie cachée (BCC) par défaut</label>
                <input
                  type="email"
                  value={emailSettings.bcc_email}
                  disabled={!canEdit}
                  onChange={(e) => setEmailSettings({ ...emailSettings, bcc_email: e.target.value })}
                />
              </div>
              <div className="field full">
                <label>Objet par défaut — factures</label>
                <input
                  value={emailSettings.invoice_default_subject}
                  disabled={!canEdit}
                  placeholder="Facture {{invoice_number}} — {{organization_name}}"
                  onChange={(e) =>
                    setEmailSettings({
                      ...emailSettings,
                      invoice_default_subject: e.target.value,
                    })
                  }
                />
              </div>
              <div className="field full">
                <label>Message par défaut — factures</label>
                <textarea
                  rows={5}
                  value={emailSettings.invoice_default_message}
                  disabled={!canEdit}
                  onChange={(e) =>
                    setEmailSettings({
                      ...emailSettings,
                      invoice_default_message: e.target.value,
                    })
                  }
                />
              </div>
              <div className="field full">
                <label>Objet par défaut — devis</label>
                <input
                  value={emailSettings.quote_default_subject}
                  disabled={!canEdit}
                  placeholder="Devis {{quote_number}} — {{organization_name}}"
                  onChange={(e) =>
                    setEmailSettings({
                      ...emailSettings,
                      quote_default_subject: e.target.value,
                    })
                  }
                />
              </div>
              <div className="field full">
                <label>Message par défaut — devis</label>
                <textarea
                  rows={5}
                  value={emailSettings.quote_default_message}
                  disabled={!canEdit}
                  onChange={(e) =>
                    setEmailSettings({
                      ...emailSettings,
                      quote_default_message: e.target.value,
                    })
                  }
                />
              </div>
              <div className="field full">
                <label>Signature d’e-mail</label>
                <textarea
                  rows={3}
                  value={emailSettings.email_signature}
                  disabled={!canEdit}
                  onChange={(e) =>
                    setEmailSettings({ ...emailSettings, email_signature: e.target.value })
                  }
                />
              </div>
            </div>
            <div className="actions" style={{ flexWrap: 'wrap' }}>
              {canEdit ? (
                <button
                  className="btn"
                  type="button"
                  disabled={emailSaving}
                  onClick={() => void saveEmailSettings()}
                >
                  {emailSaving ? 'Enregistrement…' : 'Enregistrer les modèles'}
                </button>
              ) : (
                <p className="muted">Lecture seule — demandez un accès paramètres.</p>
              )}
            </div>
            {emailError && <p className="form-error">{emailError}</p>}
            {emailMessage && <p className="muted">{emailMessage}</p>}
          </>
        ) : (
          <p className="muted">Impossible de charger les paramètres d’envoi.</p>
        )}

        <h3 style={{ marginTop: '1.5rem' }}>TVA & OCR</h3>
        <div className="form-grid">
          <div className="field">
            <label>Taux par défaut (%)</label>
            <input
              type="number"
              step="0.1"
              value={form.default_vat_rate}
              disabled={!canEdit}
              onChange={(e) => setForm({ ...form, default_vat_rate: Number(e.target.value) })}
            />
          </div>
          <div className="field">
            <label>Seuil de confiance</label>
            <input
              type="number"
              step="0.01"
              min="0"
              max="1"
              value={form.confidence_threshold}
              disabled={!canEdit}
              onChange={(e) => setForm({ ...form, confidence_threshold: Number(e.target.value) })}
            />
          </div>
        </div>

        <h3 style={{ marginTop: '1.5rem' }}>Comptes comptables</h3>
        <div className="form-grid">
          <div className="field">
            <label>Compte de charge</label>
            <input
              value={form.expense_account}
              disabled={!canEdit}
              onChange={(e) => setForm({ ...form, expense_account: e.target.value })}
            />
          </div>
          <div className="field">
            <label>Compte TVA</label>
            <input
              value={form.vat_account}
              disabled={!canEdit}
              onChange={(e) => setForm({ ...form, vat_account: e.target.value })}
            />
          </div>
          <div className="field">
            <label>Compte fournisseur</label>
            <input
              value={form.supplier_account}
              disabled={!canEdit}
              onChange={(e) => setForm({ ...form, supplier_account: e.target.value })}
            />
          </div>
        </div>

        <h3 style={{ marginTop: '1.5rem' }}>Cabinet comptable</h3>
        <div className="form-grid">
          <div className="field">
            <label>Cabinet</label>
            <input
              value={form.accountant_firm}
              disabled={!canEdit}
              onChange={(e) => setForm({ ...form, accountant_firm: e.target.value })}
            />
          </div>
          <div className="field">
            <label>Email</label>
            <input
              type="email"
              value={form.accountant_email}
              disabled={!canEdit}
              onChange={(e) => setForm({ ...form, accountant_email: e.target.value })}
            />
          </div>
        </div>

        <div className="actions">
          {canEdit ? (
            <button className="btn" type="submit" disabled={saving}>
              {saving ? 'Enregistrement…' : 'Enregistrer'}
            </button>
          ) : (
            <p className="muted">Lecture seule — demandez un accès paramètres.</p>
          )}
        </div>
        {message && <p className="muted">{message}</p>}
      </form>
    </>
  )
}

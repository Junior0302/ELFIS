import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api, type CompanySettings } from '../api'
import { useAuth } from '../auth'

const empty: Omit<CompanySettings, 'id'> = {
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

export default function SettingsPage() {
  const { token, orgId } = useAuth()
  const [form, setForm] = useState(empty)
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!token) return
    api
      .getSettings(token, orgId)
      .then((s) => {
        setForm({
          company_name: s.company_name,
          siret: s.siret,
          vat_number: s.vat_number,
          default_vat_rate: s.default_vat_rate,
          expense_account: s.expense_account,
          vat_account: s.vat_account,
          supplier_account: s.supplier_account,
          accountant_firm: s.accountant_firm,
          accountant_email: s.accountant_email,
          confidence_threshold: s.confidence_threshold,
        })
      })
      .finally(() => setLoading(false))
  }, [token, orgId])

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setMessage('')
    try {
      if (!token) throw new Error('Authentification requise')
      await api.saveSettings(form, token, orgId)
      setMessage('Paramètres enregistrés.')
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Erreur')
    }
  }

  if (loading) return <div className="loading">Chargement des paramètres…</div>

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Paramètres</h2>
          <p>
            Infos légales, TVA et préférences d’écritures pour l’OCR. Votre profil personnel se
            gère dans Mon compte.
          </p>
        </div>
        <Link className="btn secondary" to="/compte">
          Mon compte
        </Link>
      </div>

      <form className="panel" onSubmit={onSubmit}>
        <h3>Entreprise</h3>
        <div className="form-grid">
          <div className="field full">
            <label>Raison sociale</label>
            <input
              value={form.company_name}
              onChange={(e) => setForm({ ...form, company_name: e.target.value })}
            />
          </div>
          <div className="field">
            <label>SIRET</label>
            <input value={form.siret} onChange={(e) => setForm({ ...form, siret: e.target.value })} />
          </div>
          <div className="field">
            <label>N° TVA</label>
            <input
              value={form.vat_number}
              onChange={(e) => setForm({ ...form, vat_number: e.target.value })}
            />
          </div>
        </div>

        <h3 style={{ marginTop: '1.5rem' }}>TVA</h3>
        <div className="form-grid">
          <div className="field">
            <label>Taux par défaut (%)</label>
            <input
              type="number"
              step="0.1"
              value={form.default_vat_rate}
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
              onChange={(e) => setForm({ ...form, expense_account: e.target.value })}
            />
          </div>
          <div className="field">
            <label>Compte TVA</label>
            <input
              value={form.vat_account}
              onChange={(e) => setForm({ ...form, vat_account: e.target.value })}
            />
          </div>
          <div className="field">
            <label>Compte fournisseur</label>
            <input
              value={form.supplier_account}
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
              onChange={(e) => setForm({ ...form, accountant_firm: e.target.value })}
            />
          </div>
          <div className="field">
            <label>Email</label>
            <input
              type="email"
              value={form.accountant_email}
              onChange={(e) => setForm({ ...form, accountant_email: e.target.value })}
            />
          </div>
        </div>

        <div className="actions">
          <button className="btn" type="submit">
            Enregistrer
          </button>
        </div>
        {message && <p className="muted">{message}</p>}
      </form>
    </>
  )
}

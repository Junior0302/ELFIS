import { useCallback, useState } from 'react'
import {
  api,
  type VaultArchiveMeta,
  type VaultDocument,
  type VaultDocumentType,
} from '../api'
import { useAuth } from '../auth'

const ACCEPT = 'application/pdf,.pdf'
const MAX_BYTES = 15 * 1024 * 1024

const DOCUMENT_TYPES: { value: VaultDocumentType; label: string }[] = [
  { value: 'customer_invoice', label: 'Facture client' },
  { value: 'supplier_invoice', label: 'Facture fournisseur' },
  { value: 'quote', label: 'Devis' },
  { value: 'credit_note', label: 'Avoir' },
  { value: 'expense_report', label: 'Note de frais' },
  { value: 'bank_statement', label: 'Relevé bancaire' },
  { value: 'contract', label: 'Contrat' },
  { value: 'other', label: 'Autre' },
]

type DocumentsTab = 'deposit' | 'list'

function isPdf(file: File) {
  const name = file.name.toLowerCase()
  return name.endsWith('.pdf') || file.type === 'application/pdf'
}

export default function DocumentsPage() {
  const { token, orgId } = useAuth()
  const [tab, setTab] = useState<DocumentsTab>('deposit')
  const [active, setActive] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [result, setResult] = useState<VaultDocument | null>(null)
  const [documentType, setDocumentType] = useState<VaultDocumentType>('customer_invoice')
  const [documentNumber, setDocumentNumber] = useState('')
  const [currency, setCurrency] = useState('EUR')

  const pickFile = (files: FileList | null) => {
    const next = files?.[0]
    if (!next) return
    setError('')
    setSuccess('')
    setResult(null)
    if (!isPdf(next)) {
      setError('Seuls les fichiers PDF sont acceptés.')
      setFile(null)
      return
    }
    if (next.size > MAX_BYTES) {
      setError('Fichier trop volumineux (max 15 Mo).')
      setFile(null)
      return
    }
    setFile(next)
  }

  const archive = useCallback(async () => {
    if (!file) {
      setError('Choisissez un PDF à archiver.')
      return
    }
    if (!token) {
      setError('Authentification requise')
      return
    }
    if (!orgId) {
      setError('Sélectionnez une organisation.')
      return
    }
    setLoading(true)
    setError('')
    setSuccess('')
    setResult(null)
    const meta: VaultArchiveMeta = {
      document_type: documentType,
      document_number: documentNumber.trim() || undefined,
      currency: currency.trim() || 'EUR',
    }
    try {
      const archived = await api.archiveVaultDocument(file, meta, token, orgId)
      setResult(archived)
      setSuccess('Document archivé avec succès dans ELFIS Vault.')
      setFile(null)
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Archivage impossible'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [file, token, orgId, documentType, documentNumber, currency])

  return (
    <>
      <div className="page-head">
        <div>
          <h2>ELFIS Vault – Coffre-fort documentaire sécurisé</h2>
          <p>
            Archivez vos PDF comptables dans le coffre privé de votre entreprise, isolé par
            organisation.
          </p>
        </div>
      </div>

      <div className="billing-tabs" style={{ marginBottom: '1.25rem' }} role="tablist">
        <button
          type="button"
          role="tab"
          className={`billing-tab ${tab === 'deposit' ? 'active' : ''}`}
          aria-selected={tab === 'deposit'}
          onClick={() => setTab('deposit')}
        >
          Déposer un document
        </button>
        <button
          type="button"
          role="tab"
          className={`billing-tab ${tab === 'list' ? 'active' : ''}`}
          aria-selected={tab === 'list'}
          onClick={() => setTab('list')}
        >
          Mes documents
        </button>
      </div>

      {tab === 'deposit' ? (
        <>
          <div
            className={`dropzone ${active ? 'active' : ''} ${loading ? 'busy' : ''}`}
            onDragEnter={(e) => {
              e.preventDefault()
              setActive(true)
            }}
            onDragOver={(e) => {
              e.preventDefault()
              setActive(true)
            }}
            onDragLeave={() => setActive(false)}
            onDrop={(e) => {
              e.preventDefault()
              setActive(false)
              pickFile(e.dataTransfer.files)
            }}
          >
            <div>
              <h3>{loading ? 'Archivage en cours…' : file ? 'Fichier prêt' : 'PDF à archiver'}</h3>
              <p>
                {loading
                  ? 'Envoi sécurisé vers ELFIS Vault…'
                  : file
                    ? `${file.name} (${Math.round(file.size / 1024)} Ko)`
                    : 'Glissez-déposez un PDF (max 15 Mo), ou choisissez un fichier.'}
              </p>
              {!loading && (
                <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', justifyContent: 'center' }}>
                  <label className="btn secondary" style={{ cursor: 'pointer' }}>
                    {file ? 'Changer de PDF' : 'Choisir un PDF'}
                    <input
                      type="file"
                      accept={ACCEPT}
                      hidden
                      onChange={(e) => pickFile(e.target.files)}
                    />
                  </label>
                  {file && (
                    <button type="button" className="btn" onClick={() => void archive()}>
                      Archiver
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>

          <div className="panel" style={{ marginTop: '1.25rem' }}>
            <h3>Informations du document</h3>
            <div className="form-grid">
              <div className="field">
                <label htmlFor="docs-type">Type de document</label>
                <select
                  id="docs-type"
                  value={documentType}
                  onChange={(e) => setDocumentType(e.target.value as VaultDocumentType)}
                  disabled={loading}
                >
                  {DOCUMENT_TYPES.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="docs-number">Numéro de document</label>
                <input
                  id="docs-number"
                  value={documentNumber}
                  onChange={(e) => setDocumentNumber(e.target.value)}
                  placeholder="FACT-2026-000015"
                  disabled={loading}
                />
              </div>
              <div className="field">
                <label htmlFor="docs-currency">Devise</label>
                <input
                  id="docs-currency"
                  value={currency}
                  onChange={(e) => setCurrency(e.target.value.toUpperCase())}
                  maxLength={3}
                  disabled={loading}
                />
              </div>
            </div>

            <div style={{ marginTop: '1rem' }}>
              <button
                type="button"
                className="btn"
                disabled={loading || !file}
                onClick={() => void archive()}
              >
                {loading ? 'Archivage…' : 'Archiver'}
              </button>
            </div>

            {loading && <p className="muted" style={{ marginTop: '0.75rem' }}>Chargement…</p>}
            {error && <p className="form-error">{error}</p>}
            {success && !error && (
              <p className="muted" style={{ marginTop: '0.75rem', color: 'var(--forest)' }}>
                {success}
              </p>
            )}
          </div>

          {result && (
            <div className="panel" style={{ marginTop: '1.25rem' }}>
              <h3>Document archivé</h3>
              <div className="form-grid">
                <div className="field">
                  <label>Identifiant</label>
                  <input readOnly value={result.id} />
                </div>
                <div className="field">
                  <label>Fichier</label>
                  <input readOnly value={result.original_filename} />
                </div>
                <div className="field full">
                  <label>Chemin Storage</label>
                  <input readOnly value={result.storage_path} />
                </div>
                <div className="field full">
                  <label>Checksum SHA-256</label>
                  <input readOnly value={result.checksum_sha256} />
                </div>
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="panel">
          <h3>Mes documents</h3>
          <p className="muted" style={{ margin: '0.75rem 0 0' }}>
            Aucun document archivé pour le moment.
          </p>
        </div>
      )}
    </>
  )
}

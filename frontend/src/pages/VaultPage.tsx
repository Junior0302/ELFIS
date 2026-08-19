import { useCallback, useState } from 'react'
import { api, type VaultArchiveMeta, type VaultDocument, type VaultDocumentType } from '../api'
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

function isPdf(file: File) {
  const name = file.name.toLowerCase()
  return name.endsWith('.pdf') || file.type === 'application/pdf'
}

export default function VaultPage({ embedded = false }: { embedded?: boolean }) {
  const { token, orgId } = useAuth()
  const [active, setActive] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [result, setResult] = useState<VaultDocument | null>(null)
  const [documentType, setDocumentType] = useState<VaultDocumentType>('customer_invoice')
  const [documentNumber, setDocumentNumber] = useState('')
  const [invoiceDate, setInvoiceDate] = useState('')
  const [dueDate, setDueDate] = useState('')
  const [amountHt, setAmountHt] = useState('')
  const [amountVat, setAmountVat] = useState('')
  const [amountTtc, setAmountTtc] = useState('')
  const [currency, setCurrency] = useState('EUR')

  const pickFile = (files: FileList | null) => {
    const next = files?.[0]
    if (!next) return
    setError('')
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
    setResult(null)
    const meta: VaultArchiveMeta = {
      document_type: documentType,
      document_number: documentNumber.trim() || undefined,
      invoice_date: invoiceDate || undefined,
      due_date: dueDate || undefined,
      amount_ht: amountHt.trim() || undefined,
      amount_vat: amountVat.trim() || undefined,
      amount_ttc: amountTtc.trim() || undefined,
      currency: currency.trim() || 'EUR',
    }
    try {
      const archived = await api.archiveVaultDocument(file, meta, token, orgId)
      setResult(archived)
      setFile(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Archivage impossible')
    } finally {
      setLoading(false)
    }
  }, [
    file,
    token,
    orgId,
    documentType,
    documentNumber,
    invoiceDate,
    dueDate,
    amountHt,
    amountVat,
    amountTtc,
    currency,
  ])

  return (
    <>
      {!embedded && (
        <div className="page-head">
          <div>
            <h2>ELFIS Vault – Coffre-fort documentaire sécurisé</h2>
            <p>
              Archivez un PDF dans le coffre privé de votre entreprise : factures, devis, avoirs et
              pièces comptables.
            </p>
          </div>
        </div>
      )}

      {embedded && (
        <div className="page-head" style={{ marginBottom: '1rem' }}>
          <div>
            <h2>ELFIS Vault – Coffre-fort documentaire sécurisé</h2>
            <p>
              Archivez un PDF dans le coffre privé : factures, devis, avoirs et pièces comptables
              (sans analyse IA).
            </p>
          </div>
        </div>
      )}

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
                ? `${file.name} (${Math.round(file.size / 1024)} Ko) — choisissez le type ci-dessous puis archivez.`
                : 'Glissez-déposez un PDF (max 15 Mo), ou choisissez un fichier.'}
          </p>
          {!loading && (
            <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', justifyContent: 'center' }}>
              <label className="btn secondary" style={{ cursor: 'pointer' }}>
                {file ? 'Changer de PDF' : 'Choisir un PDF'}
                <input type="file" accept={ACCEPT} hidden onChange={(e) => pickFile(e.target.files)} />
              </label>
              {file && (
                <button type="button" className="btn" onClick={() => void archive()}>
                  Archiver dans le coffre
                </button>
              )}
            </div>
          )}
          {error && <p className="form-error">{error}</p>}
        </div>
      </div>

      <div className="panel" style={{ marginTop: '1.25rem' }}>
        <h3>Métadonnées (optionnel sauf le type)</h3>
        <div className="form-grid">
          <div className="field">
            <label htmlFor="vault-doc-type">Type de document</label>
            <select
              id="vault-doc-type"
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
            <label htmlFor="vault-doc-number">Numéro (optionnel)</label>
            <input
              id="vault-doc-number"
              value={documentNumber}
              onChange={(e) => setDocumentNumber(e.target.value)}
              placeholder="FACT-2026-000015"
              disabled={loading}
            />
          </div>
          <div className="field">
            <label htmlFor="vault-invoice-date">Date document</label>
            <input
              id="vault-invoice-date"
              type="date"
              value={invoiceDate}
              onChange={(e) => setInvoiceDate(e.target.value)}
              disabled={loading}
            />
          </div>
          <div className="field">
            <label htmlFor="vault-due-date">Échéance</label>
            <input
              id="vault-due-date"
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
              disabled={loading}
            />
          </div>
          <div className="field">
            <label htmlFor="vault-ht">Montant HT</label>
            <input
              id="vault-ht"
              inputMode="decimal"
              value={amountHt}
              onChange={(e) => setAmountHt(e.target.value)}
              placeholder="0.00"
              disabled={loading}
            />
          </div>
          <div className="field">
            <label htmlFor="vault-vat">TVA</label>
            <input
              id="vault-vat"
              inputMode="decimal"
              value={amountVat}
              onChange={(e) => setAmountVat(e.target.value)}
              placeholder="0.00"
              disabled={loading}
            />
          </div>
          <div className="field">
            <label htmlFor="vault-ttc">Montant TTC</label>
            <input
              id="vault-ttc"
              inputMode="decimal"
              value={amountTtc}
              onChange={(e) => setAmountTtc(e.target.value)}
              placeholder="0.00"
              disabled={loading}
            />
          </div>
          <div className="field">
            <label htmlFor="vault-currency">Devise</label>
            <input
              id="vault-currency"
              value={currency}
              onChange={(e) => setCurrency(e.target.value.toUpperCase())}
              maxLength={3}
              disabled={loading}
            />
          </div>
        </div>
      </div>

      {result && (
        <div className="panel" style={{ marginTop: '1.25rem' }}>
          <h3>Document archivé</h3>
          <p>
            <strong>{result.original_filename}</strong> — statut {result.archive_status}
          </p>
          <div className="form-grid">
            <div className="field">
              <label>Identifiant</label>
              <input readOnly value={result.id} />
            </div>
            <div className="field">
              <label>Type</label>
              <input readOnly value={result.document_type} />
            </div>
            <div className="field full">
              <label>Chemin Storage</label>
              <input readOnly value={result.storage_path} />
            </div>
            <div className="field full">
              <label>Checksum SHA-256</label>
              <input readOnly value={result.checksum_sha256} />
            </div>
            <div className="field">
              <label>Taille</label>
              <input readOnly value={`${result.file_size} octets`} />
            </div>
            <div className="field">
              <label>Archivé le</label>
              <input readOnly value={result.archived_at} />
            </div>
          </div>
        </div>
      )}
    </>
  )
}

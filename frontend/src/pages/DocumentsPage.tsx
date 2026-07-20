import { useCallback, useEffect, useState } from 'react'
import {
  api,
  type VaultArchiveMeta,
  type VaultDocument,
  type VaultDocumentDetail,
  type VaultDocumentListItem,
  type VaultDocumentType,
} from '../api'
import { useAuth } from '../auth'
import {
  formatVaultAmount,
  formatVaultDate,
  formatVaultDateTime,
  formatVaultFileSize,
  vaultAccountingStatusLabel,
  vaultArchiveStatusLabel,
  vaultDocumentTypeLabel,
  VAULT_DOCUMENT_TYPE_LABELS,
} from '../vaultFormat'

const ACCEPT = 'application/pdf,.pdf'
const MAX_BYTES = 15 * 1024 * 1024

const DOCUMENT_TYPES = Object.entries(VAULT_DOCUMENT_TYPE_LABELS).map(([value, label]) => ({
  value: value as VaultDocumentType,
  label,
}))

type DocumentsTab = 'deposit' | 'list'

function isPdf(file: File) {
  const name = file.name.toLowerCase()
  return name.endsWith('.pdf') || file.type === 'application/pdf'
}

export default function DocumentsPage() {
  const { token, orgId } = useAuth()
  const [tab, setTab] = useState<DocumentsTab>('deposit')

  // ── dépôt ──────────────────────────────────────────────────────
  const [active, setActive] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [result, setResult] = useState<VaultDocument | null>(null)
  const [documentType, setDocumentType] = useState<VaultDocumentType>('customer_invoice')
  const [documentNumber, setDocumentNumber] = useState('')
  const [currency, setCurrency] = useState('EUR')

  // ── liste ──────────────────────────────────────────────────────
  const [listLoading, setListLoading] = useState(false)
  const [listError, setListError] = useState('')
  const [items, setItems] = useState<VaultDocumentListItem[]>([])
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [totalPages, setTotalPages] = useState(0)
  const [totalItems, setTotalItems] = useState(0)
  const [filterType, setFilterType] = useState<VaultDocumentType | ''>('')
  const [search, setSearch] = useState('')
  const [searchDraft, setSearchDraft] = useState('')
  const [detail, setDetail] = useState<VaultDocumentDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [downloadBusyId, setDownloadBusyId] = useState<string | null>(null)

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
      setError(e instanceof Error ? e.message : 'Archivage impossible')
    } finally {
      setLoading(false)
    }
  }, [file, token, orgId, documentType, documentNumber, currency])

  const loadList = useCallback(async () => {
    if (!token || !orgId) return
    setListLoading(true)
    setListError('')
    try {
      const data = await api.getVaultDocuments(
        {
          page,
          page_size: pageSize,
          document_type: filterType || undefined,
          search: search.trim() || undefined,
          sort_by: 'created_at',
          sort_order: 'desc',
        },
        token,
        orgId,
      )
      setItems(data.items)
      setTotalPages(data.pagination.total_pages)
      setTotalItems(data.pagination.total_items)
    } catch (e) {
      setItems([])
      setListError(e instanceof Error ? e.message : 'Impossible de charger les documents')
    } finally {
      setListLoading(false)
    }
  }, [token, orgId, page, pageSize, filterType, search])

  useEffect(() => {
    if (tab === 'list') void loadList()
  }, [tab, loadList])

  const openDetail = async (id: string) => {
    if (!token || !orgId) return
    setDetailLoading(true)
    setListError('')
    try {
      const data = await api.getVaultDocument(id, token, orgId)
      setDetail(data)
    } catch (e) {
      setListError(e instanceof Error ? e.message : 'Consultation impossible')
    } finally {
      setDetailLoading(false)
    }
  }

  const downloadDoc = async (id: string) => {
    if (!token || !orgId) return
    setDownloadBusyId(id)
    setListError('')
    try {
      const { download_url } = await api.getVaultDocumentDownloadUrl(id, token, orgId)
      // URL temporaire : usage immédiat, pas de localStorage / état global
      window.open(download_url, '_blank', 'noopener,noreferrer')
    } catch (e) {
      setListError(e instanceof Error ? e.message : 'Téléchargement impossible')
    } finally {
      setDownloadBusyId(null)
    }
  }

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
              </div>
            </div>
          )}
        </>
      ) : (
        <>
          <div className="panel">
            <div className="toolbar" style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', alignItems: 'end' }}>
              <div className="field" style={{ margin: 0, minWidth: '10rem' }}>
                <label htmlFor="vault-filter-type">Type</label>
                <select
                  id="vault-filter-type"
                  value={filterType}
                  onChange={(e) => {
                    setPage(1)
                    setFilterType((e.target.value || '') as VaultDocumentType | '')
                  }}
                >
                  <option value="">Tous</option>
                  {DOCUMENT_TYPES.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field" style={{ margin: 0, flex: 1, minWidth: '12rem' }}>
                <label htmlFor="vault-search">Recherche</label>
                <input
                  id="vault-search"
                  value={searchDraft}
                  onChange={(e) => setSearchDraft(e.target.value)}
                  placeholder="Numéro ou nom de fichier"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      setPage(1)
                      setSearch(searchDraft)
                    }
                  }}
                />
              </div>
              <button
                type="button"
                className="btn secondary"
                onClick={() => {
                  setPage(1)
                  setSearch(searchDraft)
                }}
              >
                Filtrer
              </button>
              <button type="button" className="btn secondary" onClick={() => void loadList()} disabled={listLoading}>
                Actualiser
              </button>
            </div>

            {listLoading && <p className="loading" style={{ marginTop: '1rem' }}>Chargement…</p>}
            {listError && <p className="form-error">{listError}</p>}

            {!listLoading && !listError && items.length === 0 && (
              <p className="muted" style={{ marginTop: '1rem' }}>
                Aucun document archivé pour le moment.
              </p>
            )}

            {!listLoading && items.length > 0 && (
              <div className="elfis-table-wrap" style={{ marginTop: '1rem' }}>
                <table className="elfis-lines-table">
                  <thead>
                    <tr>
                      <th>Numéro</th>
                      <th>Fichier</th>
                      <th>Type</th>
                      <th>Date</th>
                      <th>Montant TTC</th>
                      <th>Statut</th>
                      <th>Comptable</th>
                      <th>Archivé le</th>
                      <th>Taille</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((row) => (
                      <tr key={row.id}>
                        <td>{row.document_number || '—'}</td>
                        <td>{row.original_filename}</td>
                        <td>{vaultDocumentTypeLabel(row.document_type)}</td>
                        <td>{formatVaultDate(row.invoice_date)}</td>
                        <td>{formatVaultAmount(row.amount_ttc, row.currency)}</td>
                        <td>{vaultArchiveStatusLabel(row.archive_status)}</td>
                        <td>{vaultAccountingStatusLabel(row.accounting_status)}</td>
                        <td>{formatVaultDateTime(row.archived_at)}</td>
                        <td>{formatVaultFileSize(row.file_size)}</td>
                        <td>
                          <div className="actions" style={{ flexWrap: 'nowrap' }}>
                            <button
                              type="button"
                              className="btn secondary"
                              onClick={() => void openDetail(row.id)}
                              disabled={detailLoading}
                            >
                              Consulter
                            </button>
                            <button
                              type="button"
                              className="btn secondary"
                              onClick={() => void downloadDoc(row.id)}
                              disabled={downloadBusyId === row.id}
                            >
                              {downloadBusyId === row.id ? '…' : 'Télécharger'}
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {totalPages > 1 && (
              <div className="actions" style={{ marginTop: '1rem', alignItems: 'center' }}>
                <button
                  type="button"
                  className="btn secondary"
                  disabled={page <= 1 || listLoading}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  Précédent
                </button>
                <span className="muted">
                  Page {page} / {totalPages} ({totalItems} document{totalItems > 1 ? 's' : ''})
                </span>
                <button
                  type="button"
                  className="btn secondary"
                  disabled={page >= totalPages || listLoading}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Suivant
                </button>
              </div>
            )}
          </div>

          {detail && (
            <div className="panel" style={{ marginTop: '1.25rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
                <h3 style={{ margin: 0 }}>Détail du document</h3>
                <button type="button" className="btn secondary" onClick={() => setDetail(null)}>
                  Fermer
                </button>
              </div>
              <div className="form-grid" style={{ marginTop: '1rem' }}>
                <div className="field">
                  <label>Numéro</label>
                  <input readOnly value={detail.document_number || '—'} />
                </div>
                <div className="field">
                  <label>Type</label>
                  <input readOnly value={vaultDocumentTypeLabel(detail.document_type)} />
                </div>
                <div className="field full">
                  <label>Fichier</label>
                  <input readOnly value={detail.original_filename} />
                </div>
                <div className="field">
                  <label>Date document</label>
                  <input readOnly value={formatVaultDate(detail.invoice_date)} />
                </div>
                <div className="field">
                  <label>Échéance</label>
                  <input readOnly value={formatVaultDate(detail.due_date)} />
                </div>
                <div className="field">
                  <label>Montant TTC</label>
                  <input readOnly value={formatVaultAmount(detail.amount_ttc, detail.currency)} />
                </div>
                <div className="field">
                  <label>Devise</label>
                  <input readOnly value={detail.currency} />
                </div>
                <div className="field">
                  <label>Statut archivage</label>
                  <input readOnly value={vaultArchiveStatusLabel(detail.archive_status)} />
                </div>
                <div className="field">
                  <label>Statut comptable</label>
                  <input readOnly value={vaultAccountingStatusLabel(detail.accounting_status)} />
                </div>
                <div className="field">
                  <label>Archivé le</label>
                  <input readOnly value={formatVaultDateTime(detail.archived_at)} />
                </div>
                <div className="field">
                  <label>Taille</label>
                  <input readOnly value={formatVaultFileSize(detail.file_size)} />
                </div>
              </div>
              <div className="actions" style={{ marginTop: '1rem' }}>
                <button
                  type="button"
                  className="btn"
                  onClick={() => void downloadDoc(detail.id)}
                  disabled={downloadBusyId === detail.id}
                >
                  {downloadBusyId === detail.id ? 'Téléchargement…' : 'Télécharger'}
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </>
  )
}

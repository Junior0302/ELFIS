import { useCallback, useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  api,
  type VaultArchiveMeta,
  type VaultDocument,
  type VaultDocumentDetail,
  type VaultDocumentListItem,
  type VaultDocumentType,
} from '../api'
import { useAuth } from '../auth'
import FirstActionSuccessPanel from '../components/FirstActionSuccessPanel'
import {
  documentSuccessActions,
  documentsPageCopy,
  isLaunchDashboardSource,
  markLaunchDashboardStale,
} from '../firstExperience'
import { EmptyState } from '../ui/UiStates'
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
import '../platform-workspace/platform-workspace.css'

const ACCEPT = 'application/pdf,.pdf'
const MAX_BYTES = 15 * 1024 * 1024

const DOCUMENT_TYPES = Object.entries(VAULT_DOCUMENT_TYPE_LABELS).map(([value, label]) => ({
  value: value as VaultDocumentType,
  label,
}))

type DocumentsTab = 'hub' | 'deposit' | 'list'

/** Types utiles à la vue comptable filtrée (Vault reste propriétaire). */
const ACCOUNTING_DOCUMENT_TYPES: VaultDocumentType[] = [
  'customer_invoice',
  'supplier_invoice',
  'credit_note',
  'bank_statement',
  'expense_report',
]

export type DocumentsSurface = 'accounting' | 'platform'

type DocumentsPageProps = {
  /** accounting = ComptaPilot filtrée ; platform = Vault global ELFIS */
  surface?: DocumentsSurface
}

function isPdf(file: File) {
  const name = file.name.toLowerCase()
  return name.endsWith('.pdf') || file.type === 'application/pdf'
}

export default function DocumentsPage({ surface = 'accounting' }: DocumentsPageProps) {
  const { token, orgId } = useAuth()
  const [searchParams] = useSearchParams()
  const fromLaunch = isLaunchDashboardSource(searchParams.get('source'))
  const highlightDocumentId = (searchParams.get('document_id') || '').trim()
  const isPlatform = surface === 'platform'
  const typeOptions = isPlatform
    ? DOCUMENT_TYPES
    : DOCUMENT_TYPES.filter((t) => ACCOUNTING_DOCUMENT_TYPES.includes(t.value))
  const [tab, setTab] = useState<DocumentsTab>(() =>
    fromLaunch ? 'deposit' : highlightDocumentId ? 'list' : 'list',
  )

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
  const [showSuccessPanel, setShowSuccessPanel] = useState(false)

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
    setShowSuccessPanel(false)
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
    setShowSuccessPanel(false)
    const meta: VaultArchiveMeta = {
      document_type: documentType,
      document_number: documentNumber.trim() || undefined,
      currency: currency.trim() || 'EUR',
    }
    try {
      const archived = await api.archiveVaultDocument(file, meta, token, orgId)
      setResult(archived)
      setSuccess('Document importé')
      setShowSuccessPanel(true)
      setFile(null)
      markLaunchDashboardStale()
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

  useEffect(() => {
    if (tab === 'list') void loadList()
  }, [tab, loadList])

  useEffect(() => {
    if (!highlightDocumentId || tab !== 'list') return
    void openDetail(highlightDocumentId)
    // eslint-disable-next-line react-hooks/exhaustive-deps -- open once when highlight id is present
  }, [highlightDocumentId, tab, token, orgId])

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

  const headTitle = isPlatform
    ? 'Documents'
    : documentsPageCopy({ fromLaunch }).title.replace(/Documents?/i, 'Documents comptables') ||
      'Documents comptables'
  const headLead = isPlatform
    ? 'ELFIS Vault — tous les documents de l’organisation (permissions existantes).'
    : 'Vue filtrée des documents comptables. Le fichier appartient à ELFIS Vault.'

  return (
    <>
      <div className="page-head">
        <div>
          <h2>{isPlatform ? 'Documents' : headTitle}</h2>
          <p>{headLead}</p>
          {fromLaunch ? (
            <p className="muted first-experience-back">
              <Link to="/dashboard">Retour au Dashboard</Link>
            </p>
          ) : null}
        </div>
      </div>

      {!isPlatform ? (
        <div className="platform-surface-banner" style={{ marginBottom: '1rem' }}>
          <strong>Documents comptables · projection Vault</strong>
          <p>
            Factures, avoirs, justificatifs, extraits et pièces liées à la comptabilité. Aucune copie
            de fichier.
          </p>
          <div className="platform-surface-banner__actions">
            <Link className="btn" to="/platform/documents">
              Ouvrir tous les documents dans ELFIS Core
            </Link>
          </div>
        </div>
      ) : (
        <div className="platform-surface-banner" style={{ marginBottom: '1rem' }}>
          <strong>ELFIS Vault</strong>
          <p>Stockage unique. Les Pilots consomment des projections filtrées.</p>
          <div className="platform-surface-banner__actions">
            <Link className="btn secondary" to="/documents">
              Vue documents comptables
            </Link>
          </div>
        </div>
      )}

      <div className="billing-tabs" style={{ marginBottom: '1.25rem' }} role="tablist">
        <button
          type="button"
          role="tab"
          className={`billing-tab ${tab === 'hub' ? 'active' : ''}`}
          aria-selected={tab === 'hub'}
          onClick={() => setTab('hub')}
        >
          Parcours
        </button>
        <button
          type="button"
          role="tab"
          className={`billing-tab ${tab === 'list' ? 'active' : ''}`}
          aria-selected={tab === 'list'}
          onClick={() => setTab('list')}
        >
          Liste & aperçu
        </button>
        <button
          type="button"
          role="tab"
          className={`billing-tab ${tab === 'deposit' ? 'active' : ''}`}
          aria-selected={tab === 'deposit'}
          onClick={() => setTab('deposit')}
        >
          Déposer
        </button>
      </div>

      {tab === 'hub' ? (
        <div className="ui-card-grid">
          <a className="ui-card ui-card-link" href="#/" onClick={(e) => { e.preventDefault(); setTab('list') }}>
            <h3>Liste & filtres</h3>
            <p className="muted">Recherche, type, statut, pagination Vault.</p>
          </a>
          <a className="ui-card ui-card-link" href="#/" onClick={(e) => { e.preventDefault(); setTab('deposit') }}>
            <h3>Dépôt / archive</h3>
            <p className="muted">Archivage PDF sécurisé (Vault API).</p>
          </a>
          <Link className="ui-card ui-card-link" to="/deposit">
            <h3>Analyse documentaire</h3>
            <p className="muted">Flux dépôt + analyse AI existant.</p>
          </Link>
          <Link className="ui-card ui-card-link" to="/history">
            <h3>Extraction & historique</h3>
            <p className="muted">Documents traités, exports, audit métier.</p>
          </Link>
          <Link className="ui-card ui-card-link" to="/migration">
            <h3>Validation / import</h3>
            <p className="muted">Migration Center — validation et import API.</p>
          </Link>
          <Link className="ui-card ui-card-link" to="/accounting">
            <h3>Proposition comptable</h3>
            <p className="muted">Hub comptabilité & moteur V2.</p>
          </Link>
          <Link className="ui-card ui-card-link" to="/search">
            <h3>Recherche</h3>
            <p className="muted">Search Engine global.</p>
          </Link>
          <Link className="ui-card ui-card-link" to="/cockpit">
            <h3>Audit / monitoring</h3>
            <p className="muted">Cockpit jobs & notifications.</p>
          </Link>
        </div>
      ) : null}

      {tab === 'deposit' ? (
        <>
          <p className="muted first-experience-hint" style={{ marginBottom: '1rem' }}>
            Formats autorisés : PDF · taille max 15 Mo. Les fichiers importés sont conservés dans
            votre espace documentaire. L’analyse éventuelle est distincte de l’import.
          </p>

          {showSuccessPanel && result ? (
            <FirstActionSuccessPanel
              title="Document importé"
              description="Le document est maintenant disponible dans votre espace :"
              resourceName={result.original_filename}
              primaryAction={documentSuccessActions().primary}
              secondaryActions={[
                {
                  label: 'Voir le document',
                  onClick: () => {
                    setTab('list')
                    void openDetail(result.id)
                  },
                  tone: 'secondary',
                },
                ...documentSuccessActions().secondary,
              ]}
              extra={
                <p className="muted" style={{ marginBottom: '0.75rem' }}>
                  Import terminé. Une analyse peut démarrer en arrière-plan : elle n’est confirmée
                  que lorsque le backend le signale.
                </p>
              }
            />
          ) : null}

          <div
            className={`dropzone ${active ? 'active' : ''} ${loading ? 'busy' : ''}`}
            aria-busy={loading}
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
                    <button type="button" className="btn" disabled={loading} onClick={() => void archive()}>
                      Importer un document
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
                  {typeOptions.map((opt) => (
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
                aria-busy={loading}
                onClick={() => void archive()}
              >
                {loading ? 'Import en cours…' : 'Importer un document'}
              </button>
            </div>
            {loading && (
              <p className="muted" style={{ marginTop: '0.75rem' }} aria-live="polite">
                Upload en cours…
              </p>
            )}
            {error && (
              <p className="form-error" role="alert">
                {error}{' '}
                <button type="button" className="linkish" onClick={() => void archive()} disabled={loading || !file}>
                  Réessayer
                </button>
              </p>
            )}
            {success && !error && !showSuccessPanel && (
              <p className="muted" style={{ marginTop: '0.75rem', color: 'var(--pilot-primary, var(--forest))' }} role="status">
                {success}
              </p>
            )}
          </div>

          {result && !showSuccessPanel && (
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
                  {typeOptions.map((opt) => (
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
              <EmptyState
                title="Aucun document importé"
                description="Ajoutez vos justificatifs et factures fournisseurs dans votre espace documentaire sécurisé."
                action={
                  <button type="button" className="btn" onClick={() => setTab('deposit')}>
                    Importer un document
                  </button>
                }
              />
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

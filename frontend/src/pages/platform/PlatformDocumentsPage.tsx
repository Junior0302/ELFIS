import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../auth'
import DocumentDownloadButton from '../../components/documents/DocumentDownloadButton'
import DocumentUpload from '../../components/documents/DocumentUpload'
import {
  archiveRegistryDocument,
  downloadRegistryVersion,
  listLegalHolds,
  listRegistryDocuments,
  listRegistryVersions,
  placeLegalHold,
  releaseLegalHold,
  softDeleteRegistryDocument,
  unarchiveRegistryDocument,
  uploadRegistryVersion,
  type RegistryDocument,
  type RegistryLegalHold,
  type RegistryVersion,
} from '../../services/documentRegistryApi'
import {
  createComptaPilotPackage,
  createProcessingJob,
  listBusinessValidations,
  listClassifications,
  listExtractions,
  listOcrResults,
  listProcessingJobs,
  listProductBridges,
  type BusinessValidationResult,
  type DocumentClassification,
  type DocumentExtractionResult,
  type DocumentOCRResult,
  type ProcessingJob,
} from '../../services/documentProcessingApi'
import { can } from '../../types/permissions'

/**
 * Page interne minimale — bibliothèque documentaire complète hors scope.
 * Pas de bouton Purger (purge CLI uniquement).
 */
export default function PlatformDocumentsPage() {
  const { token, orgId, memberships } = useAuth()
  const [items, setItems] = useState<RegistryDocument[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<string | null>(null)
  const [versions, setVersions] = useState<RegistryVersion[]>([])
  const [holdDoc, setHoldDoc] = useState<RegistryDocument | null>(null)
  const [holds, setHolds] = useState<RegistryLegalHold[]>([])
  const [holdReason, setHoldReason] = useState('')
  const [lastJobs, setLastJobs] = useState<Record<string, ProcessingJob>>({})
  const [lastClass, setLastClass] = useState<Record<string, DocumentClassification>>({})
  const [lastOcr, setLastOcr] = useState<Record<string, DocumentOCRResult>>({})
  const [lastExtr, setLastExtr] = useState<Record<string, DocumentExtractionResult>>({})
  const [lastBv, setLastBv] = useState<Record<string, BusinessValidationResult>>({})
  const [bridgePublishEnabled, setBridgePublishEnabled] = useState(false)

  const membership = memberships.find((m) => m.organization_id === orgId)
  const permissions = membership?.permissions || []

  const refresh = useCallback(async () => {
    if (!token) return
    setLoading(true)
    setError(null)
    try {
      const res = await listRegistryDocuments(token, orgId, { limit: 50, offset: 0 })
      setItems(res.items)
      const jobMap: Record<string, ProcessingJob> = {}
      const classMap: Record<string, DocumentClassification> = {}
      const ocrMap: Record<string, DocumentOCRResult> = {}
      const extrMap: Record<string, DocumentExtractionResult> = {}
      const bvMap: Record<string, BusinessValidationResult> = {}
      await Promise.all(
        res.items.slice(0, 20).map(async (doc) => {
          try {
            const jobs = await listProcessingJobs(token, orgId, {
              document_id: doc.id,
              limit: 1,
            })
            if (jobs.items[0]) jobMap[doc.id] = jobs.items[0]
          } catch {
            /* ignore */
          }
          try {
            const cls = await listClassifications(token, orgId, {
              document_id: doc.id,
              limit: 1,
            })
            if (cls.items[0]) classMap[doc.id] = cls.items[0]
          } catch {
            /* ignore */
          }
          try {
            const ocr = await listOcrResults(token, orgId, {
              document_id: doc.id,
              limit: 1,
            })
            if (ocr.items[0]) ocrMap[doc.id] = ocr.items[0]
          } catch {
            /* ignore */
          }
          try {
            const extr = await listExtractions(token, orgId, {
              document_id: doc.id,
              limit: 1,
            })
            if (extr.items[0]) extrMap[doc.id] = extr.items[0]
          } catch {
            /* ignore */
          }
          try {
            const bv = await listBusinessValidations(token, orgId, {
              document_id: doc.id,
              limit: 1,
            })
            if (bv.items[0]) bvMap[doc.id] = bv.items[0]
          } catch {
            /* ignore */
          }
        }),
      )
      setLastJobs(jobMap)
      setLastClass(classMap)
      setLastOcr(ocrMap)
      setLastExtr(extrMap)
      setLastBv(bvMap)
      try {
        const bridges = await listProductBridges(token, orgId)
        const cp = bridges.items.find((b) => b.product_key === 'comptapilot')
        const health = (cp?.health || {}) as { publish_enabled?: boolean }
        setBridgePublishEnabled(Boolean(cp?.bridge_enabled_globally) && Boolean(health.publish_enabled))
      } catch {
        setBridgePublishEnabled(false)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erreur')
    } finally {
      setLoading(false)
    }
  }, [token, orgId])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const canRead = can(permissions, 'documents.read') || can(permissions, '*')
  const canArchive = can(permissions, 'documents.archive') || can(permissions, 'documents.manage') || can(permissions, '*')
  const canDelete = can(permissions, 'documents.delete') || can(permissions, 'documents.manage') || can(permissions, '*')
  const canVersions =
    can(permissions, 'documents.versions.read') ||
    can(permissions, 'documents.read') ||
    can(permissions, '*')
  const canCreateVersion =
    can(permissions, 'documents.versions.create') ||
    can(permissions, 'documents.create') ||
    can(permissions, '*')
  const canHoldManage =
    can(permissions, 'documents.legal_hold.manage') || can(permissions, '*')
  const canProcessCreate =
    can(permissions, 'document_processing.jobs.create') || can(permissions, '*')
  const canOcrCreate =
    can(permissions, 'document_processing.ocr.create') || can(permissions, '*')
  const canOcrRead = can(permissions, 'document_processing.ocr.read') || can(permissions, '*')
  const canExtrCreate =
    can(permissions, 'document_processing.extractions.create') || can(permissions, '*')
  const canExtrRead =
    can(permissions, 'document_processing.extractions.read') || can(permissions, '*')
  const canBvCreate =
    can(permissions, 'document_processing.business_validations.create') || can(permissions, '*')
  const canBvRead =
    can(permissions, 'document_processing.business_validations.read') || can(permissions, '*')
  const canCpPublish =
    can(permissions, 'product_integrations.comptapilot.publish') || can(permissions, '*')
  const canPkgCreate =
    can(permissions, 'product_integrations.packages.create') || can(permissions, '*')

  async function launchProcessing(doc: RegistryDocument) {
    if (!token) return
    try {
      await createProcessingJob(token, orgId, {
        document_id: doc.id,
        idempotency_key: `manual-${doc.id}-${doc.current_version_id || 'nv'}`,
      })
      await refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Traitement')
    }
  }

  async function launchClassification(doc: RegistryDocument) {
    if (!token) return
    try {
      await createProcessingJob(token, orgId, {
        document_id: doc.id,
        document_version_id: doc.current_version_id || undefined,
        pipeline_key: 'document_classification_v1',
        idempotency_key: `class-${doc.id}-${doc.current_version_id || 'nv'}`,
      })
      await refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Classification')
    }
  }

  async function launchOcr(doc: RegistryDocument) {
    if (!token) return
    try {
      await createProcessingJob(token, orgId, {
        document_id: doc.id,
        document_version_id: doc.current_version_id || undefined,
        pipeline_key: 'document_ocr_v1',
        idempotency_key: `ocr-${doc.id}-${doc.current_version_id || 'nv'}`,
        metadata: { force_ocr_enabled: true, noop_mode: 'ok' },
      })
      await refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'OCR')
    }
  }

  async function launchExtraction(doc: RegistryDocument) {
    if (!token) return
    try {
      await createProcessingJob(token, orgId, {
        document_id: doc.id,
        document_version_id: doc.current_version_id || undefined,
        pipeline_key: 'document_extraction_v1',
        idempotency_key: `extr-${doc.id}-${doc.current_version_id || 'nv'}`,
        metadata: { force_extraction_enabled: true, noop_mode: 'ok' },
      })
      await refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Extraction')
    }
  }

  async function launchBusinessValidation(doc: RegistryDocument) {
    if (!token) return
    try {
      await createProcessingJob(token, orgId, {
        document_id: doc.id,
        document_version_id: doc.current_version_id || undefined,
        pipeline_key: 'document_business_validation_v1',
        idempotency_key: `bv-${doc.id}-${doc.current_version_id || 'nv'}`,
        metadata: { force_business_validation_enabled: true },
      })
      await refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Validation documentaire')
    }
  }

  async function prepareComptaPilot(doc: RegistryDocument) {
    if (!token) return
    try {
      await createComptaPilotPackage(token, orgId, {
        document_id: doc.id,
        document_version_id: doc.current_version_id || undefined,
        business_validation_id: lastBv[doc.id]?.id,
      })
      await refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Package ComptaPilot')
    }
  }

  async function toggleVersions(doc: RegistryDocument) {
    if (!token || !canVersions) return
    if (expanded === doc.id) {
      setExpanded(null)
      return
    }
    setExpanded(doc.id)
    try {
      const res = await listRegistryVersions(doc.id, token, orgId)
      setVersions(res.items)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Versions')
    }
  }

  async function openHoldModal(doc: RegistryDocument) {
    if (!token) return
    setHoldDoc(doc)
    try {
      const res = await listLegalHolds(doc.id, token, orgId)
      setHolds(res.items)
    } catch {
      setHolds([])
    }
  }

  return (
    <div className="platform-page">
      <header className="platform-page__header">
        <h1>Documents (registre)</h1>
        <p className="muted">
          Versions, archivage et suppression logique — RC2.4. Pas de purge UI. Hors ComptaPilot.
        </p>
      </header>

      {token ? (
        <DocumentUpload token={token} orgId={orgId} permissions={permissions} onUploaded={() => void refresh()} />
      ) : null}

      {!canRead ? <p className="muted">Permission documents.read requise pour la liste.</p> : null}
      {loading ? <p className="muted">Chargement…</p> : null}
      {error ? <p role="alert">{error}</p> : null}

      {canRead && !loading ? (
        <ul className="platform-simple-list">
          {items.length === 0 ? <li className="muted">Aucun document</li> : null}
          {items.map((doc) => (
            <li key={doc.id}>
              <strong>{doc.title}</strong>
              <span className="muted">
                {' '}
                · {doc.status}
                {doc.document_type ? ` · type ${doc.document_type}` : null}
                {doc.version_count != null ? ` · v×${doc.version_count}` : null}
                {doc.current_version_id ? ` · courant ${doc.current_version_id.slice(0, 8)}` : null}
                {' · '}
                {doc.storage_object?.safe_filename || '—'}
              </span>
              {lastClass[doc.id]?.requires_review ? (
                <span className="muted"> · classification en attente</span>
              ) : null}
              {lastClass[doc.id] && !lastClass[doc.id].requires_review ? (
                <span className="muted">
                  {' '}
                  · classif. {lastClass[doc.id].confirmed_type || lastClass[doc.id].predicted_type}
                  {lastClass[doc.id].document_version_id
                    ? ` (v ${lastClass[doc.id].document_version_id.slice(0, 8)})`
                    : ''}
                </span>
              ) : null}
              {canOcrRead && lastOcr[doc.id] ? (
                <span className="muted">
                  {' '}
                  · OCR {lastOcr[doc.id].status} · {lastOcr[doc.id].extraction_method} ·{' '}
                  {lastOcr[doc.id].page_count}p
                  {lastOcr[doc.id].document_version_id
                    ? ` (v ${lastOcr[doc.id].document_version_id.slice(0, 8)})`
                    : ''}
                </span>
              ) : null}
              {canExtrRead && lastExtr[doc.id] ? (
                <span className="muted">
                  {' '}
                  · extr. {lastExtr[doc.id].status} · {lastExtr[doc.id].schema_key}
                  {lastExtr[doc.id].missing_required_fields_count
                    ? ` · manquants ${lastExtr[doc.id].missing_required_fields_count}`
                    : ''}
                  {lastExtr[doc.id].document_version_id
                    ? ` (v ${lastExtr[doc.id].document_version_id.slice(0, 8)})`
                    : ''}
                </span>
              ) : null}
              {canBvRead && lastBv[doc.id] ? (
                <span className="muted">
                  {' '}
                  · validation documentaire ELFIS {lastBv[doc.id].status}
                  {lastBv[doc.id].blocking_issue_count
                    ? ` · erreurs ${lastBv[doc.id].blocking_issue_count}`
                    : ''}
                  {lastBv[doc.id].warning_count ? ` · warnings ${lastBv[doc.id].warning_count}` : ''}
                </span>
              ) : null}
              {doc.legal_hold_active ? (
                <span className="muted"> · legal hold</span>
              ) : null}
              <div className="platform-inline-actions">
                {token ? (
                  <DocumentDownloadButton
                    documentId={doc.id}
                    token={token}
                    orgId={orgId}
                    permissions={permissions}
                  />
                ) : null}
                {canVersions ? (
                  <button type="button" className="platform-action" onClick={() => void toggleVersions(doc)}>
                    Versions
                  </button>
                ) : null}
                {canArchive && doc.status === 'available' ? (
                  <button
                    type="button"
                    className="platform-action"
                    onClick={() =>
                      void archiveRegistryDocument(doc.id, token!, orgId).then(() => refresh())
                    }
                  >
                    Archiver
                  </button>
                ) : null}
                {canArchive && doc.status === 'archived' ? (
                  <button
                    type="button"
                    className="platform-action"
                    onClick={() =>
                      void unarchiveRegistryDocument(doc.id, token!, orgId).then(() => refresh())
                    }
                  >
                    Désarchiver
                  </button>
                ) : null}
                {canDelete && doc.status !== 'deleted' ? (
                  <button
                    type="button"
                    className="platform-action"
                    onClick={() => {
                      if (!window.confirm('Supprimer logiquement ce document ?')) return
                      void softDeleteRegistryDocument(doc.id, token!, orgId).then(() => refresh())
                    }}
                  >
                    Supprimer
                  </button>
                ) : null}
                {canHoldManage ? (
                  <button type="button" className="platform-action" onClick={() => void openHoldModal(doc)}>
                    Legal hold
                  </button>
                ) : null}
                {canProcessCreate && doc.status === 'available' ? (
                  <button
                    type="button"
                    className="platform-action"
                    onClick={() => void launchProcessing(doc)}
                  >
                    Lancer un traitement
                  </button>
                ) : null}
                {canProcessCreate && doc.status === 'available' ? (
                  <button
                    type="button"
                    className="platform-action"
                    onClick={() => void launchClassification(doc)}
                  >
                    Lancer classification
                  </button>
                ) : null}
                {canOcrCreate && doc.status === 'available' ? (
                  <button
                    type="button"
                    className="platform-action"
                    onClick={() => void launchOcr(doc)}
                  >
                    Lancer OCR
                  </button>
                ) : null}
                {canExtrCreate && doc.status === 'available' ? (
                  <button
                    type="button"
                    className="platform-action"
                    onClick={() => void launchExtraction(doc)}
                  >
                    Extraire les données
                  </button>
                ) : null}
                {canBvCreate && doc.status === 'available' ? (
                  <button
                    type="button"
                    className="platform-action"
                    onClick={() => void launchBusinessValidation(doc)}
                  >
                    Valider le document
                  </button>
                ) : null}
                {bridgePublishEnabled && canCpPublish && canPkgCreate && lastBv[doc.id]?.valid ? (
                  <button
                    type="button"
                    className="platform-action"
                    onClick={() => void prepareComptaPilot(doc)}
                  >
                    Préparer pour ComptaPilot
                  </button>
                ) : null}
                {canBvRead && lastBv[doc.id]?.requires_review ? (
                  <Link to="/elfadmin/processing">Revue validation documentaire</Link>
                ) : null}
                {lastClass[doc.id]?.requires_review ? (
                  <Link to="/elfadmin/processing">Revue classification</Link>
                ) : null}
                {canOcrRead && lastOcr[doc.id]?.requires_review ? (
                  <Link to="/elfadmin/processing">Revue OCR</Link>
                ) : null}
                {canOcrRead && lastOcr[doc.id] ? (
                  <Link to="/elfadmin/processing">Résultat OCR</Link>
                ) : null}
                {canExtrRead && lastExtr[doc.id]?.requires_review ? (
                  <Link to="/elfadmin/processing">Revue extraction</Link>
                ) : null}
                {lastJobs[doc.id] ? (
                  <span className="muted">
                    {' '}
                    · job {lastJobs[doc.id].status}{' '}
                    <Link to="/elfadmin/processing">détail</Link>
                  </span>
                ) : null}
              </div>

              {expanded === doc.id ? (
                <div className="platform-nested">
                  <ul>
                    {versions.map((v) => (
                      <li key={v.id}>
                        v{v.version_number} · {v.status} · {v.original_filename}
                        {token ? (
                          <button
                            type="button"
                            className="platform-action"
                            onClick={() =>
                              void downloadRegistryVersion(doc.id, v.id, token, orgId).then(({ blob, filename }) => {
                                const url = URL.createObjectURL(blob)
                                const a = document.createElement('a')
                                a.href = url
                                a.download = filename
                                a.click()
                                URL.revokeObjectURL(url)
                              })
                            }
                          >
                            Télécharger
                          </button>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                  {canCreateVersion && doc.status === 'available' && token ? (
                    <label>
                      Nouvelle version{' '}
                      <input
                        type="file"
                        onChange={(ev) => {
                          const file = ev.target.files?.[0]
                          if (!file) return
                          void uploadRegistryVersion({
                            documentId: doc.id,
                            file,
                            token,
                            orgId,
                            changeReason: 'ui_replace',
                          }).then(() => {
                            void refresh()
                            void toggleVersions(doc)
                          })
                        }}
                      />
                    </label>
                  ) : null}
                </div>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}

      {holdDoc && token ? (
        <div className="platform-modal" role="dialog" aria-label="Legal hold">
          <h2>Legal hold — {holdDoc.title}</h2>
          <ul>
            {holds.map((h) => (
              <li key={h.id}>
                {h.active ? 'actif' : 'levé'} · {h.reason}
                {h.active && canHoldManage ? (
                  <button
                    type="button"
                    className="platform-action"
                    onClick={() =>
                      void releaseLegalHold(holdDoc.id, h.id, token, orgId).then(() => openHoldModal(holdDoc))
                    }
                  >
                    Lever
                  </button>
                ) : null}
              </li>
            ))}
          </ul>
          {canHoldManage ? (
            <form
              onSubmit={(e) => {
                e.preventDefault()
                if (holdReason.trim().length < 3) return
                void placeLegalHold(holdDoc.id, token, orgId, holdReason.trim()).then(() => {
                  setHoldReason('')
                  void openHoldModal(holdDoc)
                  void refresh()
                })
              }}
            >
              <input
                value={holdReason}
                onChange={(e) => setHoldReason(e.target.value)}
                placeholder="Raison (obligatoire)"
              />
              <button type="submit" className="platform-action">
                Poser
              </button>
            </form>
          ) : null}
          <button type="button" className="platform-action" onClick={() => setHoldDoc(null)}>
            Fermer
          </button>
        </div>
      ) : null}
    </div>
  )
}

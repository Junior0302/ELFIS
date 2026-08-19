import { useCallback, useEffect, useMemo, useState } from 'react'
import { useAuth } from '../../auth'
import ProcessingFiltersBar from '../../components/processing/ProcessingFiltersBar'
import ProcessingJobDetailsDrawer from '../../components/processing/ProcessingJobDetailsDrawer'
import ProcessingJobsTable from '../../components/processing/ProcessingJobsTable'
import ProcessingSummaryCards from '../../components/processing/ProcessingSummaryCards'
import {
  cancelProcessingJob,
  confirmClassification,
  confirmExtraction,
  confirmBusinessValidation,
  getExtractionContent,
  getOcrText,
  getProcessingJob,
  listBusinessValidationIssues,
  listBusinessValidations,
  listClassifications,
  listExtractionFields,
  listExtractions,
  listOcrPages,
  listOcrResults,
  listProcessingAttempts,
  listProcessingJobs,
  listProcessingSteps,
  reclassifyDocument,
  reextractDocument,
  rejectClassification,
  rejectExtraction,
  rejectOcr,
  resolveValidationIssue,
  retryOcr,
  retryProcessingJob,
  type BusinessValidationResult,
  type DocumentClassification,
  type DocumentExtractedField,
  type DocumentExtractionResult,
  type DocumentOCRPage,
  type DocumentOCRResult,
  type ProcessingAttempt,
  type ProcessingJob,
  type ProcessingStep,
  type ValidationIssue,
} from '../../services/documentProcessingApi'
import { can } from '../../types/permissions'

/**
 * Administration jobs + revue classification (score heuristique, pas de probabilité).
 */
export default function PlatformProcessingPage() {
  const { token, orgId, memberships } = useAuth()
  const membership = memberships.find((m) => m.organization_id === orgId)
  const permissions = membership?.permissions || []
  const canRead = can(permissions, 'document_processing.jobs.read') || can(permissions, '*')
  const canCancel =
    can(permissions, 'document_processing.jobs.cancel') ||
    can(permissions, 'document_processing.jobs.manage') ||
    can(permissions, '*')
  const canRetry =
    can(permissions, 'document_processing.jobs.retry') ||
    can(permissions, 'document_processing.jobs.manage') ||
    can(permissions, '*')
  const canReview =
    can(permissions, 'document_processing.classifications.review') || can(permissions, '*')
  const canReclass =
    can(permissions, 'document_processing.classifications.reclassify') || can(permissions, '*')
  const canReadCls =
    can(permissions, 'document_processing.classifications.read') || can(permissions, '*')
  const canReadOcr = can(permissions, 'document_processing.ocr.read') || can(permissions, '*')
  const canRetryOcr =
    can(permissions, 'document_processing.ocr.retry') || can(permissions, '*')
  const canRejectOcr =
    can(permissions, 'document_processing.ocr.reject') || can(permissions, '*')
  const canReadOcrText =
    can(permissions, 'document_processing.ocr.text.read') || can(permissions, '*')
  const canReadExtr =
    can(permissions, 'document_processing.extractions.read') || can(permissions, '*')
  const canReviewExtr =
    can(permissions, 'document_processing.extractions.review') || can(permissions, '*')
  const canRetryExtr =
    can(permissions, 'document_processing.extractions.retry') || can(permissions, '*')
  const canReadExtrContent =
    can(permissions, 'document_processing.extractions.content.read') || can(permissions, '*')
  const canReadBv =
    can(permissions, 'document_processing.business_validations.read') || can(permissions, '*')
  const canReviewBv =
    can(permissions, 'document_processing.business_validations.review') || can(permissions, '*')
  const canConfirmBv =
    can(permissions, 'document_processing.business_validations.confirm') || can(permissions, '*')

  const [items, setItems] = useState<ProcessingJob[]>([])
  const [total, setTotal] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [filters, setFilters] = useState({ status: '', pipeline_key: '', document_id: '' })
  const [selected, setSelected] = useState<ProcessingJob | null>(null)
  const [steps, setSteps] = useState<ProcessingStep[]>([])
  const [attempts, setAttempts] = useState<ProcessingAttempt[]>([])
  const [classifications, setClassifications] = useState<DocumentClassification[]>([])
  const [confirmType, setConfirmType] = useState('')
  const [ocrResults, setOcrResults] = useState<DocumentOCRResult[]>([])
  const [ocrTextId, setOcrTextId] = useState<string | null>(null)
  const [ocrText, setOcrText] = useState<string | null>(null)
  const [ocrPages, setOcrPages] = useState<DocumentOCRPage[]>([])
  const [extractions, setExtractions] = useState<DocumentExtractionResult[]>([])
  const [extrContentId, setExtrContentId] = useState<string | null>(null)
  const [extrContent, setExtrContent] = useState<string | null>(null)
  const [extrFields, setExtrFields] = useState<DocumentExtractedField[]>([])
  const [validations, setValidations] = useState<BusinessValidationResult[]>([])
  const [bvIssuesId, setBvIssuesId] = useState<string | null>(null)
  const [bvIssues, setBvIssues] = useState<ValidationIssue[]>([])

  const load = useCallback(async () => {
    if (!token || !canRead) return
    setError(null)
    try {
      const res = await listProcessingJobs(token, orgId, {
        limit: 50,
        status: filters.status || undefined,
        pipeline_key: filters.pipeline_key || undefined,
        document_id: filters.document_id || undefined,
      })
      setItems(res.items)
      setTotal(res.total)
      if (canReadCls) {
        const cls = await listClassifications(token, orgId, { requires_review: true, limit: 20 })
        setClassifications(cls.items)
      }
      if (canReadOcr) {
        const ocr = await listOcrResults(token, orgId, { requires_review: true, limit: 20 })
        setOcrResults(ocr.items)
      }
      if (canReadExtr) {
        const extr = await listExtractions(token, orgId, { requires_review: true, limit: 20 })
        setExtractions(extr.items)
      }
      if (canReadBv) {
        const bv = await listBusinessValidations(token, orgId, { requires_review: true, limit: 20 })
        setValidations(bv.items)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erreur')
    }
  }, [token, orgId, canRead, canReadCls, canReadOcr, canReadExtr, canReadBv, filters])

  useEffect(() => {
    void load()
  }, [load])

  const cards = useMemo(() => {
    const by = (s: string) => items.filter((j) => j.status === s).length
    return [
      { label: 'Total (page)', value: total },
      { label: 'Queued', value: by('queued') },
      { label: 'Running', value: by('running') },
      { label: 'Failed', value: by('failed') },
      { label: 'Revue classif.', value: classifications.length },
      { label: 'Revue OCR', value: ocrResults.length },
      { label: 'Revue extr.', value: extractions.length },
      { label: 'Revue validation', value: validations.length },
    ]
  }, [items, total, classifications, ocrResults, extractions, validations])

  async function openOcrText(id: string) {
    if (!token || !canReadOcrText) return
    if (ocrTextId === id) {
      setOcrTextId(null)
      setOcrText(null)
      setOcrPages([])
      return
    }
    try {
      const [text, pages] = await Promise.all([
        getOcrText(id, token, orgId),
        listOcrPages(id, token, orgId),
      ])
      setOcrTextId(id)
      setOcrText(text)
      setOcrPages(pages.items)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Texte OCR')
    }
  }

  async function openExtrContent(id: string) {
    if (!token || !canReadExtrContent) return
    if (extrContentId === id) {
      setExtrContentId(null)
      setExtrContent(null)
      setExtrFields([])
      return
    }
    try {
      const [text, fields] = await Promise.all([
        getExtractionContent(id, token, orgId),
        listExtractionFields(id, token, orgId),
      ])
      setExtrContentId(id)
      setExtrContent(text)
      setExtrFields(fields.items)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Contenu extraction')
    }
  }

  async function openJob(job: ProcessingJob) {
    if (!token) return
    setSelected(job)
    try {
      const [full, st, at] = await Promise.all([
        getProcessingJob(job.id, token, orgId),
        listProcessingSteps(job.id, token, orgId),
        listProcessingAttempts(job.id, token, orgId),
      ])
      setSelected(full)
      setSteps(st.items)
      setAttempts(at.items)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Détail')
    }
  }

  async function onCancel() {
    if (!token || !selected) return
    await cancelProcessingJob(selected.id, token, orgId)
    await load()
    await openJob(selected)
  }

  async function onRetry() {
    if (!token || !selected) return
    await retryProcessingJob(selected.id, token, orgId)
    await load()
    await openJob(selected)
  }

  return (
    <div className="platform-page">
      <header className="platform-page__header">
        <h1>Document Processing</h1>
        <p className="muted">
          Jobs, classification, OCR et extraction structurée — pas d’IA générative ni de mapping
          comptable.
        </p>
      </header>
      {!canRead ? <p className="muted">Permission document_processing.jobs.read requise.</p> : null}
      {error ? <p role="alert">{error}</p> : null}
      <ProcessingSummaryCards cards={cards} />
      <ProcessingFiltersBar filters={filters} onChange={setFilters} />
      <ProcessingJobsTable items={items} onSelect={(j) => void openJob(j)} />

      {canReadCls ? (
        <section>
          <h2>Classifications en revue</h2>
          <p className="muted">Score heuristique — confirmation humaine recommandée.</p>
          <ul className="platform-simple-list">
            {classifications.length === 0 ? <li className="muted">Aucune</li> : null}
            {classifications.map((c) => (
              <li key={c.id}>
                <strong>{c.predicted_type}</strong> · score {c.confidence_score.toFixed(2)} (heuristique)
                {c.requires_review ? ' · revue' : ''}
                {c.alternatives?.length ? (
                  <span className="muted">
                    {' '}
                    · alt. {c.alternatives.map((a) => a.type).join(', ')}
                  </span>
                ) : null}
                {c.evidence?.length ? (
                  <span className="muted">
                    {' '}
                    · preuves {c.evidence.map((e) => e.code).slice(0, 5).join(', ')}
                  </span>
                ) : null}
                <div className="platform-inline-actions">
                  {canReview ? (
                    <>
                      <input
                        placeholder="type confirmé"
                        value={confirmType}
                        onChange={(e) => setConfirmType(e.target.value)}
                      />
                      <button
                        type="button"
                        className="platform-action"
                        onClick={() =>
                          void confirmClassification(c.id, token!, orgId, confirmType || c.predicted_type).then(
                            () => load(),
                          )
                        }
                      >
                        Confirmer
                      </button>
                      <button
                        type="button"
                        className="platform-action"
                        onClick={() => void rejectClassification(c.id, token!, orgId, 'revue').then(() => load())}
                      >
                        Rejeter
                      </button>
                    </>
                  ) : null}
                  {canReclass ? (
                    <button
                      type="button"
                      className="platform-action"
                      onClick={() => void reclassifyDocument(c.id, token!, orgId).then(() => load())}
                    >
                      Relancer classification
                    </button>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {canReadOcr ? (
        <section>
          <h2>Résultats OCR (revue)</h2>
          <p className="muted">
            Métadonnées uniquement en liste — le texte n’est chargé qu’à l’ouverture explicite.
          </p>
          <ul className="platform-simple-list">
            {ocrResults.length === 0 ? <li className="muted">Aucun</li> : null}
            {ocrResults.map((o) => (
              <li key={o.id}>
                <strong>{o.provider_key}</strong> · {o.extraction_method} · {o.status}
                {' · '}
                {o.page_count} page(s)
                {o.average_confidence != null
                  ? ` · conf. ${o.average_confidence.toFixed(2)}`
                  : ''}
                {o.requires_review ? ' · revue' : ''}
                {o.warnings?.length ? (
                  <span className="muted"> · warn {o.warnings.slice(0, 3).join(', ')}</span>
                ) : null}
                <span className="muted">
                  {' '}
                  · v {o.document_version_id.slice(0, 8)} · len {o.text_length}
                </span>
                <div className="platform-inline-actions">
                  {canReadOcrText ? (
                    <button
                      type="button"
                      className="platform-action"
                      onClick={() => void openOcrText(o.id)}
                    >
                      {ocrTextId === o.id ? 'Masquer texte' : 'Voir texte'}
                    </button>
                  ) : null}
                  {canRetryOcr ? (
                    <button
                      type="button"
                      className="platform-action"
                      onClick={() => void retryOcr(o.id, token!, orgId).then(() => load())}
                    >
                      Relancer OCR
                    </button>
                  ) : null}
                  {canRejectOcr ? (
                    <button
                      type="button"
                      className="platform-action"
                      onClick={() => void rejectOcr(o.id, token!, orgId).then(() => load())}
                    >
                      Rejeter
                    </button>
                  ) : null}
                </div>
                {ocrTextId === o.id && ocrText != null ? (
                  <div className="platform-nested">
                    <p className="muted">
                      Pages métadonnées :{' '}
                      {ocrPages.map((p) => `p${p.page_number}(${p.character_count})`).join(', ') ||
                        '—'}
                    </p>
                    <pre className="platform-code-block">{ocrText.slice(0, 8000)}</pre>
                  </div>
                ) : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {canReadExtr ? (
        <section>
          <h2>Extractions structurées (revue)</h2>
          <p className="muted">
            Métadonnées en liste — contenu JSON chargé uniquement à l’ouverture explicite.
          </p>
          <ul className="platform-simple-list">
            {extractions.length === 0 ? <li className="muted">Aucune</li> : null}
            {extractions.map((e) => (
              <li key={e.id}>
                <strong>{e.schema_key}</strong> · {e.provider_key} · {e.status}
                {' · '}
                {e.fields_count} champs
                {e.missing_required_fields_count
                  ? ` · manquants ${e.missing_required_fields_count}`
                  : ''}
                {e.invalid_fields_count ? ` · invalides ${e.invalid_fields_count}` : ''}
                {e.confidence_score != null ? ` · score ${e.confidence_score.toFixed(2)}` : ''}
                {e.requires_review ? ' · revue' : ''}
                <span className="muted">
                  {' '}
                  · v {e.document_version_id.slice(0, 8)}
                  {e.effective_document_type ? ` · type ${e.effective_document_type}` : ''}
                </span>
                <div className="platform-inline-actions">
                  {canReadExtrContent ? (
                    <button
                      type="button"
                      className="platform-action"
                      onClick={() => void openExtrContent(e.id)}
                    >
                      {extrContentId === e.id ? 'Masquer contenu' : 'Voir contenu'}
                    </button>
                  ) : null}
                  {canReviewExtr ? (
                    <>
                      <button
                        type="button"
                        className="platform-action"
                        onClick={() => void confirmExtraction(e.id, token!, orgId).then(() => load())}
                      >
                        Confirmer
                      </button>
                      <button
                        type="button"
                        className="platform-action"
                        onClick={() =>
                          void rejectExtraction(e.id, token!, orgId, 'revue').then(() => load())
                        }
                      >
                        Rejeter
                      </button>
                    </>
                  ) : null}
                  {canRetryExtr ? (
                    <button
                      type="button"
                      className="platform-action"
                      onClick={() => void reextractDocument(e.id, token!, orgId).then(() => load())}
                    >
                      Relancer extraction
                    </button>
                  ) : null}
                </div>
                {extrContentId === e.id ? (
                  <div className="platform-nested">
                    <p className="muted">
                      Champs :{' '}
                      {extrFields
                        .map((f) => `${f.field_path}=${f.display_value_masked || f.status}`)
                        .join(', ') || '—'}
                    </p>
                    {extrContent ? (
                      <pre className="platform-code-block">{extrContent.slice(0, 8000)}</pre>
                    ) : null}
                  </div>
                ) : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {canReadBv ? (
        <section>
          <h2>Validation documentaire ELFIS (revue)</h2>
          <p className="muted">Pas de validation comptable — codes d&apos;issues uniquement (pas de montants).</p>
          <ul>
            {validations.length === 0 ? <li className="muted">Aucune</li> : null}
            {validations.map((v) => (
              <li key={v.id}>
                <strong>{v.rule_set_key}</strong> · {v.status} · erreurs {v.blocking_issue_count} · warnings{' '}
                {v.warning_count}
                <span className="muted">
                  {' '}
                  · v {v.document_version_id.slice(0, 8)} · extr {v.extraction_result_id.slice(0, 8)}
                </span>
                <div className="platform-inline-actions">
                  <button
                    type="button"
                    className="platform-action"
                    onClick={() =>
                      void (async () => {
                        if (bvIssuesId === v.id) {
                          setBvIssuesId(null)
                          setBvIssues([])
                          return
                        }
                        const res = await listBusinessValidationIssues(v.id, token!, orgId)
                        setBvIssuesId(v.id)
                        setBvIssues(res.items)
                      })()
                    }
                  >
                    {bvIssuesId === v.id ? 'Masquer issues' : 'Voir issues'}
                  </button>
                  {canConfirmBv ? (
                    <button
                      type="button"
                      className="platform-action"
                      onClick={() =>
                        void confirmBusinessValidation(v.id, token!, orgId).then(() => load())
                      }
                    >
                      Confirmer
                    </button>
                  ) : null}
                </div>
                {bvIssuesId === v.id ? (
                  <ul className="platform-nested">
                    {bvIssues.map((iss) => (
                      <li key={iss.id}>
                        {iss.issue_code} · {iss.severity}
                        {iss.blocking ? ' · blocking' : ''}
                        {iss.resolved ? ` · résolu (${iss.resolution_type})` : ''}
                        {canReviewBv && !iss.resolved ? (
                          <button
                            type="button"
                            className="platform-action"
                            onClick={() =>
                              void resolveValidationIssue(
                                v.id,
                                iss.id,
                                iss.blocking ? 'false_positive' : 'accepted_warning',
                                token!,
                                orgId,
                              ).then(() =>
                                listBusinessValidationIssues(v.id, token!, orgId).then((r) =>
                                  setBvIssues(r.items),
                                ),
                              )
                            }
                          >
                            Résoudre
                          </button>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                ) : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <ProcessingJobDetailsDrawer
        job={selected}
        steps={steps}
        attempts={attempts}
        canCancel={canCancel && !!selected && !['completed', 'cancelled', 'failed'].includes(selected.status)}
        canRetry={
          canRetry &&
          !!selected &&
          ['failed', 'timed_out', 'partially_completed'].includes(selected.status)
        }
        onClose={() => setSelected(null)}
        onCancel={() => void onCancel()}
        onRetry={() => void onRetry()}
      />
    </div>
  )
}

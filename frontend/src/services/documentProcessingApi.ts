export type ProcessingJobStatus =
  | 'pending'
  | 'queued'
  | 'running'
  | 'retrying'
  | 'completed'
  | 'partially_completed'
  | 'failed'
  | 'cancelled'
  | 'timed_out'
  | 'blocked'

export type ProcessingJob = {
  id: string
  document_id: string
  document_version_id: string
  organization_id: number
  product?: string | null
  pipeline_key: string
  status: ProcessingJobStatus | string
  priority: number
  progress_percent: number
  current_step_key?: string | null
  attempts_count: number
  max_attempts: number
  last_error_code?: string | null
  last_error_message_sanitized?: string | null
  created_at?: string | null
  started_at?: string | null
  completed_at?: string | null
  failed_at?: string | null
  cancelled_at?: string | null
}

export type ProcessingStep = {
  id: string
  job_id: string
  step_key: string
  sequence_number: number
  status: string
  required: boolean
  attempts_count: number
  last_error_code?: string | null
  last_error_message_sanitized?: string | null
  started_at?: string | null
  completed_at?: string | null
}

export type ProcessingAttempt = {
  id: string
  job_id: string
  step_id: string
  attempt_number: number
  worker_id?: string | null
  status: string
  duration_ms?: number | null
  error_code?: string | null
  error_message_sanitized?: string | null
  retryable?: boolean
  started_at?: string | null
  completed_at?: string | null
}

function apiRoot(): string {
  const raw = (import.meta.env.VITE_API_URL as string | undefined)?.trim()
  if (raw) return raw.replace(/\/$/, '')
  return '/api'
}

function headers(token: string, orgId?: number | null): HeadersInit {
  const h: Record<string, string> = {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
  }
  if (orgId != null) h['X-Organization-Id'] = String(orgId)
  return h
}

async function parse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    const msg = (body as { detail?: { message?: string } | string })?.detail
    throw new Error(
      typeof msg === 'string' ? msg : msg?.message || `HTTP ${res.status}`,
    )
  }
  return res.json() as Promise<T>
}

export async function listProcessingJobs(
  token: string,
  orgId: number | null | undefined,
  params: { limit?: number; offset?: number; status?: string; document_id?: string; pipeline_key?: string } = {},
) {
  const q = new URLSearchParams()
  q.set('limit', String(params.limit ?? 50))
  q.set('offset', String(params.offset ?? 0))
  if (params.status) q.set('status', params.status)
  if (params.document_id) q.set('document_id', params.document_id)
  if (params.pipeline_key) q.set('pipeline_key', params.pipeline_key)
  const res = await fetch(`${apiRoot()}/document-processing/jobs?${q}`, {
    headers: headers(token, orgId),
  })
  return parse<{ items: ProcessingJob[]; total: number }>(res)
}

export async function getProcessingJob(jobId: string, token: string, orgId?: number | null) {
  const res = await fetch(`${apiRoot()}/document-processing/jobs/${jobId}`, {
    headers: headers(token, orgId),
  })
  return parse<ProcessingJob>(res)
}

export async function listProcessingSteps(jobId: string, token: string, orgId?: number | null) {
  const res = await fetch(`${apiRoot()}/document-processing/jobs/${jobId}/steps`, {
    headers: headers(token, orgId),
  })
  return parse<{ items: ProcessingStep[]; total: number }>(res)
}

export async function listProcessingAttempts(jobId: string, token: string, orgId?: number | null) {
  const res = await fetch(`${apiRoot()}/document-processing/jobs/${jobId}/attempts`, {
    headers: headers(token, orgId),
  })
  return parse<{ items: ProcessingAttempt[]; total: number }>(res)
}

export async function createProcessingJob(
  token: string,
  orgId: number | null | undefined,
  body: {
    document_id: string
    document_version_id?: string
    pipeline_key?: string
    idempotency_key?: string
    metadata?: Record<string, unknown>
  },
) {
  const res = await fetch(`${apiRoot()}/document-processing/jobs`, {
    method: 'POST',
    headers: headers(token, orgId),
    body: JSON.stringify(body),
  })
  return parse<ProcessingJob>(res)
}

export async function cancelProcessingJob(jobId: string, token: string, orgId?: number | null) {
  const res = await fetch(`${apiRoot()}/document-processing/jobs/${jobId}/cancel`, {
    method: 'POST',
    headers: headers(token, orgId),
  })
  return parse<ProcessingJob>(res)
}

export async function retryProcessingJob(jobId: string, token: string, orgId?: number | null) {
  const res = await fetch(`${apiRoot()}/document-processing/jobs/${jobId}/retry`, {
    method: 'POST',
    headers: headers(token, orgId),
  })
  return parse<ProcessingJob>(res)
}

export type DocumentClassification = {
  id: string
  document_id: string
  document_version_id: string
  processing_job_id?: string | null
  organization_id: number
  classifier_key: string
  classifier_version: string
  predicted_type: string
  confidence_score: number
  status: string
  requires_review: boolean
  evidence?: Array<{ code: string; detail?: string; weight?: number }> | null
  alternatives?: Array<{ type: string; score: number }> | null
  confirmed_type?: string | null
  score_kind?: string
  created_at?: string
}

export async function listClassifications(
  token: string,
  orgId: number | null | undefined,
  params: { document_id?: string; version_id?: string; requires_review?: boolean; limit?: number } = {},
) {
  const q = new URLSearchParams()
  q.set('limit', String(params.limit ?? 20))
  if (params.document_id) q.set('document_id', params.document_id)
  if (params.version_id) q.set('version_id', params.version_id)
  if (params.requires_review != null) q.set('requires_review', String(params.requires_review))
  const res = await fetch(`${apiRoot()}/document-processing/classifications?${q}`, {
    headers: headers(token, orgId),
  })
  return parse<{ items: DocumentClassification[]; total: number }>(res)
}

export async function confirmClassification(
  id: string,
  token: string,
  orgId: number | null | undefined,
  confirmed_type: string,
) {
  const res = await fetch(`${apiRoot()}/document-processing/classifications/${id}/confirm`, {
    method: 'POST',
    headers: headers(token, orgId),
    body: JSON.stringify({ confirmed_type }),
  })
  return parse<DocumentClassification>(res)
}

export async function rejectClassification(
  id: string,
  token: string,
  orgId: number | null | undefined,
  reason?: string,
) {
  const res = await fetch(`${apiRoot()}/document-processing/classifications/${id}/reject`, {
    method: 'POST',
    headers: headers(token, orgId),
    body: JSON.stringify({ reason }),
  })
  return parse<DocumentClassification>(res)
}

export async function reclassifyDocument(id: string, token: string, orgId?: number | null) {
  const res = await fetch(`${apiRoot()}/document-processing/classifications/${id}/reclassify`, {
    method: 'POST',
    headers: headers(token, orgId),
  })
  return parse<ProcessingJob>(res)
}

export type DocumentOCRResult = {
  id: string
  document_id: string
  document_version_id: string
  organization_id: number
  processing_job_id?: string | null
  provider_key: string
  provider_version: string
  status: string
  extraction_method: string
  page_count: number
  processed_page_count: number
  average_confidence?: number | null
  text_length: number
  requires_review: boolean
  warnings?: string[] | null
  error_code?: string | null
  error_message_sanitized?: string | null
  selection_reason_code?: string | null
  started_at?: string | null
  completed_at?: string | null
  created_at?: string
}

export type DocumentOCRPage = {
  id: string
  ocr_result_id: string
  page_number: number
  status: string
  character_count: number
  word_count?: number | null
  confidence?: number | null
  detected_language?: string | null
  warnings?: string[] | null
}

export async function listOcrResults(
  token: string,
  orgId: number | null | undefined,
  params: {
    document_id?: string
    version_id?: string
    status?: string
    requires_review?: boolean
    limit?: number
  } = {},
) {
  const q = new URLSearchParams()
  q.set('limit', String(params.limit ?? 20))
  if (params.document_id) q.set('document_id', params.document_id)
  if (params.version_id) q.set('version_id', params.version_id)
  if (params.status) q.set('status', params.status)
  if (params.requires_review != null) q.set('requires_review', String(params.requires_review))
  const res = await fetch(`${apiRoot()}/document-processing/ocr-results?${q}`, {
    headers: headers(token, orgId),
  })
  return parse<{ items: DocumentOCRResult[]; total: number }>(res)
}

export async function getOcrResult(id: string, token: string, orgId?: number | null) {
  const res = await fetch(`${apiRoot()}/document-processing/ocr-results/${id}`, {
    headers: headers(token, orgId),
  })
  return parse<DocumentOCRResult>(res)
}

export async function listOcrPages(id: string, token: string, orgId?: number | null) {
  const res = await fetch(`${apiRoot()}/document-processing/ocr-results/${id}/pages`, {
    headers: headers(token, orgId),
  })
  return parse<{ items: DocumentOCRPage[]; total: number }>(res)
}

export async function getOcrText(id: string, token: string, orgId?: number | null) {
  const res = await fetch(`${apiRoot()}/document-processing/ocr-results/${id}/text`, {
    headers: headers(token, orgId),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error((err as { detail?: string }).detail || `HTTP ${res.status}`)
  }
  return res.text()
}

export async function retryOcr(id: string, token: string, orgId?: number | null) {
  const res = await fetch(`${apiRoot()}/document-processing/ocr-results/${id}/retry`, {
    method: 'POST',
    headers: headers(token, orgId),
  })
  return parse<ProcessingJob>(res)
}

export async function rejectOcr(id: string, token: string, orgId?: number | null) {
  const res = await fetch(`${apiRoot()}/document-processing/ocr-results/${id}/reject`, {
    method: 'POST',
    headers: headers(token, orgId),
  })
  return parse<DocumentOCRResult>(res)
}

export async function listOcrProviders(token: string, orgId?: number | null) {
  const res = await fetch(`${apiRoot()}/document-processing/ocr/providers`, {
    headers: headers(token, orgId),
  })
  return parse<{ items: Array<Record<string, unknown>> }>(res)
}

export type DocumentExtractionResult = {
  id: string
  document_id: string
  document_version_id: string
  organization_id: number
  ocr_result_id?: string | null
  schema_key: string
  schema_version: string
  provider_key: string
  provider_version: string
  status: string
  confidence_score?: number | null
  requires_review: boolean
  fields_count: number
  valid_fields_count: number
  invalid_fields_count: number
  missing_required_fields_count: number
  effective_document_type?: string | null
  warnings?: string[] | null
  created_at?: string
}

export type DocumentExtractedField = {
  id: string
  extraction_result_id: string
  field_path: string
  field_type: string
  status: string
  display_value_masked?: string | null
  confidence_score?: number | null
  manually_corrected?: boolean
}

export async function listExtractions(
  token: string,
  orgId: number | null | undefined,
  params: {
    document_id?: string
    version_id?: string
    status?: string
    requires_review?: boolean
    limit?: number
  } = {},
) {
  const q = new URLSearchParams()
  q.set('limit', String(params.limit ?? 20))
  if (params.document_id) q.set('document_id', params.document_id)
  if (params.version_id) q.set('version_id', params.version_id)
  if (params.status) q.set('status', params.status)
  if (params.requires_review != null) q.set('requires_review', String(params.requires_review))
  const res = await fetch(`${apiRoot()}/document-processing/extractions?${q}`, {
    headers: headers(token, orgId),
  })
  return parse<{ items: DocumentExtractionResult[]; total: number }>(res)
}

export async function listExtractionFields(id: string, token: string, orgId?: number | null) {
  const res = await fetch(`${apiRoot()}/document-processing/extractions/${id}/fields`, {
    headers: headers(token, orgId),
  })
  return parse<{ items: DocumentExtractedField[]; total: number }>(res)
}

export async function getExtractionContent(id: string, token: string, orgId?: number | null) {
  const res = await fetch(`${apiRoot()}/document-processing/extractions/${id}/content`, {
    headers: headers(token, orgId),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error((err as { detail?: string }).detail || `HTTP ${res.status}`)
  }
  return res.text()
}

export async function confirmExtraction(id: string, token: string, orgId?: number | null) {
  const res = await fetch(`${apiRoot()}/document-processing/extractions/${id}/confirm`, {
    method: 'POST',
    headers: headers(token, orgId),
  })
  return parse<DocumentExtractionResult>(res)
}

export async function rejectExtraction(
  id: string,
  token: string,
  orgId?: number | null,
  reason?: string,
) {
  const res = await fetch(`${apiRoot()}/document-processing/extractions/${id}/reject`, {
    method: 'POST',
    headers: headers(token, orgId),
    body: JSON.stringify({ reason }),
  })
  return parse<DocumentExtractionResult>(res)
}

export async function reextractDocument(id: string, token: string, orgId?: number | null) {
  const res = await fetch(`${apiRoot()}/document-processing/extractions/${id}/reextract`, {
    method: 'POST',
    headers: headers(token, orgId),
  })
  return parse<ProcessingJob>(res)
}

export type BusinessValidationResult = {
  id: string
  document_id: string
  document_version_id: string
  organization_id: number
  extraction_result_id: string
  rule_set_key: string
  rule_set_version: string
  status: string
  valid: boolean
  blocking_issue_count: number
  warning_count: number
  info_count: number
  requires_review: boolean
  created_at?: string
}

export type ValidationIssue = {
  id: string
  business_validation_id: string
  rule_key: string
  severity: string
  issue_code: string
  blocking: boolean
  resolved: boolean
  resolution_type?: string | null
  field_paths?: string[] | null
}

export async function listBusinessValidations(
  token: string,
  orgId: number | null | undefined,
  params: {
    document_id?: string
    version_id?: string
    status?: string
    requires_review?: boolean
    limit?: number
  } = {},
) {
  const q = new URLSearchParams()
  q.set('limit', String(params.limit ?? 20))
  if (params.document_id) q.set('document_id', params.document_id)
  if (params.version_id) q.set('version_id', params.version_id)
  if (params.status) q.set('status', params.status)
  if (params.requires_review != null) q.set('requires_review', String(params.requires_review))
  const res = await fetch(`${apiRoot()}/document-processing/business-validations?${q}`, {
    headers: headers(token, orgId),
  })
  return parse<{ items: BusinessValidationResult[]; total: number }>(res)
}

export async function listBusinessValidationIssues(
  id: string,
  token: string,
  orgId?: number | null,
) {
  const res = await fetch(`${apiRoot()}/document-processing/business-validations/${id}/issues`, {
    headers: headers(token, orgId),
  })
  return parse<{ items: ValidationIssue[]; total: number }>(res)
}

export async function confirmBusinessValidation(id: string, token: string, orgId?: number | null) {
  const res = await fetch(`${apiRoot()}/document-processing/business-validations/${id}/confirm`, {
    method: 'POST',
    headers: headers(token, orgId),
  })
  return parse<BusinessValidationResult>(res)
}

export async function resolveValidationIssue(
  validationId: string,
  issueId: string,
  resolution_type: string,
  token: string,
  orgId?: number | null,
) {
  const res = await fetch(
    `${apiRoot()}/document-processing/business-validations/${validationId}/issues/${issueId}/resolve`,
    {
      method: 'POST',
      headers: headers(token, orgId),
      body: JSON.stringify({ resolution_type }),
    },
  )
  return parse<ValidationIssue>(res)
}

export async function listProductBridges(token: string, orgId?: number | null) {
  const res = await fetch(`${apiRoot()}/product-integrations/bridges`, {
    headers: headers(token, orgId),
  })
  return parse<{ items: Array<Record<string, unknown>> }>(res)
}

export async function createComptaPilotPackage(
  token: string,
  orgId: number | null | undefined,
  body: {
    document_id: string
    document_version_id?: string
    business_validation_id?: string
  },
) {
  const res = await fetch(`${apiRoot()}/product-integrations/comptapilot/packages`, {
    method: 'POST',
    headers: headers(token, orgId),
    body: JSON.stringify(body),
  })
  return parse<Record<string, unknown>>(res)
}

export async function deliverComptaPilotPackage(
  packageId: string,
  token: string,
  orgId?: number | null,
) {
  const res = await fetch(
    `${apiRoot()}/product-integrations/comptapilot/packages/${packageId}/deliver`,
    {
      method: 'POST',
      headers: headers(token, orgId),
    },
  )
  return parse<Record<string, unknown>>(res)
}
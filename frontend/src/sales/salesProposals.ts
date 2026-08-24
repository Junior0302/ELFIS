/** SalesPilot Commercial Proposal Engine V1 — types + helpers. */

export type ProposalStatus =
  | 'draft'
  | 'preparing'
  | 'review_required'
  | 'approved'
  | 'sent'
  | 'viewed'
  | 'negotiating'
  | 'accepted'
  | 'rejected'
  | 'expired'
  | 'converted'
  | 'cancelled'

export type ProposalListItem = {
  id: number
  proposal_number: string
  proposal_type: string
  status: ProposalStatus | string
  opportunity_id?: number | null
  sales_company_id?: number | null
  currency: string
  current_version_id?: number | null
  owner_user_id?: number | null
  valid_until?: string | null
  created_at: string
  updated_at: string
}

export type ProposalAction = {
  id: string
  label: string
  kind?: string
  enabled: boolean
  reason?: string | null
  disabled_reason?: string | null
  permission?: string | null
  requires_confirmation?: boolean
  destructive?: boolean
  expected_result?: string | null
}

export type CustomerResolutionMode =
  | 'use_linked_customer'
  | 'use_existing_customer'
  | 'create_new_customer'

export type ProposalConversionState = {
  proposal_id: number
  proposal_status: string
  accepted_version_id?: number | null
  conversion_status: string
  linked_customer_id?: number | null
  linked_invoice_id?: number | null
  customer_resolution?: Record<string, unknown>
  duplicate_candidates?: {
    exact_match?: Array<Record<string, unknown>>
    possible_match?: Array<Record<string, unknown>>
  }
  missing_information?: string[]
  preview_available?: boolean
  can_convert?: boolean
  blockers?: string[]
  warnings?: string[]
  generated_at: string
}

export type InvoiceConversionPreview = {
  proposal: { id: number; proposal_number: string; status: string }
  accepted_version: {
    id: number
    version_number: number
    title?: string
    locked_at?: string | null
  }
  customer?: { id: number; name: string; email?: string | null } | null
  invoice_header: Record<string, unknown>
  invoice_lines: Array<Record<string, unknown>>
  subtotal: string
  discount_total: string
  tax_total: string
  total: string
  currency: string
  payment_terms?: string | null
  notes?: string | null
  warnings: string[]
  blockers: string[]
  source_mapping: Record<string, unknown>
  can_confirm: boolean
  linked_invoice_id?: number | null
}

export type ConvertToInvoiceResult = {
  already_converted: boolean
  proposal_id: number
  invoice_id: number
  invoice_number: string
  invoice_status: string
  customer_id?: number | null
  message?: string | null
}

export function invoiceFromProposalPath(invoiceId: number | string): string {
  return `/facturation?doc=${invoiceId}`
}

export type ProposalWorkspace = {
  header: {
    proposal_id: number
    proposal_number: string
    title: string
    proposal_type: string
    status: string
    company_name?: string | null
    opportunity_name?: string | null
    opportunity_id?: number | null
    version_number?: number | null
    total?: string | number | null
    valid_until?: string | null
    owner_label?: string | null
    currency: string
    updated_at?: string | null
  }
  current_version: {
    id: number
    version_number: number
    status: string
    title: string
    introduction?: string | null
    scope?: string | null
    terms?: string | null
    payment_terms?: string | null
    notes?: string | null
    subtotal: string | number
    discount_total: string | number
    tax_total: string | number
    total: string | number
    currency: string
    valid_until?: string | null
    readiness_score: number
    readiness_level: string
    readiness_explanation?: Record<string, unknown>
    pdf_vault_document_id?: string | null
    checksum?: string | null
    locked_at?: string | null
    updated_at?: string | null
  } | null
  versions: Array<{
    id: number
    version_number: number
    status: string
    total: string | number
    created_at: string
    locked_at?: string | null
  }>
  lines: Array<{
    id: number
    name: string
    description?: string | null
    quantity: string | number
    unit_price: string | number
    discount_type: string
    discount_value: string | number
    tax_rate: string | number
    subtotal: string | number
    discount_amount: string | number
    tax_amount: string | number
    total: string | number
    position: number
  }>
  totals: {
    subtotal: string | number
    discount_total: string | number
    tax_total: string | number
    total: string | number
  }
  readiness: {
    score: number
    level: string
    checks: Array<{ key: string; label: string; status: string; weight: number }>
    blockers: string[]
    warnings: string[]
    recommendations: string[]
  }
  workflow: { status: string; allowed_transitions: string[] }
  company?: { id: number; name: string } | null
  contact?: { id: number; name: string } | null
  opportunity?: { id: number; name: string } | null
  documents: Array<{
    vault_document_id?: string | number | null
    label?: string | null
    open_url?: string | null
    version_number?: number
  }>
  timeline: Array<{ id: number | string; event_type: string; title: string; occurred_at: string }>
  available_actions: ProposalAction[]
  conversion_state?: Record<string, unknown> | null
  generated_at: string
}

export function proposalPath(id: number | string): string {
  return `/sales/proposals/${id}`
}

export function proposalNewPath(opportunityId?: number | null): string {
  return opportunityId
    ? `/sales/proposals/new?opportunity_id=${opportunityId}`
    : '/sales/proposals/new'
}

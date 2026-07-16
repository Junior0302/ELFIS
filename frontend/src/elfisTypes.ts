export type ElfisFieldValue = {
  value: unknown
  confidence: number
  source: string
  status: string
  anomaly?: string | null
}

export type ElfisLineItem = {
  label?: string | null
  description?: string | null
  reference?: string | null
  quantity?: number | null
  unit?: string | null
  unit_price_ht?: number | null
  discount?: number | null
  vat_rate?: number | null
  vat_amount?: number | null
  total_ht?: number | null
  total_ttc?: number | null
}

export type ElfisAnomaly = {
  id: string
  category: string
  title: string
  description: string
  severity: string
  field?: string | null
  detected_value?: unknown
  expected_value?: unknown
  recommended_action: string
  blocking: boolean
}

export type ElfisReport = {
  metadata: {
    analysis_id?: number | null
    document_id: number
    organization_id: number
    analysis_version: string
    processing_time_ms: number
    status: string
    created_at?: string | null
  }
  extraction: {
    supplier: Record<string, ElfisFieldValue>
    customer: Record<string, ElfisFieldValue>
    document: Record<string, ElfisFieldValue>
    line_items: ElfisLineItem[]
    totals: Record<string, ElfisFieldValue>
    legal_mentions: Record<string, ElfisFieldValue>
  }
  confidence: {
    global_score: number
    factors: { label: string; positive: boolean; detail?: string }[]
    missing_fields: string[]
    uncertain_fields: string[]
    summary: string
  }
  accounting: {
    journal: string
    entry_date?: string | null
    label: string
    currency: string
    lines: {
      account: string
      label: string
      debit: number
      credit: number
      justification: string
      certainty: string
    }[]
    total_debit: number
    total_credit: number
    balanced: boolean
    confidence: number
    review_required: boolean
    potential_immobilization: boolean
    explanations: string[]
    status: string
  }
  checks: {
    anomalies: ElfisAnomaly[]
    calculation_checks: ElfisAnomaly[]
    tax_checks: ElfisAnomaly[]
  }
  financial_analysis: {
    status: string
    monthly_weight_pct?: number | null
    cash_impact?: string | null
    recommended_payment_date?: string | null
    amount_remaining?: number | null
    due_in_days?: number | null
    messages: string[]
    limitations?: string
  }
  risk_analysis: {
    score: number
    level: string
    factors: { code: string; label: string; detail: string }[]
    explanation: string
    recommendation: string
  }
  tax_analysis: {
    recoverable_vat?: number | null
    vat_rate?: number | null
    messages: string[]
    disclaimer: string
    potential_immobilization: boolean
  }
  compliance: {
    items: { code: string; label: string; status: string; detail?: string }[]
    synthesis: string
    summary: string
  }
  supplier_intelligence: {
    status: string
    known_supplier?: boolean | null
    document_count: number
    average_amount?: number | null
    cumulative_amount?: number | null
    messages: string[]
    iban_history: string[]
  }
  recommendations: {
    category: string
    priority: string
    title: string
    description: string
    action: string
    reason: string
  }[]
  cfo_summary: {
    what_is_it: string
    is_coherent: string
    main_impact: string
    next_action: string
    summary: string
    limitations: string[]
  }
  summary_card: {
    document_type?: string
    amount_ttc?: number | null
    confidence_pct?: number
    status?: string
    risk_level?: string
    anomaly_count?: number
    fields_extracted?: number
    processing_time_ms?: number
    accounting_balanced?: boolean
    ready_label?: string
  }
}

export type ElfisAnalysisHistoryItem = {
  id: number
  created_at: string | null
  analysis_version: string
  processing_time_ms: number
  status: string
}

export type IntelligenceOverview = {
  period: string
  period_label: string
  company_synthesis: {
    revenue: number | null
    expenses: number
    estimated_result: number | null
    estimated_vat: number
    client_invoices_pending: number
    client_amount_pending: number
    supplier_invoices_to_pay: number
    supplier_amount: number
    treasury: string
    documents_analyzed: number
    open_anomalies: number
  }
  alerts: {
    type: string
    priority: string
    title: string
    description: string
    document_id?: number | null
    document_label?: string
  }[]
  recent_activity: {
    id: number
    supplier: string | null
    number: string | null
    amount_ttc: number | null
    status: string
    date: string | null
    needs_review: boolean
  }[]
  anomalies: IntelligenceOverview['alerts']
  forecasts: {
    status: string
    outflows_30d: number | null
    inflows_expected: number | null
    vat_estimate: number
    method: string
    limitations: string
  }
  opportunities: {
    type: string
    title: string
    description: string
    document_id?: number
  }[]
}

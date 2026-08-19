import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import AccountingProposalPanel from '../components/AccountingProposalPanel'
import { Skeleton } from '../ui/UiStates'

function invoiceToPayload(inv: {
  document_type: string | null
  invoice_number: string | null
  invoice_date: string | null
  supplier: string | null
  amount_ht: number | null
  amount_tva: number | null
  amount_ttc: number | null
  vat_rate: number | null
  confidence_score: number | null
}) {
  return {
    document_type: inv.document_type || 'invoice',
    document_number: inv.invoice_number,
    document_date: inv.invoice_date,
    supplier_name: inv.supplier,
    amount_ht: inv.amount_ht,
    amount_vat: inv.amount_tva,
    amount_ttc: inv.amount_ttc,
    vat_rate: inv.vat_rate,
    currency: 'EUR',
    extraction_confidence: inv.confidence_score,
    validation_confidence: inv.confidence_score,
  }
}

export default function AccountingEnginePage() {
  const { token, orgId } = useAuth()
  const [params] = useSearchParams()
  const invoiceId = params.get('invoice_id')
  const [payload, setPayload] = useState<Record<string, unknown> | undefined>(undefined)
  const [resolvedInvoiceId, setResolvedInvoiceId] = useState<number | undefined>()
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!token || orgId == null) {
      setLoading(false)
      return
    }
    let cancelled = false
    async function load() {
      try {
        if (invoiceId) {
          const inv = await api.getDocument(Number(invoiceId), token!, orgId)
          if (cancelled) return
          setPayload(invoiceToPayload(inv))
          setResolvedInvoiceId(inv.id)
          return
        }
        const list = await api.listDocuments({}, token!, orgId)
        const inv = list[0]
        if (inv && !cancelled) {
          setPayload(invoiceToPayload(inv))
          setResolvedInvoiceId(inv.id)
        }
      } catch {
        if (!cancelled) {
          setPayload(undefined)
          setResolvedInvoiceId(undefined)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [token, orgId, invoiceId])

  if (!token || orgId == null) {
    return <p className="muted">Authentification requise</p>
  }

  return (
    <div className="page">
      <p className="muted">
        <Link to="/accounting">← Comptabilité</Link>
      </p>
      {loading ? <Skeleton rows={4} /> : null}
      {!loading ? (
        <AccountingProposalPanel
          token={token}
          orgId={orgId}
          invoiceId={resolvedInvoiceId}
          initialPayload={payload || { document_type: 'invoice', currency: 'EUR' }}
        />
      ) : null}
    </div>
  )
}

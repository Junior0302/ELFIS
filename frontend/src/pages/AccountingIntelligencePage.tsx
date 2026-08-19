import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import AccountingIntelligencePanel from '../components/AccountingIntelligencePanel'
import { Skeleton } from '../ui/UiStates'

export default function AccountingIntelligencePage() {
  const { token, orgId } = useAuth()
  const [payload, setPayload] = useState<Record<string, unknown> | undefined>()
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!token || orgId == null) {
      setLoading(false)
      return
    }
    let cancelled = false
    api
      .listDocuments({}, token, orgId)
      .then((list) => {
        if (cancelled) return
        const inv = list[0]
        if (!inv) return
        setPayload({
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
        })
      })
      .catch(() => undefined)
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [token, orgId])

  if (!token || orgId == null) {
    return <p className="muted">Authentification requise</p>
  }

  return (
    <div className="page">
      <p className="muted">
        <Link to="/accounting">← Comptabilité</Link>
        {' · '}
        <Link to="/accounting/engine">Moteur V2</Link>
      </p>
      {loading ? <Skeleton rows={4} /> : null}
      {!loading ? (
        <AccountingIntelligencePanel
          token={token}
          orgId={orgId}
          initialPayload={payload || { document_type: 'invoice', currency: 'EUR' }}
        />
      ) : null}
    </div>
  )
}

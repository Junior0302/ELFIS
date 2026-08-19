import { useCallback, useEffect, useState } from 'react'
import {
  confidenceLabel,
  documentExtractionApi,
  extractionStatusLabel,
  fieldCount,
  type ExtractionRecord,
} from '../services/documentExtractionApi'

type Props = {
  token: string
  orgId: number
  migrationSessionId: string
}

function summaryFields(data: Record<string, unknown>): string {
  const parts: string[] = []
  const num = data.document_number || data.quote_number || data.credit_note_number
  if (typeof num === 'string') parts.push(`N° ${num}`)
  const date = data.document_date || data.issue_date || data.credit_note_date
  if (typeof date === 'string') parts.push(String(date))
  const amounts = data.amounts as Record<string, unknown> | undefined
  if (amounts?.total_including_tax != null) parts.push(`TTC ${amounts.total_including_tax}`)
  if (typeof data.currency === 'string') parts.push(data.currency)
  const supplier = data.supplier as Record<string, unknown> | undefined
  if (typeof supplier?.name === 'string') parts.push(supplier.name)
  if (typeof data.merchant_name === 'string') parts.push(data.merchant_name)
  return parts.join(' · ') || '—'
}

export default function MigrationExtractionPanel({ token, orgId, migrationSessionId }: Props) {
  const [items, setItems] = useState<ExtractionRecord[]>([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [statusMessage, setStatusMessage] = useState('Extraction structurée')
  const [detailId, setDetailId] = useState<string | null>(null)
  const [provenance, setProvenance] = useState<Record<string, unknown> | null>(null)
  const [lowFields, setLowFields] = useState<string[]>([])

  const reload = useCallback(async () => {
    const data = await documentExtractionApi.listExtractions(token, orgId, migrationSessionId)
    setItems(data.items)
  }, [token, orgId, migrationSessionId])

  useEffect(() => {
    let cancelled = false
    async function boot() {
      try {
        await reload()
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Chargement extraction impossible')
      }
    }
    void boot()
    return () => {
      cancelled = true
    }
  }, [reload])

  async function runExtraction() {
    if (busy) return
    setBusy(true)
    setError('')
    setStatusMessage('Extraction en cours')
    try {
      const result = await documentExtractionApi.extractSession(token, orgId, migrationSessionId)
      await reload()
      if (result.errors.length) {
        setStatusMessage(`Extraction terminée avec ${result.errors.length} erreur(s)`)
      } else {
        setStatusMessage(`${result.extracted} proposition(s) en attente de validation`)
      }
    } catch (e) {
      const err = e as Error & { code?: string; status?: number }
      if (err.code === 'QUOTA_EXCEEDED' || err.status === 429) {
        setError('Quota d’extraction dépassé')
        setStatusMessage('Quota dépassé')
      } else if (err.status === 403) {
        setError('Permission refusée')
        setStatusMessage('Permission refusée')
      } else {
        setError(err.message || 'Extraction impossible')
        setStatusMessage('Échec de l’extraction')
      }
    } finally {
      setBusy(false)
    }
  }

  async function openDetail(id: string) {
    setDetailId(id)
    try {
      const [prov, fields] = await Promise.all([
        documentExtractionApi.getProvenance(token, orgId, id),
        documentExtractionApi.getFields(token, orgId, id),
      ])
      setProvenance(prov.provenance)
      setLowFields(fields.low_confidence)
    } catch {
      setProvenance(null)
      setLowFields([])
    }
  }

  async function onRetry(id: string) {
    if (busy) return
    setBusy(true)
    try {
      await documentExtractionApi.retry(token, orgId, id)
      await reload()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Relance impossible')
    } finally {
      setBusy(false)
    }
  }

  async function onCancel(id: string) {
    if (busy) return
    setBusy(true)
    try {
      await documentExtractionApi.cancel(token, orgId, id)
      await reload()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Annulation impossible')
    } finally {
      setBusy(false)
    }
  }

  const detail = items.find((i) => i.id === detailId) || null
  const awaiting = items.filter((i) => i.status === 'awaiting_human_validation')
  const ocrPending = items.filter((i) => i.status === 'ocr_pending')

  return (
    <div className="migration-extraction panel">
      <h3>Extraction IA (proposition)</h3>
      <p className="muted">
        Données structurées versionnées en attente de validation humaine. Aucun import métier, aucun
        client/fournisseur créé, aucune écriture comptable.
      </p>

      <div className="migration-analysis-toolbar">
        <button type="button" className="btn" disabled={busy} onClick={() => void runExtraction()}>
          {busy ? 'Extraction…' : 'Lancer l’extraction'}
        </button>
        <button type="button" className="btn secondary" disabled={busy} onClick={() => void reload()}>
          Actualiser
        </button>
        <span className="muted">{statusMessage}</span>
      </div>

      <p className="muted">
        Prêts / validables : {awaiting.length} · Attente OCR : {ocrPending.length} · Total :{' '}
        {items.length}
      </p>

      {error ? <div className="form-error">{error}</div> : null}

      <ul className="migration-analysis-list">
        {items.map((r) => (
          <li key={r.id} className={`is-${r.status}`}>
            <div className="migration-progress-bar" aria-label="Progression">
              <span style={{ width: `${r.progress_percent}%` }} />
            </div>
            <div>
              <strong>
                {r.universal_document_id || r.document_id.slice(0, 8)}
                {r.schema_name ? ` · ${r.schema_name}` : ''}
              </strong>
              <p className="muted">
                {extractionStatusLabel(r.status)}
                {' · '}Confiance {confidenceLabel(r.confidence_level)}
                {r.overall_confidence != null
                  ? ` (${Math.round(r.overall_confidence * 100)}%)`
                  : ''}
                {' · '}
                {fieldCount(r.structured_data)} champ(s)
                {r.strategy ? ` · ${r.strategy}` : ''}
              </p>
              <p className="muted">{summaryFields(r.structured_data)}</p>
              {r.warnings?.length ? (
                <p className="muted">Avertissements : {r.warnings.length}</p>
              ) : null}
              {r.errors?.length ? <p className="form-error">Erreurs : {r.errors.length}</p> : null}
              <div className="migration-analysis-toolbar">
                <button type="button" className="btn secondary" onClick={() => void openDetail(r.id)}>
                  Détail
                </button>
                <button
                  type="button"
                  className="btn secondary"
                  disabled={busy}
                  onClick={() => void onRetry(r.id)}
                >
                  Relancer
                </button>
                <button
                  type="button"
                  className="btn secondary"
                  disabled={busy || r.status === 'awaiting_human_validation'}
                  onClick={() => void onCancel(r.id)}
                >
                  Annuler
                </button>
              </div>
            </div>
          </li>
        ))}
      </ul>

      {!items.length ? (
        <p className="muted">
          Aucune extraction. Analysez d’abord les documents jusqu’à « prêts pour l’IA », puis lancez
          l’extraction.
        </p>
      ) : null}

      {detail ? (
        <div className="migration-extraction-detail">
          <h4>Détail — {detail.universal_document_id || detail.id.slice(0, 8)}</h4>
          <p className="muted">Revue seule — édition finale au Sprint 5. Pas d’import.</p>
          <section>
            <h5>1. Résumé</h5>
            <p className="muted">
              Schéma {detail.schema_name} · Confiance globale {confidenceLabel(detail.confidence_level)}{' '}
              · Revue humaine obligatoire
            </p>
          </section>
          <section>
            <h5>2–7. Parties / Dates / Montants / Taxes / Lignes / Paiement</h5>
            <pre className="muted" style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem' }}>
              {JSON.stringify(detail.structured_data, null, 2)}
            </pre>
          </section>
          <section>
            <h5>8. Avertissements</h5>
            <p className="muted">{JSON.stringify(detail.warnings || [])}</p>
          </section>
          <section>
            <h5>9. Provenance</h5>
            {lowFields.length ? (
              <p className="form-error">Champs faibles : {lowFields.join(', ')}</p>
            ) : null}
            <pre className="muted" style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem' }}>
              {JSON.stringify(provenance || {}, null, 2)}
            </pre>
          </section>
          <section>
            <h5>10. Technique (limité)</h5>
            <p className="muted">
              Stratégie {detail.strategy || '—'} · Source texte {detail.text_source || '—'} · Étape{' '}
              {detail.current_step || '—'} · {detail.progress_percent}%
            </p>
          </section>
          <button type="button" className="btn secondary" onClick={() => setDetailId(null)}>
            Fermer
          </button>
        </div>
      ) : null}
    </div>
  )
}

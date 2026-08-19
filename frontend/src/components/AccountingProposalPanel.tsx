import { useCallback, useEffect, useState } from 'react'
import {
  accountingEngineApi,
  type AccountingEngineProposal,
} from '../services/accountingEngineApi'

type Props = {
  token: string
  orgId: number
  /** Payload métier optionnel (ex. après validation) */
  initialPayload?: Record<string, unknown>
  invoiceId?: number
}

export default function AccountingProposalPanel({
  token,
  orgId,
  initialPayload,
  invoiceId,
}: Props) {
  const [proposal, setProposal] = useState<AccountingEngineProposal | null>(null)
  const [explanation, setExplanation] = useState<Record<string, unknown> | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const loadExtras = useCallback(
    async (id: string) => {
      try {
        const [c, e] = await Promise.all([
          accountingEngineApi.confidence(token, orgId, id),
          accountingEngineApi.explanation(token, orgId, id),
        ])
        setExplanation({ ...e, confidence: c })
      } catch {
        setExplanation(null)
      }
    },
    [token, orgId],
  )

  async function generate() {
    if (busy) return
    setBusy(true)
    setError('')
    try {
      const p = await accountingEngineApi.generate(token, orgId, {
        payload: initialPayload,
        invoice_id: invoiceId,
        source_document_id: invoiceId != null ? String(invoiceId) : undefined,
        source_kind: invoiceId != null ? 'invoice' : 'manual',
      })
      setProposal(p)
      await loadExtras(p.id)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Génération impossible')
    } finally {
      setBusy(false)
    }
  }

  async function regenerate() {
    if (!proposal || busy) return
    setBusy(true)
    setError('')
    try {
      const p = await accountingEngineApi.regenerate(token, orgId, proposal.id)
      setProposal(p)
      await loadExtras(p.id)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Régénération impossible')
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => {
    // pas d'auto-génération — l'utilisateur déclenche
  }, [])

  const scorePct = Math.round((proposal?.confidence_score ?? 0) * 100)

  return (
    <div className="migration-analysis-panel">
      <header className="migration-analysis-toolbar" style={{ justifyContent: 'space-between' }}>
        <div>
          <h3>Proposition comptable V2</h3>
          <p className="muted">
            Moteur Accounting Engine — aucune écriture définitive
          </p>
        </div>
        <div className="migration-analysis-toolbar">
          <button type="button" className="btn" disabled={busy} onClick={() => void generate()}>
            Générer
          </button>
          <button
            type="button"
            className="btn secondary"
            disabled={busy || !proposal}
            onClick={() => void regenerate()}
          >
            Régénérer
          </button>
        </div>
      </header>

      {error ? <div className="form-error">{error}</div> : null}

      {proposal ? (
        <>
          <section>
            <h4>
              Journal {proposal.journal_code} — {proposal.journal_label}
            </h4>
            <p className="muted">
              {proposal.document_type} · {proposal.direction} · {proposal.status} · v
              {proposal.version}
            </p>
            <div className="migration-progress-bar" aria-label="Score de confiance">
              <span style={{ width: `${scorePct}%` }} />
            </div>
            <p className="muted">Confiance {scorePct}%</p>
          </section>

          <section style={{ marginTop: '1rem' }}>
            <h4>TVA & montants</h4>
            <p className="muted">
              HT {proposal.amount_ht?.toFixed?.(2) ?? '—'} · TVA{' '}
              {proposal.amount_vat?.toFixed?.(2) ?? '—'} ({proposal.vat_rate ?? '—'}%) · TTC{' '}
              {proposal.amount_ttc?.toFixed?.(2) ?? '—'} {proposal.currency}
            </p>
          </section>

          <section style={{ marginTop: '1rem' }}>
            <h4>Comptes / lignes</h4>
            <ul className="migration-analysis-list">
              {(proposal.lines || []).map((l) => (
                <li key={l.line_number}>
                  <strong>
                    {l.account_code} · {l.account_label}
                  </strong>
                  <p className="muted">
                    Débit {Number(l.debit || 0).toFixed(2)} · Crédit {Number(l.credit || 0).toFixed(2)}
                  </p>
                </li>
              ))}
            </ul>
          </section>

          <section style={{ marginTop: '1rem' }}>
            <h4>Explications & warnings</h4>
            <ul>
              {(proposal.explanations || []).map((x, i) => (
                <li key={`e-${i}`} className="muted">
                  {x}
                </li>
              ))}
            </ul>
            {(proposal.warnings || []).length ? (
              <div className="form-error" style={{ marginTop: '0.5rem' }}>
                {(proposal.warnings || []).join(' · ')}
              </div>
            ) : null}
            {(proposal.errors || []).length ? (
              <div className="form-error">{(proposal.errors || []).join(' · ')}</div>
            ) : null}
          </section>

          {explanation ? (
            <section style={{ marginTop: '1rem' }}>
              <h4>Comparaison avant / après</h4>
              <pre className="muted" style={{ whiteSpace: 'pre-wrap', fontSize: '0.8rem' }}>
                {JSON.stringify(
                  (explanation as { comparison?: unknown }).comparison || explanation,
                  null,
                  2,
                )}
              </pre>
            </section>
          ) : null}

          <p className="muted" style={{ marginTop: '1rem' }}>
            {proposal.disclaimer}
          </p>
        </>
      ) : (
        <p className="muted">Générez une proposition à partir des données métier validées.</p>
      )}
    </div>
  )
}

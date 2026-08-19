import { useState, type FormEvent } from 'react'
import { formatEuro, type SalesDoc } from '../api'

type Props = {
  doc: SalesDoc
  busy?: boolean
  onClose: () => void
  onSubmit: (payload: {
    amount: number
    method: string
    reference: string
    paid_at?: string
  }) => void | Promise<void>
}

function todayIso(): string {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

/** Convertit YYYY-MM-DD → DD-MM-YYYY (format stocké BE). */
export function isoDateToPaidAt(iso: string): string {
  const [y, m, d] = iso.split('-')
  if (!y || !m || !d) return iso
  return `${d}-${m}-${y}`
}

export default function InvoicePaymentModal({ doc, busy, onClose, onSubmit }: Props) {
  const remaining = Math.max(Math.round((doc.amount_ttc - (doc.paid_amount || 0)) * 100) / 100, 0)
  const [amount, setAmount] = useState(remaining > 0 ? remaining : doc.amount_ttc)
  const [method, setMethod] = useState('virement')
  const [reference, setReference] = useState('')
  const [paidAtIso, setPaidAtIso] = useState(todayIso())
  const [error, setError] = useState('')

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    const value = Number(amount)
    if (!Number.isFinite(value) || value <= 0) {
      setError('Indiquez un montant positif.')
      return
    }
    if (value > remaining + 0.009 && remaining > 0) {
      setError(`Le montant ne peut pas dépasser le reste dû (${formatEuro(remaining)}).`)
      return
    }
    if (!paidAtIso) {
      setError('Indiquez la date de paiement.')
      return
    }
    await onSubmit({
      amount: Math.round(value * 100) / 100,
      method,
      reference: reference.trim(),
      paid_at: isoDateToPaidAt(paidAtIso),
    })
  }

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label="Enregistrer un paiement">
      <div className="modal-panel" style={{ maxWidth: 440 }}>
        <div className="modal-head">
          <div>
            <h3>Enregistrer un paiement</h3>
            <p className="muted">
              {doc.number} · {doc.customer_name} · Reste dû {formatEuro(remaining)}
            </p>
          </div>
          <button className="btn secondary" type="button" onClick={onClose} disabled={busy}>
            Fermer
          </button>
        </div>

        <form onSubmit={(e) => void handleSubmit(e)}>
          <div className="form-grid">
            <div className="field">
              <label htmlFor="pay_amount">Montant (€)</label>
              <input
                id="pay_amount"
                type="number"
                step="0.01"
                min="0.01"
                value={amount}
                onChange={(e) => setAmount(Number(e.target.value))}
                disabled={busy}
                required
              />
            </div>
            <div className="field">
              <label htmlFor="pay_date">Date</label>
              <input
                id="pay_date"
                type="date"
                value={paidAtIso}
                onChange={(e) => setPaidAtIso(e.target.value)}
                disabled={busy}
                required
              />
            </div>
            <div className="field">
              <label htmlFor="pay_method">Mode</label>
              <select
                id="pay_method"
                value={method}
                onChange={(e) => setMethod(e.target.value)}
                disabled={busy}
              >
                <option value="virement">Virement</option>
                <option value="cb">Carte bancaire</option>
                <option value="cheque">Chèque</option>
                <option value="especes">Espèces</option>
                <option value="prelevement">Prélèvement</option>
                <option value="autre">Autre</option>
              </select>
            </div>
            <div className="field">
              <label htmlFor="pay_ref">Référence</label>
              <input
                id="pay_ref"
                value={reference}
                onChange={(e) => setReference(e.target.value)}
                placeholder="N° virement, chèque…"
                disabled={busy}
              />
            </div>
          </div>
          {error ? <p className="form-error">{error}</p> : null}
          <div className="actions">
            <button className="btn secondary" type="button" onClick={onClose} disabled={busy}>
              Annuler
            </button>
            <button className="btn" type="submit" disabled={busy || remaining <= 0} aria-busy={busy}>
              {busy ? 'Enregistrement…' : 'Valider le paiement'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

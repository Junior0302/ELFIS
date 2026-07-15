import { useEffect, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, downloadApiFile, formatEuro, type Invoice } from '../api'
import ConfidenceMeter from '../components/ConfidenceMeter'
import StatusBadge from '../components/StatusBadge'
import { useAuth } from '../auth'

const SOFTWARE_EXPORTS = [
  { id: 'fec', label: 'FEC' },
  { id: 'sage', label: 'Sage' },
  { id: 'pennylane', label: 'Pennylane' },
  { id: 'cegid', label: 'Cegid' },
  { id: 'ebp', label: 'EBP' },
  { id: 'odoo', label: 'Odoo' },
  { id: 'csv', label: 'CSV' },
]

function isImage(invoice: Invoice) {
  const mime = (invoice.mime_type || '').toLowerCase()
  const name = invoice.filename.toLowerCase()
  return (
    mime.startsWith('image/') ||
    name.endsWith('.jpg') ||
    name.endsWith('.jpeg') ||
    name.endsWith('.png') ||
    name.endsWith('.webp')
  )
}

export default function ResultPage() {
  const { token, orgId } = useAuth()
  const { id } = useParams()
  const invoiceId = Number(id)
  const [invoice, setInvoice] = useState<Invoice | null>(null)
  const [saving, setSaving] = useState(false)
  const [reprocessing, setReprocessing] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [previewUrl, setPreviewUrl] = useState('')

  useEffect(() => {
    if (!invoiceId || !token) return
    api
      .getDocument(invoiceId, token, orgId)
      .then(setInvoice)
      .catch((e) => setError(e.message || 'Document introuvable'))
  }, [invoiceId, token, orgId])

  useEffect(() => {
    if (!invoice?.id || !token) return
    let objectUrl = ''
    setPreviewUrl('')
    api
      .documentFile(invoice.id, token, orgId)
      .then(({ blob }) => {
        objectUrl = URL.createObjectURL(blob)
        setPreviewUrl(objectUrl)
      })
      .catch((reason) =>
        setMessage(reason instanceof Error ? reason.message : 'Aperçu indisponible'),
      )
    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [invoice?.id, token, orgId])

  const onSave = async (e: FormEvent) => {
    e.preventDefault()
    if (!invoice || !token) return
    setSaving(true)
    setMessage('')
    try {
      const updated = await api.updateDocument(invoice.id, {
        supplier: invoice.supplier,
        invoice_date: invoice.invoice_date,
        invoice_number: invoice.invoice_number,
        amount_ht: invoice.amount_ht,
        amount_tva: invoice.amount_tva,
        amount_ttc: invoice.amount_ttc,
        vat_rate: invoice.vat_rate,
        document_type: invoice.document_type,
      }, token, orgId)
      setInvoice(updated)
      setMessage('Modifications enregistrées. Écriture régénérée.')
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Erreur de sauvegarde')
    } finally {
      setSaving(false)
    }
  }

  const onReprocess = async () => {
    if (!invoice || !token) return
    setReprocessing(true)
    setMessage('')
    try {
      const updated = await api.reprocessDocument(invoice.id, token, orgId)
      setInvoice(updated)
      setMessage('Document retraité par le pipeline IA.')
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Échec du retraitement')
    } finally {
      setReprocessing(false)
    }
  }

  const download = async (path: string) => {
    if (!token) return
    setMessage('')
    try {
      await downloadApiFile(path, token, orgId)
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : 'Export impossible')
    }
  }

  if (error) return <div className="panel form-error">{error}</div>
  if (!invoice) return <div className="loading">Chargement du résultat…</div>

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Résultat</h2>
          <p>
            Module 1 · {invoice.filename} ·{' '}
            <StatusBadge needsReview={invoice.needs_review} status={invoice.status} />
          </p>
        </div>
        <Link className="btn secondary" to="/history">
          Historique
        </Link>
      </div>

      <div className="result-grid">
        <section className="panel" style={{ padding: '0.75rem' }}>
          {!previewUrl ? (
            <div className="loading">Chargement de l’aperçu…</div>
          ) : isImage(invoice) ? (
            <img className="pdf-frame" style={{ objectFit: 'contain' }} alt={invoice.filename} src={previewUrl} />
          ) : (
            <iframe className="pdf-frame" title="PDF" src={previewUrl} />
          )}
        </section>

        <section className="panel">
          <h3>Extraction IA</h3>
          <ConfidenceMeter score={invoice.confidence_score} />

          <form onSubmit={onSave}>
            <div className="form-grid" style={{ marginTop: '1rem' }}>
              <div className="field full">
                <label>Fournisseur</label>
                <input
                  value={invoice.supplier || ''}
                  onChange={(e) => setInvoice({ ...invoice, supplier: e.target.value })}
                />
              </div>
              <div className="field">
                <label>Date</label>
                <input
                  value={invoice.invoice_date || ''}
                  onChange={(e) => setInvoice({ ...invoice, invoice_date: e.target.value })}
                />
              </div>
              <div className="field">
                <label>Numéro</label>
                <input
                  value={invoice.invoice_number || ''}
                  onChange={(e) => setInvoice({ ...invoice, invoice_number: e.target.value })}
                />
              </div>
              <div className="field">
                <label>HT</label>
                <input
                  type="number"
                  step="0.01"
                  value={invoice.amount_ht ?? ''}
                  onChange={(e) =>
                    setInvoice({
                      ...invoice,
                      amount_ht: e.target.value === '' ? null : Number(e.target.value),
                    })
                  }
                />
              </div>
              <div className="field">
                <label>TVA</label>
                <input
                  type="number"
                  step="0.01"
                  value={invoice.amount_tva ?? ''}
                  onChange={(e) =>
                    setInvoice({
                      ...invoice,
                      amount_tva: e.target.value === '' ? null : Number(e.target.value),
                    })
                  }
                />
              </div>
              <div className="field">
                <label>TTC</label>
                <input
                  type="number"
                  step="0.01"
                  value={invoice.amount_ttc ?? ''}
                  onChange={(e) =>
                    setInvoice({
                      ...invoice,
                      amount_ttc: e.target.value === '' ? null : Number(e.target.value),
                    })
                  }
                />
              </div>
              <div className="field">
                <label>Taux TVA (%)</label>
                <input
                  type="number"
                  step="0.1"
                  value={invoice.vat_rate ?? ''}
                  onChange={(e) =>
                    setInvoice({
                      ...invoice,
                      vat_rate: e.target.value === '' ? null : Number(e.target.value),
                    })
                  }
                />
              </div>
              <div className="field">
                <label>Type de document</label>
                <select
                  value={invoice.document_type || 'facture'}
                  onChange={(e) => setInvoice({ ...invoice, document_type: e.target.value })}
                >
                  <option value="facture">Facture</option>
                  <option value="avoir">Avoir</option>
                  <option value="devis">Devis</option>
                  <option value="ticket">Ticket</option>
                  <option value="note_frais">Note de frais</option>
                  <option value="releve">Relevé</option>
                  <option value="autre">Autre</option>
                </select>
              </div>
            </div>

            {(invoice.anomalies.length > 0 || invoice.missing_fields.length > 0) && (
              <div style={{ marginTop: '1rem' }}>
                <strong>Contrôles / incohérences</strong>
                <ul className="alert-list">
                  {invoice.anomalies.map((a) => (
                    <li key={a}>{a}</li>
                  ))}
                  {invoice.missing_fields.map((m) => (
                    <li key={m}>Champ manquant : {m}</li>
                  ))}
                </ul>
              </div>
            )}

            {invoice.accounting_entry && (
              <div style={{ marginTop: '1.1rem' }}>
                <strong>Imputation & écriture</strong>
                {invoice.accounting_entry.imputation && (
                  <p className="muted" style={{ margin: '0.35rem 0' }}>
                    Proposition : {invoice.accounting_entry.imputation}
                  </p>
                )}
                <p className="muted" style={{ margin: '0.35rem 0' }}>
                  {invoice.accounting_entry.label}
                </p>
                <p className="muted" style={{ margin: 0 }}>
                  {invoice.accounting_entry.explanation}
                </p>
                {invoice.accounting_entry.lines.length > 0 ? (
                  <table className="entry-table">
                    <thead>
                      <tr>
                        <th>Compte</th>
                        <th>Libellé</th>
                        <th>Débit</th>
                        <th>Crédit</th>
                      </tr>
                    </thead>
                    <tbody>
                      {invoice.accounting_entry.lines.map((line, idx) => (
                        <tr key={`${line.account}-${idx}`}>
                          <td>{line.account}</td>
                          <td>{line.label}</td>
                          <td>{formatEuro(line.debit)}</td>
                          <td>{formatEuro(line.credit)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <p className="muted">Aucune ligne d’écriture pour ce type de document.</p>
                )}
              </div>
            )}

            <div className="actions">
              <button className="btn" type="submit" disabled={saving}>
                {saving ? 'Enregistrement…' : 'Enregistrer'}
              </button>
              <button className="btn secondary" type="button" onClick={onReprocess} disabled={reprocessing}>
                {reprocessing ? 'Retraitement…' : 'Relancer l’IA'}
              </button>
              <button
                className="btn secondary"
                type="button"
                onClick={() => void download(`/exports/${invoice.id}/excel`)}
              >
                Excel
              </button>
              <button
                className="btn secondary"
                type="button"
                onClick={() => void download(`/exports/${invoice.id}/pdf`)}
              >
                PDF
              </button>
            </div>

            <div className="export-block">
              <strong>Exports logiciels comptables</strong>
              <div className="actions">
                {SOFTWARE_EXPORTS.map((item) => (
                  <button
                    key={item.id}
                    className="btn secondary"
                    type="button"
                    onClick={() => void download(`/exports/${invoice.id}/${item.id}`)}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>

            {message && <p className="muted">{message}</p>}
          </form>
        </section>
      </div>
    </>
  )
}

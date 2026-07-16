import { useEffect, useState, type FormEvent } from 'react'
import { api, type DocumentEmailLog, type SalesDoc } from '../api'

type Props = {
  doc: SalesDoc
  token: string
  orgId: number
  onClose: () => void
  onEdit: (doc: SalesDoc) => void
  onSent: (doc: SalesDoc, log: DocumentEmailLog) => void
}

export default function SalesDocPreviewModal({
  doc,
  token,
  orgId,
  onClose,
  onEdit,
  onSent,
}: Props) {
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [loadingPdf, setLoadingPdf] = useState(true)
  const [error, setError] = useState('')
  const [sending, setSending] = useState(false)
  const [recipient, setRecipient] = useState(doc.customer_email || '')
  const [message, setMessage] = useState(
    `Bonjour,\n\nVeuillez trouver ci-joint votre ${
      doc.doc_type === 'devis' ? 'devis' : 'facture'
    } ${doc.number}.\n\nCordialement`,
  )
  const [logs, setLogs] = useState<DocumentEmailLog[]>([])

  useEffect(() => {
    let objectUrl: string | null = null
    let cancelled = false
    setLoadingPdf(true)
    setError('')
    api
      .openSalesDocPdfBlob(doc.id, token, orgId)
      .then((url) => {
        if (cancelled) {
          URL.revokeObjectURL(url)
          return
        }
        objectUrl = url
        setPdfUrl(url)
      })
      .catch((reason) => {
        if (!cancelled) setError(reason instanceof Error ? reason.message : 'PDF indisponible')
      })
      .finally(() => {
        if (!cancelled) setLoadingPdf(false)
      })
    api
      .salesDocEmails(doc.id, token, orgId)
      .then((data) => {
        if (!cancelled) setLogs(data.email_logs)
      })
      .catch(() => undefined)
    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [doc.id, token, orgId])

  const download = async () => {
    try {
      await api.downloadSalesDocPdf(doc.id, token, orgId)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Téléchargement impossible')
    }
  }

  const send = async (e: FormEvent) => {
    e.preventDefault()
    setSending(true)
    setError('')
    try {
      const result = await api.emailSalesDoc(
        doc.id,
        { recipient, message },
        token,
        orgId,
      )
      setLogs((current) => [result.email_log, ...current])
      onSent(result.document, result.email_log)
      if (result.email_log.status !== 'sent') {
        setError(
          result.email_log.error_message ||
            (result.smtp_configured
              ? 'Envoi échoué'
              : 'SMTP non configuré — configurez SMTP_HOST / SMTP_FROM côté serveur.'),
        )
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Envoi impossible')
    } finally {
      setSending(false)
    }
  }

  const label = doc.doc_type === 'devis' ? 'Devis' : doc.doc_type === 'avoir' ? 'Avoir' : 'Facture'
  const statusLabel = (status: string) =>
    status === 'sent' ? 'Envoyé' : status === 'failed' ? 'Échec' : 'En attente'

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label={`Aperçu ${doc.number}`}>
      <div className="modal-panel sales-preview-modal">
        <div className="modal-head">
          <div>
            <h3>
              {label} {doc.number}
            </h3>
            <p className="muted">
              {doc.customer_name}
              {doc.customer_email ? ` · ${doc.customer_email}` : ''} · {doc.status}
            </p>
          </div>
          <button className="btn secondary" type="button" onClick={onClose}>
            Fermer
          </button>
        </div>

        <div className="sales-preview-grid">
          <div className="sales-preview-pdf">
            {loadingPdf && <p className="muted">Chargement de l’aperçu PDF…</p>}
            {!loadingPdf && pdfUrl && (
              <iframe title={`PDF ${doc.number}`} src={pdfUrl} />
            )}
            {!loadingPdf && !pdfUrl && <p className="form-error">Aperçu PDF indisponible.</p>}
          </div>

          <div className="sales-preview-side">
            <div className="actions" style={{ marginTop: 0, flexWrap: 'wrap' }}>
              <button className="btn secondary" type="button" onClick={() => onEdit(doc)}>
                Modifier
              </button>
              <button className="btn secondary" type="button" onClick={() => void download()}>
                Télécharger
              </button>
            </div>

            <form onSubmit={send}>
              <h4>Envoyer au client</h4>
              <div className="field">
                <label>Adresse e-mail</label>
                <input
                  type="email"
                  required
                  value={recipient}
                  onChange={(e) => setRecipient(e.target.value)}
                  placeholder="client@exemple.fr"
                />
              </div>
              <div className="field">
                <label>Message</label>
                <textarea
                  rows={6}
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                />
              </div>
              <p className="muted" style={{ marginTop: 0 }}>
                Objet : {label} n°{doc.number} · PDF joint automatiquement
              </p>
              <button className="btn" type="submit" disabled={sending}>
                {sending ? 'Envoi…' : 'Envoyer au client'}
              </button>
            </form>

            {error && <p className="form-error">{error}</p>}

            <section>
              <h4>Historique des envois</h4>
              {logs.length === 0 ? (
                <p className="muted">Aucun envoi pour ce document.</p>
              ) : (
                <div className="list">
                  {logs.map((log) => (
                    <div key={log.id} className="list-item" style={{ gridTemplateColumns: '1fr auto' }}>
                      <div>
                        <strong>{log.recipient || '—'}</strong>
                        <span>
                          {new Date(log.sent_at).toLocaleString('fr-FR')} · {log.subject}
                          {log.error_message ? ` · ${log.error_message}` : ''}
                        </span>
                      </div>
                      <span className={`badge ${log.status === 'sent' ? '' : 'warn'}`}>
                        {statusLabel(log.status)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </div>
        </div>
      </div>
    </div>
  )
}

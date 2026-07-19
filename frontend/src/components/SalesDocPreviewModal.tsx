import { useEffect, useRef, useState, type FormEvent } from 'react'
import {
  api,
  type DocumentEmailLog,
  type EmailConnection,
  type EmailSendPreview,
  type SalesDoc,
} from '../api'
import { useAuth } from '../auth'

type Props = {
  doc: SalesDoc
  token: string
  orgId: number
  onClose: () => void
  onEdit: (doc: SalesDoc) => void
  onSent: (doc: SalesDoc, log: DocumentEmailLog) => void
}

function statusLabel(status: string) {
  const map: Record<string, string> = {
    preparing: 'Préparation',
    queued: 'En file',
    sent: 'Envoyé',
    delivered: 'Distribué',
    opened: 'Ouvert',
    bounced: 'Rebond',
    blocked: 'Bloqué',
    failed: 'Échec',
  }
  return map[status] || status
}

export default function SalesDocPreviewModal({
  doc,
  token,
  orgId,
  onClose,
  onEdit,
  onSent,
}: Props) {
  const { user } = useAuth()
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [loadingPdf, setLoadingPdf] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [sending, setSending] = useState(false)
  const [recipient, setRecipient] = useState(doc.customer_email || '')
  const [cc, setCc] = useState('')
  const [bcc, setBcc] = useState('')
  const [subject, setSubject] = useState('')
  const [message, setMessage] = useState('')
  const [preview, setPreview] = useState<EmailSendPreview | null>(null)
  const [logs, setLogs] = useState<DocumentEmailLog[]>([])
  const [connections, setConnections] = useState<EmailConnection[]>([])
  const [connectionId, setConnectionId] = useState<number | null>(null)
  const [emailReady, setEmailReady] = useState(true)
  const [fromEmail, setFromEmail] = useState('')
  const sendingLock = useRef(false)
  const idempotencyRef = useRef(`send-${doc.id}-${Date.now()}`)

  const accountEmail = (preview?.user_email || user?.email || '').trim()
  const orgEmail = (preview?.org_email || '').trim()
  const replyTo = (fromEmail || accountEmail || orgEmail || preview?.reply_to_email || '').trim()

  useEffect(() => {
    let objectUrl: string | null = null
    let cancelled = false
    setLoadingPdf(true)
    setError('')
    setSuccess('')
    idempotencyRef.current = `send-${doc.id}-${Date.now()}`
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
        if (cancelled) return
        setLogs(data.email_logs)
        setConnections(data.connections || [])
        setEmailReady(
          Boolean(data.can_send_direct || data.email_configured || data.smtp_configured),
        )
        setConnectionId(data.default_connection_id ?? data.preview?.connection_id ?? null)
        if (data.preview) {
          setPreview(data.preview)
          setRecipient(data.preview.recipient || doc.customer_email || '')
          setCc(data.preview.cc || '')
          setBcc(data.preview.bcc || '')
          setSubject(data.preview.subject || '')
          setMessage(data.preview.message || '')
          setFromEmail(
            data.preview.reply_to_email ||
              data.preview.org_email ||
              data.preview.user_email ||
              '',
          )
        }
      })
      .catch(() => undefined)
    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [doc.id, doc.customer_email, token, orgId])

  const download = async () => {
    try {
      await api.downloadSalesDocPdf(doc.id, token, orgId)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Téléchargement impossible')
    }
  }

  const refreshLogs = async () => {
    try {
      const data = await api.salesDocEmails(doc.id, token, orgId)
      setLogs(data.email_logs)
      setEmailReady(Boolean(data.can_send_direct || data.email_configured || data.smtp_configured))
    } catch {
      /* ignore */
    }
  }

  /** Envoi réel côté serveur — le PDF est joint automatiquement (jamais de mailto). */
  const sendDirect = async () => {
    if (sendingLock.current) return
    if (!recipient.trim()) {
      setError('Indiquez le destinataire.')
      return
    }
    if (!replyTo) {
      setError(
        'Indiquez une adresse de réponse (e-mail de votre entreprise) avant l’envoi.',
      )
      return
    }
    sendingLock.current = true
    setSending(true)
    setError('')
    setSuccess('')
    try {
      const result = await api.emailSalesDoc(
        doc.id,
        {
          recipient: recipient.trim(),
          message,
          subject,
          cc: cc.trim() || undefined,
          bcc: bcc.trim() || undefined,
          send_mode: 'server',
          connection_id: connectionId,
          preferred_from_email: replyTo,
          preferred_from_label: replyTo,
          idempotency_key: `${idempotencyRef.current}-server`,
        },
        token,
        orgId,
      )
      setLogs((current) => [result.email_log, ...current])
      if (result.can_send_direct === false && result.smtp_configured === false) {
        setEmailReady(false)
      }
      if (result.email_log.status === 'failed' || result.email_log.status === 'blocked') {
        const detail = (result.email_log.error_message || '').trim()
        const code = (result.email_log.error_code || '').trim()
        setError(
          detail ||
            (code
              ? `Échec d’envoi (${code}).`
              : 'L’e-mail n’a pas pu être envoyé. Aucun message n’a été remis au destinataire.'),
        )
        return
      }
      onSent(result.document, result.email_log)
      idempotencyRef.current = `send-${doc.id}-${Date.now()}`
      const pdfName = preview?.pdf_filename || `${doc.number}.pdf`
      setSuccess(
        `E-mail envoyé à ${result.email_log.recipient_email || recipient} avec la pièce jointe ${pdfName}. Aucun téléchargement sur votre PC n’est nécessaire.`,
      )
      await refreshLogs()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Envoi impossible')
    } finally {
      setSending(false)
      sendingLock.current = false
    }
  }

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    void sendDirect()
  }

  const label = doc.doc_type === 'devis' ? 'Devis' : doc.doc_type === 'avoir' ? 'Avoir' : 'Facture'
  const pdfName = preview?.pdf_filename || `${label}-${doc.number}.pdf`
  const senderDisplay =
    preview?.sender_email ||
    connections.find((c) => c.id === connectionId)?.email_address ||
    'ComptaPilot'

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
            {!loadingPdf && pdfUrl && <iframe title={`PDF ${doc.number}`} src={pdfUrl} />}
            {!loadingPdf && !pdfUrl && <p className="form-error">Aperçu PDF indisponible.</p>}
          </div>

          <div className="sales-preview-side">
            <div className="actions" style={{ marginTop: 0, flexWrap: 'wrap' }}>
              <button className="btn secondary" type="button" onClick={() => onEdit(doc)}>
                Modifier
              </button>
              <button className="btn secondary" type="button" onClick={() => void download()}>
                Télécharger le PDF
              </button>
            </div>

            <form className="mailto-send-panel document-email-panel" onSubmit={onSubmit}>
              <header className="mailto-send-head">
                <h4>Envoyer au client</h4>
                <p>
                  Un clic sur <strong>Envoyer maintenant</strong> envoie l’e-mail depuis ComptaPilot
                  avec le <strong>PDF joint automatiquement</strong>. Pas besoin d’ouvrir Outlook ni
                  de joindre le fichier à la main.
                </p>
              </header>

              <div className="mailto-recap" aria-label="Pièce jointe automatique">
                <div>
                  <span>Expéditeur</span>
                  <strong>{senderDisplay}</strong>
                </div>
                <div>
                  <span>À</span>
                  <strong>{recipient || '—'}</strong>
                </div>
                <div>
                  <span>Pièce jointe</span>
                  <strong>{pdfName} · jointe automatiquement</strong>
                </div>
              </div>

              {!emailReady && (
                <p className="form-error" role="status">
                  Le service d’envoi serveur n’est pas détecté. Vérifiez la configuration e-mail
                  (Brevo/SMTP) puis réessayez. Le téléchargement manuel reste disponible ci-dessus.
                </p>
              )}

              {connections.length > 1 && (
                <div className="field">
                  <label>Boîte d’envoi</label>
                  <select
                    value={connectionId ?? ''}
                    onChange={(e) =>
                      setConnectionId(e.target.value ? Number(e.target.value) : null)
                    }
                  >
                    {connections.map((conn) => (
                      <option key={conn.id} value={conn.id}>
                        {conn.display_name || conn.email_address} ({conn.provider})
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <div className="field">
                <label>Réponse à (Reply-To)</label>
                <input
                  type="email"
                  required
                  value={fromEmail}
                  onChange={(e) => setFromEmail(e.target.value)}
                  placeholder="contact@entreprise.fr"
                />
              </div>

              <div className="field">
                <label>Destinataire</label>
                <input
                  type="email"
                  required
                  value={recipient}
                  onChange={(e) => setRecipient(e.target.value)}
                  placeholder="client@exemple.fr"
                />
              </div>

              <div className="field">
                <label>Copie (CC)</label>
                <input
                  type="email"
                  value={cc}
                  onChange={(e) => setCc(e.target.value)}
                  placeholder="optionnel"
                />
              </div>

              <div className="field">
                <label>Objet</label>
                <input value={subject} onChange={(e) => setSubject(e.target.value)} required />
              </div>

              <div className="field">
                <label>Message</label>
                <textarea rows={6} value={message} onChange={(e) => setMessage(e.target.value)} />
              </div>

              <div className="actions" style={{ flexWrap: 'wrap' }}>
                <button className="btn secondary" type="button" onClick={onClose} disabled={sending}>
                  Annuler
                </button>
                <button className="btn" type="submit" disabled={sending || !recipient.trim()}>
                  {sending ? 'Envoi en cours…' : 'Envoyer maintenant'}
                </button>
              </div>
            </form>

            {error && <p className="form-error">{error}</p>}
            {success && (
              <p className="mailto-hint" role="status">
                {success}
              </p>
            )}

            <section className="mailto-history">
              <h4>Historique d’activité</h4>
              {logs.length === 0 ? (
                <p className="muted">Aucun envoi pour ce document.</p>
              ) : (
                <div className="list">
                  {logs.map((log) => (
                    <div key={log.id} className="list-item" style={{ gridTemplateColumns: '1fr auto' }}>
                      <div>
                        <strong>{log.recipient_email || log.recipient || '—'}</strong>
                        <span>
                          {log.sender_email ? `De ${log.sender_email} · ` : ''}
                          {new Date(log.sent_at).toLocaleString('fr-FR')}
                          {log.provider === 'mailto'
                            ? ' · Messagerie (manuel)'
                            : log.provider
                              ? ` · ${log.provider}`
                              : ''}
                        </span>
                        {log.error_message ? (
                          <span className="muted"> · {log.error_message}</span>
                        ) : null}
                      </div>
                      <span
                        className={`badge ${
                          log.status === 'sent' ||
                          log.status === 'delivered' ||
                          log.status === 'opened'
                            ? ''
                            : 'warn'
                        }`}
                      >
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

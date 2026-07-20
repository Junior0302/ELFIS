import { useEffect, useRef, useState, type FormEvent } from 'react'
import { api, type DocumentEmailLog, type EmailSendPreview, type SalesDoc } from '../api'
import { useAuth } from '../auth'

type Props = {
  doc: SalesDoc
  token: string
  orgId: number
  onClose: () => void
  onEdit: (doc: SalesDoc) => void
  onSent: (doc: SalesDoc, log: DocumentEmailLog) => void
}

type SendPhase = 'idle' | 'prepare' | 'archive' | 'send' | 'done'

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
    already_sent: 'Déjà envoyé',
    email_failed: 'Échec e-mail',
  }
  return map[status] || status
}

function phaseLabel(phase: SendPhase) {
  switch (phase) {
    case 'prepare':
      return 'Préparation du document…'
    case 'archive':
      return 'Archivage sécurisé…'
    case 'send':
      return 'Envoi de l’e-mail…'
    case 'done':
      return 'Terminé'
    default:
      return ''
  }
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
  const [sending, setSending] = useState(false)
  const [phase, setPhase] = useState<SendPhase>('idle')
  const [recipient, setRecipient] = useState(doc.customer_email || '')
  const [cc, setCc] = useState('')
  const [bcc, setBcc] = useState('')
  const [subject, setSubject] = useState('')
  const [message, setMessage] = useState('')
  const [preview, setPreview] = useState<EmailSendPreview | null>(null)
  const [logs, setLogs] = useState<DocumentEmailLog[]>([])
  const [hint, setHint] = useState('')
  const [canSendDirect, setCanSendDirect] = useState(false)
  const sendingLock = useRef(false)
  const idempotencyRef = useRef(`send-${doc.id}-${Date.now()}`)

  useEffect(() => {
    let objectUrl: string | null = null
    let cancelled = false
    setLoadingPdf(true)
    setError('')
    setHint('')
    setPhase('idle')
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
        setCanSendDirect(Boolean(data.can_send_direct ?? data.email_configured))
        if (data.preview) {
          setPreview(data.preview)
          setRecipient(data.preview.recipient || doc.customer_email || '')
          setCc(data.preview.cc || '')
          setBcc(data.preview.bcc || '')
          setSubject(data.preview.subject || '')
          setMessage(data.preview.message || '')
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

  const sendServer = async () => {
    if (sendingLock.current) return
    if (!recipient.trim()) {
      setError('Indiquez le destinataire.')
      return
    }
    sendingLock.current = true
    setSending(true)
    setError('')
    setHint('')
    setPhase('prepare')
    const prepareTimer = window.setTimeout(() => setPhase('archive'), 400)
    const archiveTimer = window.setTimeout(() => setPhase('send'), 900)
    try {
      const result = await api.emailSalesDoc(
        doc.id,
        {
          recipient,
          message,
          subject,
          cc,
          bcc,
          send_mode: 'server',
          preferred_from_email: (user?.email || '').trim() || undefined,
          preferred_from_label: (user?.email || '').trim() || undefined,
          idempotency_key: idempotencyRef.current,
        },
        token,
        orgId,
      )
      window.clearTimeout(prepareTimer)
      window.clearTimeout(archiveTimer)
      setPhase('done')
      if (result.email_log) {
        setLogs((current) => [result.email_log!, ...current])
        onSent(result.document, result.email_log)
      } else {
        onSent(result.document, {
          id: 0,
          sales_document_id: doc.id,
          recipient,
          recipient_email: recipient,
          subject,
          status: result.status || 'sent',
          sent_at: result.sent_at || new Date().toISOString(),
          provider: 'server',
          error_message: '',
        } as DocumentEmailLog)
      }
      idempotencyRef.current = `send-${doc.id}-${Date.now()}`

      if (result.status === 'email_failed' || result.email_status === 'failed') {
        setHint(
          result.message ||
            'Le document a été archivé, mais l’e-mail n’a pas pu être envoyé. Vous pourrez réessayer sans recréer la facture.',
        )
      } else if (result.already_processed || result.status === 'already_sent') {
        setHint(result.message || 'Cet envoi a déjà été traité.')
      } else {
        setHint(
          result.vault_document_id
            ? `E-mail envoyé avec le PDF en pièce jointe. Archivé dans ELFIS Vault (${result.vault_document_id}).`
            : 'E-mail envoyé avec le PDF en pièce jointe.',
        )
      }
    } catch (reason) {
      window.clearTimeout(prepareTimer)
      window.clearTimeout(archiveTimer)
      setPhase('idle')
      const msg = reason instanceof Error ? reason.message : 'Envoi impossible'
      if (msg.toLowerCase().includes('archivé') || msg.toLowerCase().includes('archive')) {
        setError(msg)
      } else if (msg.toLowerCase().includes('stockage') || msg.toLowerCase().includes('503')) {
        setError('Le document n’a pas pu être archivé. L’e-mail n’a pas été envoyé.')
      } else {
        setError(msg)
      }
    } finally {
      setSending(false)
      sendingLock.current = false
    }
  }

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    void sendServer()
  }

  const label = doc.doc_type === 'devis' ? 'Devis' : doc.doc_type === 'avoir' ? 'Avoir' : 'Facture'
  const pdfName = preview?.pdf_filename || `${label}-${doc.number}.pdf`

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

            <form className="mailto-send-panel" onSubmit={onSubmit}>
              <header className="mailto-send-head">
                <h4>Envoyer au client</h4>
                <p>
                  Le PDF est archivé dans ELFIS Vault puis joint automatiquement à l’e-mail — sans
                  téléchargement manuel.
                </p>
              </header>

              {!canSendDirect && (
                <p className="form-error">
                  L’envoi serveur n’est pas configuré (SMTP / Brevo). Contactez l’administrateur
                  plateforme.
                </p>
              )}

              <div className="field">
                <label>Destinataire</label>
                <input
                  type="email"
                  required
                  value={recipient}
                  onChange={(e) => setRecipient(e.target.value)}
                  placeholder="client@exemple.fr"
                  disabled={sending}
                />
              </div>

              <div className="mailto-recap" aria-label="Récapitulatif">
                <div>
                  <span>À</span>
                  <strong>{recipient || '—'}</strong>
                </div>
                <div>
                  <span>Pièce jointe</span>
                  <strong>{pdfName}</strong>
                </div>
                <div>
                  <span>Coffre</span>
                  <strong>ELFIS Vault</strong>
                </div>
              </div>

              <div className="field">
                <label>Copie (CC)</label>
                <input
                  type="email"
                  value={cc}
                  onChange={(e) => setCc(e.target.value)}
                  placeholder="optionnel"
                  disabled={sending}
                />
              </div>
              <div className="field">
                <label>Objet</label>
                <input
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  required
                  disabled={sending}
                />
              </div>
              <div className="field">
                <label>Message</label>
                <textarea
                  rows={6}
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  disabled={sending}
                />
              </div>

              {sending && phase !== 'idle' && (
                <p className="muted" role="status">
                  {phaseLabel(phase)}
                </p>
              )}

              <div className="actions" style={{ flexWrap: 'wrap' }}>
                <button className="btn secondary" type="button" onClick={onClose} disabled={sending}>
                  Annuler
                </button>
                <button className="btn" type="submit" disabled={sending || !canSendDirect || !recipient.trim()}>
                  {sending ? phaseLabel(phase) || 'Envoi…' : 'Envoyer maintenant'}
                </button>
              </div>
            </form>

            {error && <p className="form-error">{error}</p>}
            {hint && (
              <p className="mailto-hint" role="status">
                {hint}
              </p>
            )}

            <section className="mailto-history">
              <h4>Historique</h4>
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
                          {log.provider ? ` · ${log.provider}` : ''}
                        </span>
                      </div>
                      <span
                        className={`badge ${
                          log.status === 'sent' || log.status === 'delivered' || log.status === 'opened'
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

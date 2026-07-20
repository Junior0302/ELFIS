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

function buildMailtoUrl(opts: {
  to: string
  subject: string
  body: string
  cc?: string
  bcc?: string
}) {
  const parts: string[] = []
  if (opts.subject) parts.push(`subject=${encodeURIComponent(opts.subject)}`)
  if (opts.body) parts.push(`body=${encodeURIComponent(opts.body)}`)
  if (opts.cc) parts.push(`cc=${encodeURIComponent(opts.cc)}`)
  if (opts.bcc) parts.push(`bcc=${encodeURIComponent(opts.bcc)}`)
  const to = opts.to.trim()
  return `mailto:${to}${parts.length ? `?${parts.join('&')}` : ''}`
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
  const [recipient, setRecipient] = useState(doc.customer_email || '')
  const [cc, setCc] = useState('')
  const [bcc, setBcc] = useState('')
  const [subject, setSubject] = useState('')
  const [message, setMessage] = useState('')
  const [preview, setPreview] = useState<EmailSendPreview | null>(null)
  const [logs, setLogs] = useState<DocumentEmailLog[]>([])
  const [hint, setHint] = useState('')
  const [fromEmail, setFromEmail] = useState('')
  const sendingLock = useRef(false)
  const idempotencyRef = useRef(`send-${doc.id}-${Date.now()}`)

  const accountEmail = (preview?.user_email || user?.email || '').trim()
  const orgEmail = (preview?.org_email || '').trim()
  const effectiveFrom = (fromEmail || accountEmail || orgEmail).trim()

  useEffect(() => {
    let objectUrl: string | null = null
    let cancelled = false
    setLoadingPdf(true)
    setError('')
    setHint('')
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
        if (data.preview) {
          setPreview(data.preview)
          setRecipient(data.preview.recipient || doc.customer_email || '')
          setCc(data.preview.cc || '')
          setBcc(data.preview.bcc || '')
          setSubject(data.preview.subject || '')
          setMessage(data.preview.message || '')
          setFromEmail(data.preview.user_email || data.preview.org_email || '')
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

  const openMailbox = async () => {
    if (sendingLock.current) return
    if (!effectiveFrom) {
      setError('Indiquez votre adresse e-mail (celle depuis laquelle vous enverrez).')
      return
    }
    if (!recipient.trim()) {
      setError('Indiquez le destinataire.')
      return
    }
    sendingLock.current = true
    setSending(true)
    setError('')
    setHint('')
    try {
      await api.downloadSalesDocPdf(doc.id, token, orgId)
      const result = await api.emailSalesDoc(
        doc.id,
        {
          recipient,
          message,
          subject,
          cc,
          bcc,
          send_mode: 'mailto',
          sender_acknowledged: true,
          preferred_from_email: effectiveFrom,
          preferred_from_label: effectiveFrom,
          idempotency_key: `${idempotencyRef.current}-mailto`,
        },
        token,
        orgId,
      )
      setLogs((current) => [result.email_log, ...current])
      onSent(result.document, result.email_log)
      idempotencyRef.current = `send-${doc.id}-${Date.now()}`
      const pdfName = preview?.pdf_filename || `${doc.number}.pdf`
      const bodyWithAttachmentHint =
        `${message.trim()}\n\n` +
        `—\nJoignez le fichier PDF téléchargé : ${pdfName}\n`
      window.location.href = buildMailtoUrl({
        to: recipient.trim(),
        subject: subject.trim() || result.email_log.subject,
        body: bodyWithAttachmentHint,
        cc: cc.trim() || undefined,
        bcc: bcc.trim() || undefined,
      })
      setHint(
        `PDF téléchargé et messagerie ouverte. Joignez le fichier, vérifiez l’expéditeur (${effectiveFrom}), puis envoyez.`,
      )
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible d’ouvrir la messagerie')
    } finally {
      setSending(false)
      sendingLock.current = false
    }
  }

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    void openMailbox()
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
                  L’e-mail part depuis <strong>votre messagerie</strong> (Gmail, Outlook, Mail…). Vous
                  restez l’expéditeur réel — aucune boîte interne ELFIS.
                </p>
              </header>

              <ol className="mailto-steps" aria-label="Étapes d’envoi">
                <li>
                  <span className="mailto-step-num">1</span>
                  <span>On prépare le message et télécharge le PDF</span>
                </li>
                <li>
                  <span className="mailto-step-num">2</span>
                  <span>Votre messagerie s’ouvre avec destinataire, objet et texte</span>
                </li>
                <li>
                  <span className="mailto-step-num">3</span>
                  <span>Vous joignez le PDF et cliquez Envoyer</span>
                </li>
              </ol>

              <div className="field">
                <label>Vous envoyez depuis</label>
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

              <div className="mailto-recap" aria-label="Récapitulatif">
                <div>
                  <span>De</span>
                  <strong>{effectiveFrom || '—'}</strong>
                </div>
                <div>
                  <span>À</span>
                  <strong>{recipient || '—'}</strong>
                </div>
                <div>
                  <span>Pièce jointe</span>
                  <strong>{pdfName}</strong>
                </div>
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
                <button className="btn" type="submit" disabled={sending || !effectiveFrom}>
                  {sending ? 'Préparation…' : 'Ouvrir ma messagerie'}
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
                          {log.provider === 'mailto' ? ' · Messagerie' : log.provider ? ` · ${log.provider}` : ''}
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

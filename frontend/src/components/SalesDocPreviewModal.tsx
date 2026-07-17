import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import {
  api,
  type DocumentEmailLog,
  type EmailSendPreview,
  type EmailSenderOption,
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

function buildMailtoUrl(opts: {
  to: string
  subject: string
  body: string
  cc?: string
  bcc?: string
}) {
  const params = new URLSearchParams()
  if (opts.subject) params.set('subject', opts.subject)
  if (opts.body) params.set('body', opts.body)
  if (opts.cc) params.set('cc', opts.cc)
  if (opts.bcc) params.set('bcc', opts.bcc)
  const qs = params.toString()
  return `mailto:${encodeURIComponent(opts.to)}${qs ? `?${qs}` : ''}`
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
  const [canSendDirect, setCanSendDirect] = useState(false)
  const [connectionId, setConnectionId] = useState<number | null>(null)
  const [recipient, setRecipient] = useState(doc.customer_email || '')
  const [cc, setCc] = useState('')
  const [bcc, setBcc] = useState('')
  const [subject, setSubject] = useState('')
  const [message, setMessage] = useState('')
  const [preview, setPreview] = useState<EmailSendPreview | null>(null)
  const [logs, setLogs] = useState<DocumentEmailLog[]>([])
  const [ackSender, setAckSender] = useState(false)
  const [hint, setHint] = useState('')
  const [senderOptions, setSenderOptions] = useState<EmailSenderOption[]>([])
  const [senderOptionId, setSenderOptionId] = useState<string>('')
  const sendingLock = useRef(false)
  const idempotencyRef = useRef(`send-${doc.id}-${Date.now()}`)

  const selectedSender = senderOptions.find((o) => o.id === senderOptionId) || null
  const replyToEmail = (
    selectedSender?.email ||
    preview?.reply_to_email ||
    preview?.org_email ||
    preview?.user_email ||
    user?.email ||
    ''
  ).trim()
  const displayFrom = selectedSender
    ? selectedSender.label
    : preview?.sender_name && preview?.sender_email
      ? `${preview.sender_name} <${preview.sender_email}>`
      : preview?.sender_email || 'ComptaPilot'
  const mailboxFrom = (selectedSender?.email || preview?.user_email || user?.email || replyToEmail).trim()

  useEffect(() => {
    let objectUrl: string | null = null
    let cancelled = false
    setLoadingPdf(true)
    setError('')
    setAckSender(false)
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
        setCanSendDirect(Boolean(data.can_send_direct ?? data.email_configured ?? data.smtp_configured))
        if (data.default_connection_id) setConnectionId(data.default_connection_id)
        if (data.preview) {
          setPreview(data.preview)
          setRecipient(data.preview.recipient || doc.customer_email || '')
          setCc(data.preview.cc || '')
          setBcc(data.preview.bcc || '')
          setSubject(data.preview.subject || '')
          setMessage(data.preview.message || '')
          if (data.preview.connection_id) setConnectionId(data.preview.connection_id)
        }
      })
      .catch(() => undefined)
    api
      .professionalSenderOptions(token, orgId)
      .then((data) => {
        if (cancelled) return
        setSenderOptions(data.options)
        setSenderOptionId(data.default_option_id || data.options[0]?.id || '')
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

  const sendDirect = async () => {
    if (sendingLock.current) return
    if (!canSendDirect) {
      setError(
        'Envoi direct non activé. Ajoutez BREVO_API_KEY + PLATFORM_EMAIL_FROM sur le serveur, ou utilisez « Ouvrir ma messagerie ».',
      )
      return
    }
    if (!ackSender) {
      setError('Cochez la case pour confirmer l’adresse de réponse (votre e-mail).')
      return
    }
    if (!recipient.trim()) {
      setError('Indiquez l’adresse du client.')
      return
    }
    sendingLock.current = true
    setSending(true)
    setError('')
    setHint('')
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
          sender_acknowledged: true,
          connection_id: connectionId,
          preferred_from_email: selectedSender?.email || replyToEmail || undefined,
          preferred_from_label: selectedSender?.label || undefined,
          idempotency_key: `${idempotencyRef.current}-direct`,
        },
        token,
        orgId,
      )
      setLogs((current) => [result.email_log, ...current])
      setCanSendDirect(Boolean(result.can_send_direct ?? result.email_configured ?? result.smtp_configured))
      onSent(result.document, result.email_log)
      if (result.email_log.status === 'sent' || result.email_log.status === 'delivered') {
        idempotencyRef.current = `send-${doc.id}-${Date.now()}`
        setHint(`E-mail envoyé au client. Les réponses iront sur ${replyToEmail || 'votre adresse'}.`)
      } else {
        setError(result.email_log.error_message || 'Envoi échoué')
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Envoi impossible')
    } finally {
      setSending(false)
      sendingLock.current = false
    }
  }

  const openInMailbox = async () => {
    if (sendingLock.current) return
    if (!ackSender) {
      setError('Cochez la case pour confirmer que l’expéditeur sera votre adresse e-mail.')
      return
    }
    if (!recipient.trim()) {
      setError('Indiquez l’adresse du client.')
      return
    }
    if (!mailboxFrom) {
      setError('Renseignez votre e-mail de compte ou celui de l’entreprise dans Paramètres.')
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
          preferred_from_email: selectedSender?.email || mailboxFrom || undefined,
          preferred_from_label: selectedSender?.label || undefined,
          idempotency_key: `${idempotencyRef.current}-mailto`,
        },
        token,
        orgId,
      )
      setLogs((current) => [result.email_log, ...current])
      onSent(result.document, result.email_log)
      idempotencyRef.current = `send-${doc.id}-${Date.now()}`
      const bodyWithAttachmentHint =
        `${message.trim()}\n\n` +
        `—\nJoignez le fichier PDF téléchargé : ${preview?.pdf_filename || `${doc.number}.pdf`}\n`
      window.location.href = buildMailtoUrl({
        to: recipient.trim(),
        subject: subject.trim() || result.email_log.subject,
        body: bodyWithAttachmentHint,
        cc: cc.trim() || undefined,
        bcc: bcc.trim() || undefined,
      })
      setHint(`Messagerie ouverte. Expéditeur : ${mailboxFrom}. Joignez le PDF puis envoyez.`)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible d’ouvrir la messagerie')
    } finally {
      setSending(false)
      sendingLock.current = false
    }
  }

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (canSendDirect) void sendDirect()
    else void openInMailbox()
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

            <form onSubmit={onSubmit}>
              <h4>Envoyer au client</h4>

              {canSendDirect ? (
                <div className="email-sender-notice" role="status">
                  <strong>Envoi direct activé</strong>
                  <p>
                    ComptaPilot enverra l’e-mail <em>automatiquement</em> au client, avec le PDF joint.
                  </p>
                  <p>
                    Les réponses du client arriveront sur <strong>{replyToEmail || 'votre e-mail entreprise'}</strong>.
                  </p>
                </div>
              ) : (
                <div className="email-sender-notice" role="status">
                  <strong>Envoi via votre messagerie</strong>
                  <p>
                    L’expéditeur sera <strong>{mailboxFrom || 'votre adresse'}</strong>. Pour un envoi
                    100 % automatique depuis ComptaPilot, configurez{' '}
                    <code>BREVO_API_KEY</code> + <code>PLATFORM_EMAIL_FROM</code> sur le serveur.
                  </p>
                </div>
              )}

              <div className="field">
                <label>Expéditeur</label>
                <select
                  value={senderOptionId}
                  onChange={(e) => setSenderOptionId(e.target.value)}
                  required={senderOptions.length > 0}
                >
                  {senderOptions.length === 0 ? (
                    <option value="">{mailboxFrom || 'Mon adresse'}</option>
                  ) : (
                    senderOptions.map((opt) => (
                      <option key={opt.id} value={opt.id}>
                        {opt.kind === 'professional' ? '● ' : '○ '}
                        {opt.label}
                        {opt.kind === 'professional' ? ' (ELFIS Core)' : ''}
                        {opt.kind === 'personal' ? ' (personnel)' : ''}
                      </option>
                    ))
                  )}
                </select>
              </div>

              <label className="email-ack-row">
                <input
                  type="checkbox"
                  checked={ackSender}
                  onChange={(e) => {
                    setAckSender(e.target.checked)
                    setError('')
                  }}
                />
                <span>
                  {canSendDirect ? (
                    <>
                      J’ai compris : les réponses iront sur{' '}
                      <strong>{replyToEmail || 'mon e-mail'}</strong>
                    </>
                  ) : (
                    <>
                      J’ai compris : l’expéditeur sera{' '}
                      <strong>{mailboxFrom || 'mon adresse e-mail'}</strong>
                    </>
                  )}
                </span>
              </label>

              <div className="email-identity-box" aria-label="Récapitulatif">
                <p>
                  <strong>De</strong>
                  <span>{canSendDirect ? displayFrom : mailboxFrom || '—'}</span>
                </p>
                <p>
                  <strong>Réponse</strong>
                  <span>{replyToEmail || '—'}</span>
                </p>
                <p>
                  <strong>À</strong>
                  <span>{recipient || '—'}</span>
                </p>
                <p>
                  <strong>Pièce jointe</strong>
                  <span>{pdfName}</span>
                </p>
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
                <textarea rows={7} value={message} onChange={(e) => setMessage(e.target.value)} />
              </div>

              <div className="actions" style={{ flexWrap: 'wrap' }}>
                <button className="btn secondary" type="button" onClick={onClose} disabled={sending}>
                  Annuler
                </button>
                {canSendDirect ? (
                  <>
                    <button
                      className="btn"
                      type="submit"
                      disabled={sending || !ackSender}
                    >
                      {sending ? 'Envoi…' : 'Envoyer directement'}
                    </button>
                    <button
                      className="btn secondary"
                      type="button"
                      disabled={sending || !ackSender}
                      onClick={() => void openInMailbox()}
                    >
                      Ouvrir ma messagerie
                    </button>
                  </>
                ) : (
                  <button className="btn" type="submit" disabled={sending || !ackSender}>
                    {sending ? 'Préparation…' : 'Ouvrir ma messagerie'}
                  </button>
                )}
              </div>
              {!canSendDirect && (
                <p className="muted" style={{ fontSize: '0.85rem' }}>
                  Envoi auto : Render → Environment → <code>BREVO_API_KEY</code> et{' '}
                  <code>PLATFORM_EMAIL_FROM</code>.{' '}
                  <Link to="/settings">Paramètres entreprise</Link>
                </p>
              )}
            </form>

            {error && <p className="form-error">{error}</p>}
            {hint && <p className="muted">{hint}</p>}

            <section>
              <h4>Historique des envois</h4>
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
                            ? ' · Messagerie locale'
                            : log.provider
                              ? ` · ${log.provider}`
                              : ''}
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

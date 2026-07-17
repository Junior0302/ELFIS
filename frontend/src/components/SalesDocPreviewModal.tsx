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

type SendChannel = 'personal' | 'elfis'

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
  // encodeURIComponent (espaces → %20). URLSearchParams met des « + » que Outlook/Gmail affichent littéralement.
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
  const [platformReady, setPlatformReady] = useState(false)
  const [connectionId, setConnectionId] = useState<number | null>(null)
  const [recipient, setRecipient] = useState(doc.customer_email || '')
  const [cc, setCc] = useState('')
  const [bcc, setBcc] = useState('')
  const [subject, setSubject] = useState('')
  const [message, setMessage] = useState('')
  const [preview, setPreview] = useState<EmailSendPreview | null>(null)
  const [logs, setLogs] = useState<DocumentEmailLog[]>([])
  const [hint, setHint] = useState('')
  const [senderOptions, setSenderOptions] = useState<EmailSenderOption[]>([])
  const [channel, setChannel] = useState<SendChannel>('personal')
  const [personalEmail, setPersonalEmail] = useState('')
  const [elfisOptionId, setElfisOptionId] = useState('')
  const [hasPendingPro, setHasPendingPro] = useState(false)
  const sendingLock = useRef(false)
  const idempotencyRef = useRef(`send-${doc.id}-${Date.now()}`)

  const elfisOptions = senderOptions.filter((o) => o.kind === 'professional')
  const hasElfis = elfisOptions.length > 0
  const selectedElfis =
    elfisOptions.find((o) => o.id === elfisOptionId) || elfisOptions.find((o) => o.is_default) || elfisOptions[0] || null

  const accountEmail = (preview?.user_email || user?.email || '').trim()
  const orgEmail = (preview?.org_email || '').trim()
  const effectivePersonal = (personalEmail || accountEmail || orgEmail).trim()
  const effectiveElfis = (selectedElfis?.email || '').trim()
  const senderEmail = channel === 'elfis' ? effectiveElfis : effectivePersonal

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
        setPlatformReady(Boolean(data.can_send_direct ?? data.email_configured ?? data.smtp_configured))
        if (data.default_connection_id) setConnectionId(data.default_connection_id)
        if (data.preview) {
          setPreview(data.preview)
          setRecipient(data.preview.recipient || doc.customer_email || '')
          setCc(data.preview.cc || '')
          setBcc(data.preview.bcc || '')
          setSubject(data.preview.subject || '')
          setMessage(data.preview.message || '')
          if (data.preview.connection_id) setConnectionId(data.preview.connection_id)
          setPersonalEmail(data.preview.user_email || data.preview.org_email || '')
        }
      })
      .catch(() => undefined)
    api
      .professionalSenderOptions(token, orgId)
      .then((data) => {
        if (cancelled) return
        setSenderOptions(data.options)
        const pros = data.options.filter((o) => o.kind === 'professional')
        const personal = data.options.find((o) => o.kind === 'personal')
        if (personal?.email) setPersonalEmail(personal.email)
        if (pros.length) {
          const def =
            pros.find((o) => o.id === data.default_option_id) ||
            pros.find((o) => o.is_default) ||
            pros[0]
          setElfisOptionId(def.id)
          setChannel('elfis')
        } else {
          setChannel('personal')
        }
      })
      .catch(() => undefined)
    api
      .myProfessionalEmails(token, orgId)
      .then((data) => {
        if (!cancelled) setHasPendingPro(Boolean(data.has_pending))
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

  const sendViaElfis = async () => {
    if (sendingLock.current) return
    if (!hasElfis || !effectiveElfis) {
      setError('Aucune adresse ELFIS Core active. Demandez-la depuis Mon compte.')
      return
    }
    if (!platformReady) {
      setError(
        'Envoi depuis ELFIS Core temporairement indisponible. Réessayez plus tard ou utilisez votre messagerie personnelle.',
      )
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
          preferred_from_email: effectiveElfis,
          preferred_from_label: selectedElfis?.label || effectiveElfis,
          idempotency_key: `${idempotencyRef.current}-elfis`,
        },
        token,
        orgId,
      )
      setLogs((current) => [result.email_log, ...current])
      setPlatformReady(Boolean(result.can_send_direct ?? result.email_configured ?? result.smtp_configured))
      onSent(result.document, result.email_log)
      if (result.email_log.status === 'sent' || result.email_log.status === 'delivered') {
        idempotencyRef.current = `send-${doc.id}-${Date.now()}`
        setHint(`E-mail envoyé depuis ${effectiveElfis} vers ${recipient.trim()}.`)
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

  const sendViaPersonalMailbox = async () => {
    if (sendingLock.current) return
    if (!effectivePersonal) {
      setError('Indiquez votre adresse e-mail personnelle (expéditeur).')
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
          preferred_from_email: effectivePersonal,
          preferred_from_label: effectivePersonal,
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
      setHint(
        `Messagerie ouverte. Envoyez depuis ${effectivePersonal}, joignez le PDF, puis validez l’envoi.`,
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
    if (channel === 'elfis') void sendViaElfis()
    else void sendViaPersonalMailbox()
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
              <p className="muted" style={{ marginBottom: '0.85rem' }}>
                Deux possibilités : votre messagerie personnelle, ou votre adresse ELFIS Core une fois
                activée.
              </p>

              <fieldset className="email-channel-fieldset">
                <legend>Comment envoyer ?</legend>

                <label className={`email-channel-option ${channel === 'personal' ? 'is-selected' : ''}`}>
                  <input
                    type="radio"
                    name="send-channel"
                    checked={channel === 'personal'}
                    onChange={() => {
                      setChannel('personal')
                      setError('')
                    }}
                  />
                  <span>
                    <strong>1 · Mon e-mail personnel</strong>
                    <small>
                      Ouvre votre boîte mail (Gmail, Outlook…). Vous envoyez depuis l’adresse de votre
                      choix.
                    </small>
                  </span>
                </label>

                <label
                  className={`email-channel-option ${channel === 'elfis' ? 'is-selected' : ''} ${
                    !hasElfis ? 'is-disabled' : ''
                  }`}
                >
                  <input
                    type="radio"
                    name="send-channel"
                    checked={channel === 'elfis'}
                    disabled={!hasElfis}
                    onChange={() => {
                      setChannel('elfis')
                      setError('')
                    }}
                  />
                  <span>
                    <strong>2 · Adresse ELFIS Core (recommandé)</strong>
                    <small>
                      {hasElfis
                        ? `Envoi direct depuis l’outil avec ${effectiveElfis || 'votre adresse @elfis-core.com'}.`
                        : hasPendingPro
                          ? 'Demande en cours — accès sous 24 h après validation admin / Brevo.'
                          : 'Pas encore d’adresse. Demandez-la gratuitement dans Mon compte.'}
                    </small>
                  </span>
                </label>
              </fieldset>

              {!hasElfis && (
                <div className="email-sender-notice" role="status">
                  <strong>Obtenir jean.dupont@elfis-core.com</strong>
                  <p>
                    Sur <Link to="/compte">Mon compte</Link>, cliquez « Demander mon adresse ». Notre
                    équipe configure Brevo puis active l’envoi. Vous pourrez alors envoyer devis et
                    factures directement depuis ComptaPilot.
                  </p>
                </div>
              )}

              <div className="field">
                <label>Expéditeur</label>
                {channel === 'elfis' ? (
                  hasElfis ? (
                    <select
                      value={selectedElfis?.id || ''}
                      onChange={(e) => setElfisOptionId(e.target.value)}
                      required
                    >
                      {elfisOptions.map((opt) => (
                        <option key={opt.id} value={opt.id}>
                          {opt.email}
                          {opt.is_default ? ' (par défaut)' : ''}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input value="" disabled placeholder="Adresse ELFIS non encore activée" />
                  )
                ) : (
                  <input
                    type="email"
                    required
                    value={personalEmail}
                    onChange={(e) => setPersonalEmail(e.target.value)}
                    placeholder="contact@entreprise.fr"
                  />
                )}
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

              <div className="email-identity-box" aria-label="Récapitulatif">
                <p>
                  <strong>De</strong>
                  <span>{senderEmail || '—'}</span>
                </p>
                <p>
                  <strong>À</strong>
                  <span>{recipient || '—'}</span>
                </p>
                <p>
                  <strong>Mode</strong>
                  <span>
                    {channel === 'elfis' ? 'Envoi direct ELFIS Core' : 'Messagerie personnelle (mailto)'}
                  </span>
                </p>
                <p>
                  <strong>Pièce jointe</strong>
                  <span>{pdfName}</span>
                </p>
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
                <button
                  className="btn"
                  type="submit"
                  disabled={
                    sending ||
                    (channel === 'elfis' && (!hasElfis || !platformReady)) ||
                    (channel === 'personal' && !effectivePersonal)
                  }
                >
                  {sending
                    ? 'Envoi…'
                    : channel === 'elfis'
                      ? 'Envoyer depuis ELFIS Core'
                      : 'Ouvrir ma messagerie'}
                </button>
              </div>
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

import { useEffect, useId, useMemo, useRef, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api, type DocumentEmailLog, type EmailSendPreview, type OrgDetail, type SalesDoc } from '../api'
import { useAuth } from '../auth'
import { ConfirmDialog, Dialog } from '../design-system/overlays'
import {
  clearEmailComposerDraft,
  readEmailComposerDraft,
  writeEmailComposerDraft,
  type EmailComposerDraftFields,
} from '../emailComposerDraft'
import { mailerReasonMessage, resolveSendButtonState } from '../mailerErrorMessages'
import {
  buildMailtoClientBody,
  buildMailtoUrl,
  openMailtoUrl,
  sanitizePdfDownloadName,
  softenMailtoPreviewMessage,
} from '../mailtoComposer'
import { orgLegalGaps, orgLegalIsReadyForSend } from '../orgLegalCompleteness'

type Props = {
  doc: SalesDoc
  token: string
  orgId: number
  onClose: () => void
  onEdit: (doc: SalesDoc) => void
  onSent: (doc: SalesDoc, log: DocumentEmailLog) => void
  onMarkPaid?: (doc: SalesDoc) => void
  onRemind?: (doc: SalesDoc) => void
}

type SendPhase = 'idle' | 'prepare' | 'archive' | 'send' | 'done'
type MobileTab = 'preview' | 'actions' | 'history'
type PendingCloseAction = (() => void) | null

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
    mailto_opened: 'Messagerie ouverte',
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

function composerLog(event: string, meta?: Record<string, string | number | boolean | null>) {
  if (!import.meta.env.DEV) return
  // Never log recipient, subject, body, tokens, or PDF payloads.
  console.debug(`[EmailComposer] ${event}`, meta ?? {})
}

export default function SalesDocPreviewModal({
  doc,
  token,
  orgId,
  onClose,
  onEdit,
  onSent,
  onMarkPaid,
  onRemind,
}: Props) {
  const { user } = useAuth()
  const fieldId = useId()
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
  const [mailerReasonCode, setMailerReasonCode] = useState('')
  const [mailtoAck, setMailtoAck] = useState(false)
  const [legalAck, setLegalAck] = useState(false)
  const [orgLegal, setOrgLegal] = useState<OrgDetail['organization'] | null>(null)
  const [mobileTab, setMobileTab] = useState<MobileTab>('preview')
  const [lastFailed, setLastFailed] = useState(false)
  const [lastSent, setLastSent] = useState(false)
  const [abandonOpen, setAbandonOpen] = useState(false)
  const [mailtoConfirmOpen, setMailtoConfirmOpen] = useState(false)
  const [formReady, setFormReady] = useState(false)

  const sendingLock = useRef(false)
  const idempotencyRef = useRef(`send-${doc.id}-${Date.now()}`)
  const initializedDocIdRef = useRef<number | null>(null)
  const formInitializedRef = useRef(false)
  const baselineRef = useRef<EmailComposerDraftFields | null>(null)
  const pendingCloseRef = useRef<PendingCloseAction>(null)
  const draftTimerRef = useRef<number | null>(null)

  const legalGaps = orgLegalGaps(orgLegal)
  const legalReady = orgLegalIsReadyForSend(orgLegal)
  const blockingLegalGaps = legalGaps.filter((g) => g.code !== 'legal_mentions')
  const canProceedLegal = legalReady || legalAck
  const label = doc.doc_type === 'devis' ? 'Devis' : doc.doc_type === 'avoir' ? 'Avoir' : 'Facture'
  const pdfName = sanitizePdfDownloadName(
    preview?.pdf_filename || `${label}-${doc.number}.pdf`,
    `${label}-${doc.number}.pdf`,
  )
  const isInvoice = doc.doc_type === 'facture'
  const sendMode: 'server' | 'mailto' = canSendDirect ? 'server' : 'mailto'

  const currentFields = useMemo<EmailComposerDraftFields>(
    () => ({
      recipient,
      cc,
      bcc,
      subject,
      message,
      sendMode,
      mailtoAck,
      legalAck,
    }),
    [recipient, cc, bcc, subject, message, sendMode, mailtoAck, legalAck],
  )

  const isDirty = useMemo(() => {
    if (!formReady || !baselineRef.current) return false
    const base = baselineRef.current
    // sendMode is server-driven (can_send_direct) — not user draft dirtiness.
    return (
      currentFields.recipient !== base.recipient ||
      currentFields.cc !== base.cc ||
      currentFields.bcc !== base.bcc ||
      currentFields.subject !== base.subject ||
      currentFields.message !== base.message ||
      currentFields.mailtoAck !== base.mailtoAck ||
      currentFields.legalAck !== base.legalAck
    )
  }, [currentFields, formReady])

  const buttonState = resolveSendButtonState({
    canSendDirect,
    recipient,
    canProceedLegal: canProceedLegal && (canSendDirect || mailtoAck),
    sending,
    lastFailed,
    lastSent,
  })

  const applyFields = (fields: Partial<EmailComposerDraftFields>, asBaseline: boolean) => {
    if (fields.recipient != null) setRecipient(fields.recipient)
    if (fields.cc != null) setCc(fields.cc)
    if (fields.bcc != null) setBcc(fields.bcc)
    if (fields.subject != null) setSubject(fields.subject)
    if (fields.message != null) setMessage(fields.message)
    if (fields.mailtoAck != null) setMailtoAck(fields.mailtoAck)
    if (fields.legalAck != null) setLegalAck(fields.legalAck)
    if (asBaseline) {
      baselineRef.current = {
        recipient: fields.recipient ?? '',
        cc: fields.cc ?? '',
        bcc: fields.bcc ?? '',
        subject: fields.subject ?? '',
        message: fields.message ?? '',
        sendMode: fields.sendMode ?? 'server',
        mailtoAck: fields.mailtoAck ?? false,
        legalAck: fields.legalAck ?? false,
      }
    }
  }

  const commitBaseline = (fields: EmailComposerDraftFields) => {
    baselineRef.current = { ...fields }
  }

  useEffect(() => {
    composerLog('mounted', { documentId: doc.id, organizationId: orgId })
    return () => {
      composerLog('unmounted', { documentId: doc.id })
      if (draftTimerRef.current != null) {
        window.clearTimeout(draftTimerRef.current)
        draftTimerRef.current = null
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- mount/unmount only for this document instance
  }, [])

  // PDF + server meta: init form once per document; never wipe a local / restored draft.
  useEffect(() => {
    let objectUrl: string | null = null
    let cancelled = false
    const documentChanged = initializedDocIdRef.current !== doc.id

    if (documentChanged) {
      initializedDocIdRef.current = doc.id
      formInitializedRef.current = false
      setFormReady(false)
      setError('')
      setHint('')
      setPhase('idle')
      setLastFailed(false)
      setLastSent(false)
      setMobileTab('preview')
      setAbandonOpen(false)
      setMailtoConfirmOpen(false)
      pendingCloseRef.current = null
      idempotencyRef.current = `send-${doc.id}-${Date.now()}`
      baselineRef.current = null

      const restored = readEmailComposerDraft(orgId, doc.id)
      if (restored) {
        applyFields(
          {
            recipient: restored.recipient,
            cc: restored.cc,
            bcc: restored.bcc,
            subject: restored.subject,
            message: restored.message,
            sendMode: restored.sendMode,
            mailtoAck: restored.mailtoAck,
            legalAck: restored.legalAck,
          },
          true,
        )
        formInitializedRef.current = true
        setFormReady(true)
        composerLog('initialized', { documentId: doc.id, source: 'session_draft' })
        composerLog('draft_preserved', { documentId: doc.id, reason: 'restore' })
      } else {
        setRecipient(doc.customer_email || '')
        setCc('')
        setBcc('')
        setSubject('')
        setMessage('')
        setMailtoAck(false)
        setLegalAck(false)
      }
    } else {
      composerLog('refresh_received', {
        documentId: doc.id,
        formInitialized: formInitializedRef.current,
      })
    }

    setLoadingPdf(true)
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
        const direct = Boolean(data.can_send_direct ?? data.email_configured)
        setCanSendDirect(direct)
        setMailerReasonCode(String(data.mailer_reason_code || ''))
        if (data.preview) setPreview(data.preview)

        if (formInitializedRef.current) {
          composerLog('draft_preserved', { documentId: doc.id, reason: 'meta_refresh' })
          return
        }

        const mode: 'server' | 'mailto' = direct ? 'server' : 'mailto'
        const rawMessage = data.preview?.message || ''
        const next: EmailComposerDraftFields = data.preview
          ? {
              recipient: data.preview.recipient || doc.customer_email || '',
              cc: data.preview.cc || '',
              bcc: data.preview.bcc || '',
              subject: data.preview.subject || '',
              message: mode === 'mailto' ? softenMailtoPreviewMessage(rawMessage) : rawMessage,
              sendMode: mode,
              mailtoAck: false,
              legalAck: false,
            }
          : {
              recipient: doc.customer_email || '',
              cc: '',
              bcc: '',
              subject: '',
              message: '',
              sendMode: mode,
              mailtoAck: false,
              legalAck: false,
            }
        applyFields(next, true)
        formInitializedRef.current = true
        setFormReady(true)
        composerLog('initialized', {
          documentId: doc.id,
          source: data.preview ? 'server_preview' : 'fallback',
        })
      })
      .catch(() => {
        if (cancelled || formInitializedRef.current) return
        applyFields(
          {
            recipient: doc.customer_email || '',
            cc: '',
            bcc: '',
            subject: '',
            message: '',
            sendMode: 'mailto',
            mailtoAck: false,
            legalAck: false,
          },
          true,
        )
        formInitializedRef.current = true
        setFormReady(true)
        composerLog('initialized', { documentId: doc.id, source: 'error_fallback' })
      })

    api
      .orgDetail(orgId, token)
      .then((detail) => {
        if (!cancelled) setOrgLegal(detail.organization)
      })
      .catch(() => {
        if (!cancelled) setOrgLegal(null)
      })

    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
    // Re-init only on document identity / auth — not on parent SalesDoc object churn.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [doc.id, token, orgId])

  // Debounced session draft while dirty.
  useEffect(() => {
    if (!formReady || !isDirty) return
    composerLog('dirty', { documentId: doc.id })
    if (draftTimerRef.current != null) window.clearTimeout(draftTimerRef.current)
    draftTimerRef.current = window.setTimeout(() => {
      writeEmailComposerDraft(orgId, doc.id, currentFields)
      composerLog('draft_preserved', { documentId: doc.id, reason: 'autosave' })
    }, 400)
    return () => {
      if (draftTimerRef.current != null) {
        window.clearTimeout(draftTimerRef.current)
        draftTimerRef.current = null
      }
    }
  }, [currentFields, formReady, isDirty, orgId, doc.id])

  // Escape while dirty → confirm (dismissible=false blocks OverlayManager force-close).
  useEffect(() => {
    if (!isDirty || sending) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return
      event.preventDefault()
      event.stopPropagation()
      composerLog('close_requested', { documentId: doc.id, via: 'escape' })
      pendingCloseRef.current = () => {
        clearEmailComposerDraft(orgId, doc.id)
        onClose()
      }
      setAbandonOpen(true)
    }
    document.addEventListener('keydown', onKey, true)
    return () => document.removeEventListener('keydown', onKey, true)
  }, [isDirty, sending, doc.id, orgId, onClose])

  const finishClose = (action: () => void) => {
    clearEmailComposerDraft(orgId, doc.id)
    action()
  }

  const requestClose = (action: () => void, via: string) => {
    if (sending) return
    composerLog('close_requested', { documentId: doc.id, via, dirty: isDirty })
    if (isDirty) {
      pendingCloseRef.current = () => finishClose(action)
      setAbandonOpen(true)
      return
    }
    finishClose(action)
  }

  const download = async () => {
    try {
      await api.downloadSalesDocPdf(doc.id, token, orgId, pdfName)
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
    if (!canProceedLegal) {
      setError('Complétez les mentions légales ou confirmez l’envoi malgré les lacunes.')
      return
    }
    sendingLock.current = true
    setSending(true)
    setError('')
    setHint('')
    setLastFailed(false)
    setLastSent(false)
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
        setLastFailed(true)
        const code = result.email_log?.error_code || result.mailer_reason_code
        setHint(
          result.message ||
            mailerReasonMessage(code) ||
            'Le document a été archivé, mais l’e-mail n’a pas pu être envoyé. Vous pourrez réessayer sans recréer la facture.',
        )
        // Keep draft + fields on failure.
      } else if (result.already_processed || result.status === 'already_sent') {
        setLastSent(true)
        setHint(result.message || 'Cet envoi a déjà été traité.')
        clearEmailComposerDraft(orgId, doc.id)
        commitBaseline(currentFields)
      } else {
        setLastSent(true)
        setHint(
          result.vault_document_id
            ? `E-mail envoyé avec le PDF en pièce jointe. Archivé dans ELFIS Vault (${result.vault_document_id}).`
            : 'E-mail envoyé avec le PDF en pièce jointe.',
        )
        clearEmailComposerDraft(orgId, doc.id)
        commitBaseline(currentFields)
      }
    } catch (reason) {
      window.clearTimeout(prepareTimer)
      window.clearTimeout(archiveTimer)
      setPhase('idle')
      setLastFailed(true)
      const msg = reason instanceof Error ? reason.message : 'Envoi impossible'
      if (msg.toLowerCase().includes('stockage') || msg.toLowerCase().includes('503')) {
        setError('Le document n’a pas pu être archivé. L’e-mail n’a pas été envoyé.')
      } else {
        setError(msg)
      }
      // Keep all fields on error — never clear draft here.
    } finally {
      setSending(false)
      sendingLock.current = false
    }
  }

  const sendMailto = async () => {
    if (sendingLock.current) {
      throw new Error('Envoi déjà en cours')
    }
    if (!recipient.trim()) {
      const msg = 'Indiquez le destinataire.'
      setError(msg)
      throw new Error(msg)
    }
    if (!canProceedLegal) {
      const msg = 'Complétez les mentions légales ou confirmez l’envoi malgré les lacunes.'
      setError(msg)
      throw new Error(msg)
    }
    if (!mailtoAck) {
      const msg = 'Confirmez que l’e-mail partira depuis votre messagerie personnelle.'
      setError(msg)
      throw new Error(msg)
    }
    sendingLock.current = true
    setSending(true)
    setError('')
    setHint('')
    setLastFailed(false)
    setPhase('prepare')
    try {
      await api.downloadSalesDocPdf(doc.id, token, orgId, pdfName)
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
          preferred_from_email: (user?.email || '').trim() || undefined,
          preferred_from_label: (user?.email || '').trim() || undefined,
          idempotency_key: idempotencyRef.current,
        },
        token,
        orgId,
      )
      const mailto = buildMailtoUrl({
        to: recipient.trim(),
        subject: subject || `${label} ${doc.number}`,
        body: buildMailtoClientBody(message || '', label, pdfName),
        cc: cc || undefined,
        bcc: bcc || undefined,
      })
      // Anchor click — never window.location.href (avoids nav / remount side-effects).
      openMailtoUrl(mailto)
      setPhase('done')
      if (result.email_log) {
        setLogs((current) => [result.email_log!, ...current])
        onSent(result.document, result.email_log)
      }
      setHint(
        `PDF « ${pdfName} » téléchargé et messagerie ouverte. Joignez le fichier manuellement — ce n’est pas un envoi SMTP confirmé.`,
      )
      idempotencyRef.current = `send-${doc.id}-${Date.now()}`
      clearEmailComposerDraft(orgId, doc.id)
      commitBaseline(currentFields)
      composerLog('mailto_opened', { documentId: doc.id })
    } catch (reason) {
      setPhase('idle')
      setLastFailed(true)
      setError(reason instanceof Error ? reason.message : 'Ouverture messagerie impossible')
      throw reason
    } finally {
      setSending(false)
      sendingLock.current = false
    }
  }

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (canSendDirect) {
      void sendServer()
      return
    }
    // Personal mailbox: confirm PDF download + manual attach before opening Outlook.
    if (!recipient.trim()) {
      setError('Indiquez le destinataire.')
      return
    }
    if (!canProceedLegal) {
      setError('Complétez les mentions légales ou confirmez l’envoi malgré les lacunes.')
      return
    }
    if (!mailtoAck) {
      setError('Confirmez que l’e-mail partira depuis votre messagerie personnelle.')
      return
    }
    setError('')
    setMailtoConfirmOpen(true)
  }

  const submitDisabled =
    sending || !recipient.trim() || !canProceedLegal || (!canSendDirect && !mailtoAck)

  const submitLabel = (() => {
    if (sending) return phaseLabel(phase) || 'Envoi en cours…'
    if (buttonState === 'retry') return canSendDirect ? 'Réessayer l’envoi' : 'Réessayer (mailto)'
    if (buttonState === 'sent') return canSendDirect ? 'Renvoyer' : 'Rouvrir messagerie'
    if (!canSendDirect) return 'Télécharger PDF + ouvrir messagerie'
    return 'Envoyer maintenant'
  })()

  const freeDismiss = !sending && !isDirty

  const actionsPanel = (
    <div className="sales-preview-side">
      <div className="sales-preview-actions-bar">
        <button
          className="btn secondary"
          type="button"
          onClick={() => requestClose(() => onEdit(doc), 'edit')}
          disabled={sending}
        >
          Modifier
        </button>
        <button className="btn secondary" type="button" onClick={() => void download()}>
          Télécharger
        </button>
        {isInvoice && onMarkPaid ? (
          <button
            className="btn secondary"
            type="button"
            onClick={() => requestClose(() => onMarkPaid(doc), 'mark_paid')}
            disabled={sending}
          >
            Marquer payée
          </button>
        ) : null}
        {isInvoice && onRemind ? (
          <button className="btn secondary" type="button" onClick={() => onRemind(doc)} disabled={sending}>
            Relancer
          </button>
        ) : null}
      </div>

      <form className="mailto-send-panel" onSubmit={onSubmit}>
        <header className="mailto-send-head">
          <h4>Envoyer au client</h4>
          <p>
            {canSendDirect
              ? 'Mode serveur (Brevo / SMTP) : le PDF est archivé dans ELFIS Vault puis joint automatiquement.'
              : 'Mode messagerie personnelle : le PDF est téléchargé sur votre appareil ; vous l’ajoutez manuellement dans Outlook / votre client mail. Pas d’envoi serveur ELFIS.'}
          </p>
        </header>

        {blockingLegalGaps.length > 0 && (
          <div className="panel sales-preview-compliance" role="status">
            <p className="form-error" style={{ marginTop: 0 }}>
              Mentions à compléter avant un envoi commercial sûr
            </p>
            <ul className="muted" style={{ margin: '0.35rem 0' }}>
              {blockingLegalGaps.map((g) => (
                <li key={g.code}>{g.label}</li>
              ))}
            </ul>
            <p className="muted">
              Complétez la fiche dans <Link to="/platform/organization">Organisation</Link> (SIRET, adresse…),
              téléchargez le PDF, ou confirmez un envoi temporaire à vos risques :
            </p>
            <label className="sales-preview-check">
              <input
                type="checkbox"
                checked={legalAck}
                onChange={(e) => setLegalAck(e.target.checked)}
                disabled={sending}
              />
              <span>
                J’envoie malgré ces lacunes (consentement explicite — aucune validation juridique
                ELFIS).
              </span>
            </label>
          </div>
        )}

        {!blockingLegalGaps.length && legalGaps.some((g) => g.code === 'legal_mentions') && (
          <p className="muted" style={{ marginBottom: '0.75rem' }}>
            Astuce : ajoutez des mentions légales libres dans{' '}
            <Link to="/platform/organization">Organisation (ELFIS Core)</Link> (recommandé).
          </p>
        )}

        {!canSendDirect && (
          <div className="panel sales-preview-config-warn">
            <p className="form-error" style={{ marginTop: 0 }}>
              {mailerReasonMessage(mailerReasonCode) ||
                'Envoi serveur indisponible — fournisseur non prêt.'}
            </p>
            <p className="muted">
              Admin ELFIS : configurez le provider dans{' '}
              <Link to="/platform/communications">Communications ELFIS Core</Link>
              {' '}(sans exposer de secrets). Diagnostic admin :{' '}
              <Link to="/elfadmin/configuration">Configuration plateforme</Link>.
            </p>
            <p className="muted">
              En attendant : téléchargez le PDF (nom : {pdfName}) puis ouvrez votre messagerie.
              Limitation technique mailto : le PDF n’est pas joint automatiquement — note visible
              uniquement ici, pas dans le message client.
            </p>
            <label className="sales-preview-check">
              <input
                type="checkbox"
                checked={mailtoAck}
                onChange={(e) => setMailtoAck(e.target.checked)}
                disabled={sending}
              />
              <span>
                Je confirme que l’e-mail partira depuis mon adresse personnelle et que j’y joindrai le
                PDF téléchargé.
              </span>
            </label>
          </div>
        )}

        <div className="field">
          <label htmlFor={`${fieldId}-to`}>Destinataire</label>
          <input
            id={`${fieldId}-to`}
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
            <span>Mode</span>
            <strong>{canSendDirect ? 'Serveur (Brevo / SMTP)' : 'Messagerie personnelle'}</strong>
          </div>
        </div>

        <div className="field">
          <label htmlFor={`${fieldId}-cc`}>Copie (CC)</label>
          <input
            id={`${fieldId}-cc`}
            type="email"
            value={cc}
            onChange={(e) => setCc(e.target.value)}
            placeholder="optionnel"
            disabled={sending}
          />
        </div>
        <div className="field">
          <label htmlFor={`${fieldId}-subject`}>Objet</label>
          <input
            id={`${fieldId}-subject`}
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            required
            disabled={sending}
          />
        </div>
        <div className="field">
          <label htmlFor={`${fieldId}-msg`}>Message</label>
          <textarea
            id={`${fieldId}-msg`}
            rows={5}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            disabled={sending}
          />
        </div>

        {sending && phase !== 'idle' ? (
          <p className="muted" role="status">
            {phaseLabel(phase)}
          </p>
        ) : null}

        <div className="actions sales-preview-send-actions">
          <button
            className="btn secondary"
            type="button"
            onClick={() => requestClose(onClose, 'cancel')}
            disabled={sending}
          >
            Annuler
          </button>
          {!canSendDirect ? (
            <>
              <button className="btn secondary" type="button" onClick={() => void download()} disabled={sending}>
                Télécharger PDF
              </button>
              <Link className="btn secondary" to="/elfadmin/configuration">
                Configurer
              </Link>
            </>
          ) : null}
          <button className="btn" type="submit" disabled={submitDisabled}>
            {submitLabel}
          </button>
        </div>
      </form>

      {error ? <p className="form-error">{error}</p> : null}
      {hint ? (
        <p className="mailto-hint" role="status">
          {hint}
        </p>
      ) : null}
    </div>
  )

  const historyPanel = (
    <section className="mailto-history">
      <h4>Historique d’envoi</h4>
      <p className="muted sales-preview-archive-note">
        Archivage Vault automatique à l’envoi serveur — pas d’historique parallèle.
      </p>
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
                  {log.error_code ? ` · ${log.error_code}` : ''}
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
  )

  return (
    <>
      <Dialog
        open
        onOpenChange={(open) => {
          if (!open) requestClose(onClose, 'dialog')
        }}
        title={`${label} ${doc.number}`}
        description={`${doc.customer_name}${doc.customer_email ? ` · ${doc.customer_email}` : ''} · ${doc.status}`}
        size="full"
        className="sales-preview-dialog"
        closeOnBackdrop={freeDismiss}
        closeOnEscape={freeDismiss}
        dismissible={freeDismiss}
      >
        <div className="sales-preview-shell">
          {!freeDismiss && !sending ? (
            <div className="sales-preview-dirty-bar">
              <button
                type="button"
                className="btn secondary btn-sm"
                onClick={() => requestClose(onClose, 'header_close')}
              >
                Fermer
              </button>
            </div>
          ) : null}
          <div className="sales-preview-tabs" role="tablist" aria-label="Sections aperçu">
            <button
              type="button"
              role="tab"
              aria-selected={mobileTab === 'preview'}
              className={mobileTab === 'preview' ? 'is-active' : ''}
              onClick={() => setMobileTab('preview')}
            >
              Aperçu
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={mobileTab === 'actions'}
              className={mobileTab === 'actions' ? 'is-active' : ''}
              onClick={() => setMobileTab('actions')}
            >
              Actions
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={mobileTab === 'history'}
              className={mobileTab === 'history' ? 'is-active' : ''}
              onClick={() => setMobileTab('history')}
            >
              Historique
            </button>
          </div>

          <div className="sales-preview-grid">
            <div
              className={`sales-preview-pane sales-preview-pane--pdf ${
                mobileTab === 'preview' ? 'is-mobile-visible' : ''
              }`}
            >
              <div className="sales-preview-pdf">
                {loadingPdf && <p className="muted">Chargement de l’aperçu PDF…</p>}
                {!loadingPdf && pdfUrl ? <iframe title={`PDF ${doc.number}`} src={pdfUrl} /> : null}
                {!loadingPdf && !pdfUrl ? <p className="form-error">Aperçu PDF indisponible.</p> : null}
              </div>
            </div>
            <div
              className={`sales-preview-pane sales-preview-pane--actions ${
                mobileTab === 'actions' ? 'is-mobile-visible' : ''
              }`}
            >
              {actionsPanel}
              <div className="sales-preview-history-desktop">{historyPanel}</div>
            </div>
            <div
              className={`sales-preview-pane sales-preview-pane--history ${
                mobileTab === 'history' ? 'is-mobile-visible' : ''
              }`}
            >
              {historyPanel}
            </div>
          </div>
        </div>
      </Dialog>

      <ConfirmDialog
        open={abandonOpen}
        onOpenChange={(open) => {
          setAbandonOpen(open)
          if (!open) pendingCloseRef.current = null
        }}
        title="E-mail non envoyé"
        description="Vous avez un email non envoyé. Voulez-vous continuer la rédaction ou abandonner ce brouillon ?"
        cancelLabel="Continuer"
        confirmLabel="Abandonner"
        tone="warning"
        onConfirm={() => {
          const action = pendingCloseRef.current
          pendingCloseRef.current = null
          setAbandonOpen(false)
          if (action) action()
          else finishClose(onClose)
        }}
      />

      <ConfirmDialog
        open={mailtoConfirmOpen}
        onOpenChange={(open) => {
          if (sending) return
          setMailtoConfirmOpen(open)
        }}
        title="Ouvrir votre messagerie ?"
        description={`Le PDF « ${pdfName} » va être téléchargé. Ajoutez-le manuellement à votre message avant l’envoi. Ce n’est pas un envoi serveur ELFIS (Brevo / SMTP).`}
        cancelLabel="Retour"
        confirmLabel="Télécharger et ouvrir"
        tone="neutral"
        loading={sending}
        onConfirm={async () => {
          await sendMailto()
        }}
      />
    </>
  )
}

/**
 * Temporary email-composer draft persistence (sessionStorage).
 * Never stores tokens, Brevo keys, PDF bytes, or secrets.
 */

export type EmailComposerDraftPayload = {
  documentId: number
  organizationId: number
  recipient: string
  cc: string
  bcc: string
  subject: string
  message: string
  sendMode: 'server' | 'mailto'
  mailtoAck: boolean
  legalAck: boolean
  savedAt: number
}

export type EmailComposerDraftFields = Omit<
  EmailComposerDraftPayload,
  'documentId' | 'organizationId' | 'savedAt'
>

const KEY_PREFIX = 'elfis.email-draft'
/** Drafts older than 12h are discarded. */
export const EMAIL_DRAFT_TTL_MS = 12 * 60 * 60 * 1000

export function emailDraftStorageKey(organizationId: number, documentId: number): string {
  return `${KEY_PREFIX}.${organizationId}.${documentId}`
}

export function isEmailDraftExpired(savedAt: number, now = Date.now()): boolean {
  return !Number.isFinite(savedAt) || now - savedAt > EMAIL_DRAFT_TTL_MS
}

export function readEmailComposerDraft(
  organizationId: number,
  documentId: number,
  storage: Storage | null = typeof sessionStorage !== 'undefined' ? sessionStorage : null,
  now = Date.now(),
): EmailComposerDraftPayload | null {
  if (!storage || !organizationId || !documentId) return null
  try {
    const raw = storage.getItem(emailDraftStorageKey(organizationId, documentId))
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<EmailComposerDraftPayload>
    if (
      parsed.documentId !== documentId ||
      parsed.organizationId !== organizationId ||
      typeof parsed.savedAt !== 'number'
    ) {
      storage.removeItem(emailDraftStorageKey(organizationId, documentId))
      return null
    }
    if (isEmailDraftExpired(parsed.savedAt, now)) {
      storage.removeItem(emailDraftStorageKey(organizationId, documentId))
      return null
    }
    return {
      documentId,
      organizationId,
      recipient: String(parsed.recipient ?? ''),
      cc: String(parsed.cc ?? ''),
      bcc: String(parsed.bcc ?? ''),
      subject: String(parsed.subject ?? ''),
      message: String(parsed.message ?? ''),
      sendMode: parsed.sendMode === 'mailto' ? 'mailto' : 'server',
      mailtoAck: Boolean(parsed.mailtoAck),
      legalAck: Boolean(parsed.legalAck),
      savedAt: parsed.savedAt,
    }
  } catch {
    return null
  }
}

export function writeEmailComposerDraft(
  organizationId: number,
  documentId: number,
  fields: EmailComposerDraftFields,
  storage: Storage | null = typeof sessionStorage !== 'undefined' ? sessionStorage : null,
  now = Date.now(),
): void {
  if (!storage || !organizationId || !documentId) return
  const payload: EmailComposerDraftPayload = {
    documentId,
    organizationId,
    recipient: fields.recipient,
    cc: fields.cc,
    bcc: fields.bcc,
    subject: fields.subject,
    message: fields.message,
    sendMode: fields.sendMode,
    mailtoAck: fields.mailtoAck,
    legalAck: fields.legalAck,
    savedAt: now,
  }
  try {
    storage.setItem(emailDraftStorageKey(organizationId, documentId), JSON.stringify(payload))
  } catch {
    /* quota / private mode — ignore */
  }
}

export function clearEmailComposerDraft(
  organizationId: number,
  documentId: number,
  storage: Storage | null = typeof sessionStorage !== 'undefined' ? sessionStorage : null,
): void {
  if (!storage || !organizationId || !documentId) return
  try {
    storage.removeItem(emailDraftStorageKey(organizationId, documentId))
  } catch {
    /* ignore */
  }
}

export function emailComposerFieldsEqual(
  a: EmailComposerDraftFields,
  b: EmailComposerDraftFields,
): boolean {
  return (
    a.recipient === b.recipient &&
    a.cc === b.cc &&
    a.bcc === b.bcc &&
    a.subject === b.subject &&
    a.message === b.message &&
    a.sendMode === b.sendMode &&
    a.mailtoAck === b.mailtoAck &&
    a.legalAck === b.legalAck
  )
}

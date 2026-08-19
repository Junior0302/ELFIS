import { describe, expect, it, beforeEach } from 'vitest'
import {
  clearEmailComposerDraft,
  emailComposerFieldsEqual,
  emailDraftStorageKey,
  isEmailDraftExpired,
  readEmailComposerDraft,
  writeEmailComposerDraft,
  EMAIL_DRAFT_TTL_MS,
  type EmailComposerDraftFields,
} from './emailComposerDraft'

function memoryStorage(): Storage {
  const map = new Map<string, string>()
  return {
    get length() {
      return map.size
    },
    clear() {
      map.clear()
    },
    getItem(key: string) {
      return map.has(key) ? map.get(key)! : null
    },
    key(index: number) {
      return [...map.keys()][index] ?? null
    },
    removeItem(key: string) {
      map.delete(key)
    },
    setItem(key: string, value: string) {
      map.set(key, value)
    },
  }
}

const fields: EmailComposerDraftFields = {
  recipient: 'a@b.c',
  cc: '',
  bcc: '',
  subject: 'Facture',
  message: 'Bonjour',
  sendMode: 'server',
  mailtoAck: false,
  legalAck: true,
}

describe('emailComposerDraft', () => {
  let storage: Storage

  beforeEach(() => {
    storage = memoryStorage()
  })

  it('écrit et relit un brouillon isolé org/doc', () => {
    writeEmailComposerDraft(7, 42, fields, storage, 1_000)
    expect(emailDraftStorageKey(7, 42)).toBe('elfis.email-draft.7.42')
    const read = readEmailComposerDraft(7, 42, storage, 1_000)
    expect(read?.recipient).toBe('a@b.c')
    expect(read?.subject).toBe('Facture')
    expect(read?.organizationId).toBe(7)
    expect(read?.documentId).toBe(42)
    expect(readEmailComposerDraft(7, 99, storage, 1_000)).toBeNull()
    expect(readEmailComposerDraft(8, 42, storage, 1_000)).toBeNull()
  })

  it('expire les brouillons au-delà du TTL', () => {
    writeEmailComposerDraft(1, 2, fields, storage, 100)
    expect(isEmailDraftExpired(100, 100 + EMAIL_DRAFT_TTL_MS + 1)).toBe(true)
    expect(readEmailComposerDraft(1, 2, storage, 100)).not.toBeNull()
    expect(readEmailComposerDraft(1, 2, storage, 100 + EMAIL_DRAFT_TTL_MS + 1)).toBeNull()
  })

  it('clear supprime le brouillon', () => {
    writeEmailComposerDraft(3, 4, fields, storage)
    clearEmailComposerDraft(3, 4, storage)
    expect(readEmailComposerDraft(3, 4, storage)).toBeNull()
  })

  it('compare les champs draft', () => {
    expect(emailComposerFieldsEqual(fields, { ...fields })).toBe(true)
    expect(emailComposerFieldsEqual(fields, { ...fields, message: 'x' })).toBe(false)
  })

  it('ne stocke que des champs texte (pas de secrets)', () => {
    writeEmailComposerDraft(1, 1, fields, storage)
    const raw = storage.getItem(emailDraftStorageKey(1, 1)) || ''
    expect(raw).not.toMatch(/token|brevo|password|smtp|base64|pdf/i)
    expect(JSON.parse(raw)).not.toHaveProperty('token')
  })
})

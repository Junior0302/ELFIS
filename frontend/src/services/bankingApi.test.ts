import { describe, expect, it, vi, beforeEach } from 'vitest'
import {
  accountTypeLabel,
  bankingApi,
  connectionStatusLabel,
  syncStatusLabel,
} from '../services/bankingApi'

function mockFetch(payload: unknown, ok = true, status = 200) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok,
      status,
      text: async () => JSON.stringify(payload),
    }),
  )
}

describe('banking API', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('liste les connecteurs et connexions', async () => {
    mockFetch({
      providers: [
        { provider: 'demo', display_name: 'Banque Démo', configured: true, status: 'ok', message: '' },
      ],
      connections: [],
    })
    const data = await bankingApi.listConnectors('tok', 1)
    expect(data.providers[0].provider).toBe('demo')
    expect(data.connections).toEqual([])
  })

  it('connecte une banque via un fournisseur', async () => {
    mockFetch({
      ok: true,
      connection: { id: 1, provider: 'demo', bank_name: 'Banque Démo', status: 'connected', sync_interval_minutes: 1440, created_at: '2026-07-26' },
      accounts: [],
      message: 'Banque connectée via demo.',
    })
    const res = await bankingApi.connect('tok', 1, 'demo', 'Ma banque')
    expect(res.ok).toBe(true)
    expect(res.connection.status).toBe('connected')
    const call = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0]
    expect(String(call[0])).toContain('/banking/connectors/connect')
    expect(JSON.parse(call[1].body)).toEqual({ provider: 'demo', bank_name: 'Ma banque' })
  })

  it('déclenche une synchronisation et lit le journal', async () => {
    mockFetch({
      ok: true,
      runs: [
        {
          id: 'r1',
          connection_id: 1,
          provider: 'demo',
          sync_type: 'initial',
          trigger: 'manual',
          status: 'completed',
          accounts_synced: 1,
          transactions_created: 10,
          transactions_updated: 0,
          duplicates_skipped: 0,
          attempt_count: 1,
          max_attempts: 3,
          resumed_from_cursor: false,
          started_at: '2026-07-26T10:00:00Z',
        },
      ],
    })
    const res = await bankingApi.triggerSync('tok', 1)
    expect(res.runs[0].transactions_created).toBe(10)
    expect(res.runs[0].status).toBe('completed')
  })

  it('filtre les transactions', async () => {
    mockFetch({ items: [], total: 0, limit: 100, offset: 0 })
    await bankingApi.listTransactions('tok', 1, { q: 'loyer', category: 'loyer', limit: 50 })
    const call = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0]
    const url = String(call[0])
    expect(url).toContain('q=loyer')
    expect(url).toContain('category=loyer')
    expect(url).toContain('limit=50')
  })

  it('remonte les erreurs API avec le message backend', async () => {
    mockFetch({ detail: 'Fournisseur inconnu' }, false, 400)
    await expect(bankingApi.connect('tok', 1, 'inconnu')).rejects.toThrow('Fournisseur inconnu')
  })

  it('traduit les statuts', () => {
    expect(syncStatusLabel('completed')).toBe('Terminée')
    expect(connectionStatusLabel('connected')).toBe('Connectée')
    expect(connectionStatusLabel('error')).toBe('Erreur')
    expect(connectionStatusLabel('preparing')).toBe('Connexion en préparation')
    expect(connectionStatusLabel('awaiting_consent')).toBe('En attente du consentement')
    expect(connectionStatusLabel('disconnected')).toBe('Déconnectée')
    expect(accountTypeLabel('checking')).toBe('Compte courant')
    expect(accountTypeLabel('savings')).toBe('Épargne')
    expect(accountTypeLabel('card')).toBe('Carte')
    expect(accountTypeLabel('loan')).toBe('Crédit')
    expect(accountTypeLabel('investment')).toBe('Investissement')
    expect(accountTypeLabel('inconnu')).toBe('Autre')
  })

  it('expose uniquement l’URL temporaire Bridge, sans secret', async () => {
    mockFetch({
      ok: true,
      redirect_url: 'https://connect.bridgeapi.io/session/abc',
      connection: {
        id: 2,
        provider: 'bridge',
        bank_name: 'Bridge',
        status: 'awaiting_consent',
        sync_interval_minutes: 1440,
        created_at: '2026-08-23',
      },
      accounts: [],
      message: 'Redirection vers le consentement bancaire.',
    })
    const res = await bankingApi.connect('tok', 1, 'bridge')
    expect(res.redirect_url).toBe('https://connect.bridgeapi.io/session/abc')
    expect(JSON.stringify(res)).not.toMatch(/client_secret|access_token|Client-Secret/i)
  })
})

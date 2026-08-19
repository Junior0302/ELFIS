import { useCallback, useEffect, useMemo, useState } from 'react'
import { useAuth } from '../auth'
import {
  bankingApi,
  connectionStatusLabel,
  syncStatusLabel,
  type BankAccount,
  type BankConnection,
  type BankingHealth,
  type BankingProvider,
  type BankingStatus,
  type BankTransaction,
  type SyncRun,
} from '../services/bankingApi'

type Tab = 'banques' | 'comptes' | 'transactions' | 'synchronisation' | 'connexions'

const TABS: Array<{ id: Tab; label: string }> = [
  { id: 'banques', label: 'Banques' },
  { id: 'comptes', label: 'Comptes' },
  { id: 'transactions', label: 'Transactions' },
  { id: 'synchronisation', label: 'Synchronisation' },
  { id: 'connexions', label: 'État des connexions' },
]

function fmtDate(value?: string | null): string {
  if (!value) return '—'
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString('fr-FR')
}

function fmtAmount(amount: number, currency: string): string {
  try {
    return new Intl.NumberFormat('fr-FR', { style: 'currency', currency }).format(amount)
  } catch {
    return `${amount.toFixed(2)} ${currency}`
  }
}

export default function BankingPage() {
  const { token, orgId } = useAuth()
  const [tab, setTab] = useState<Tab>('banques')
  const [error, setError] = useState('')
  const [info, setInfo] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)

  const [providers, setProviders] = useState<BankingProvider[]>([])
  const [connections, setConnections] = useState<BankConnection[]>([])
  const [accounts, setAccounts] = useState<BankAccount[]>([])
  const [transactions, setTransactions] = useState<BankTransaction[]>([])
  const [txTotal, setTxTotal] = useState(0)
  const [txSearch, setTxSearch] = useState('')
  const [runs, setRuns] = useState<SyncRun[]>([])
  const [status, setStatus] = useState<BankingStatus | null>(null)
  const [health, setHealth] = useState<BankingHealth | null>(null)
  const [selectedProvider, setSelectedProvider] = useState('')
  const [bankName, setBankName] = useState('')

  const load = useCallback(async () => {
    if (!token || orgId == null) return
    setLoading(true)
    setError('')
    try {
      const [connectors, accs, txs, syncRuns, st, hl] = await Promise.all([
        bankingApi.listConnectors(token, orgId),
        bankingApi.listAccounts(token, orgId),
        bankingApi.listTransactions(token, orgId, { limit: 100 }),
        bankingApi.listSyncRuns(token, orgId),
        bankingApi.status(token, orgId),
        bankingApi.health(token, orgId),
      ])
      setProviders(connectors.providers)
      setConnections(connectors.connections)
      setAccounts(accs.items)
      setTransactions(txs.items)
      setTxTotal(txs.total)
      setRuns(syncRuns.items)
      setStatus(st)
      setHealth(hl)
      if (!selectedProvider && connectors.providers.length) {
        const usable = connectors.providers.find((p) => p.status === 'ok')
        setSelectedProvider(usable?.provider || connectors.providers[0].provider)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Impossible de charger les données bancaires')
    } finally {
      setLoading(false)
    }
  }, [token, orgId, selectedProvider])

  useEffect(() => {
    void load()
  }, [load])

  async function connect() {
    if (!token || orgId == null || !selectedProvider) return
    setBusy(true)
    setError('')
    setInfo('')
    try {
      const res = await bankingApi.connect(token, orgId, selectedProvider, bankName)
      setInfo(res.message)
      await load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Connexion impossible')
    } finally {
      setBusy(false)
    }
  }

  async function disconnect(connection: BankConnection) {
    if (!token || orgId == null) return
    if (!window.confirm(`Déconnecter ${connection.bank_name} ?`)) return
    setBusy(true)
    setError('')
    setInfo('')
    try {
      const res = await bankingApi.disconnect(token, orgId, connection.id)
      setInfo(res.message)
      await load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Déconnexion impossible')
    } finally {
      setBusy(false)
    }
  }

  async function sync(connectionId?: number) {
    if (!token || orgId == null) return
    setBusy(true)
    setError('')
    setInfo('')
    try {
      const res = await bankingApi.triggerSync(token, orgId, connectionId)
      const created = res.runs.reduce((n, r) => n + r.transactions_created, 0)
      const updated = res.runs.reduce((n, r) => n + r.transactions_updated, 0)
      setInfo(
        res.ok
          ? `Synchronisation terminée : ${created} créée(s), ${updated} mise(s) à jour.`
          : 'Synchronisation partielle — consultez le journal.',
      )
      await load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Synchronisation impossible')
    } finally {
      setBusy(false)
    }
  }

  async function searchTransactions() {
    if (!token || orgId == null) return
    setBusy(true)
    try {
      const txs = await bankingApi.listTransactions(token, orgId, {
        q: txSearch,
        limit: 100,
      })
      setTransactions(txs.items)
      setTxTotal(txs.total)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Recherche impossible')
    } finally {
      setBusy(false)
    }
  }

  const hasActiveConnection = useMemo(
    () => connections.some((c) => c.status !== 'disconnected'),
    [connections],
  )

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Banque</h2>
          <p>
            Connexions bancaires, comptes, transactions normalisées et synchronisation — le
            Banking Engine est la source de vérité, quel que soit le fournisseur.
          </p>
        </div>
        {hasActiveConnection ? (
          <button type="button" className="btn" disabled={busy} onClick={() => void sync()}>
            Synchroniser maintenant
          </button>
        ) : null}
      </div>

      {status ? (
        <div className="panel" style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap' }}>
          <div>
            <strong>{status.connections_connected}</strong>
            <p className="muted">Banque(s) connectée(s)</p>
          </div>
          <div>
            <strong>{status.accounts_total}</strong>
            <p className="muted">Compte(s)</p>
          </div>
          <div>
            <strong>{status.transactions_total}</strong>
            <p className="muted">Transaction(s)</p>
          </div>
          <div>
            <strong>
              {Object.entries(status.balances_by_currency)
                .map(([cur, bal]) => fmtAmount(bal, cur))
                .join(' · ') || '—'}
            </strong>
            <p className="muted">Solde total</p>
          </div>
          <div>
            <strong>{fmtDate(status.last_sync_at)}</strong>
            <p className="muted">Dernière synchronisation</p>
          </div>
          <div>
            <strong>{fmtDate(status.next_sync_at)}</strong>
            <p className="muted">Prochaine synchronisation</p>
          </div>
        </div>
      ) : null}

      <div style={{ display: 'flex', gap: '0.5rem', margin: '1rem 0', flexWrap: 'wrap' }}>
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            className={tab === t.id ? 'btn' : 'btn secondary'}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {error ? <div className="panel form-error">{error}</div> : null}
      {info ? <div className="panel">{info}</div> : null}
      {loading ? <div className="loading">Chargement des données bancaires…</div> : null}

      {!loading && tab === 'banques' ? (
        <>
          <div className="panel">
            <h3>Connecter une banque</h3>
            <p className="muted">
              Choisissez un fournisseur : ils sont interchangeables, les données restent au même
              format.
            </p>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
              <select
                value={selectedProvider}
                onChange={(e) => setSelectedProvider(e.target.value)}
                aria-label="Fournisseur"
              >
                {providers.map((p) => (
                  <option key={p.provider} value={p.provider} disabled={p.status === 'not_configured'}>
                    {p.display_name}
                    {p.status === 'not_configured' ? ' (non configuré)' : ''}
                  </option>
                ))}
              </select>
              <input
                type="text"
                placeholder="Nom de la banque (optionnel)"
                value={bankName}
                onChange={(e) => setBankName(e.target.value)}
              />
              <button type="button" className="btn" disabled={busy || !selectedProvider} onClick={() => void connect()}>
                Connecter
              </button>
            </div>
          </div>

          {connections.length ? (
            <div className="list">
              {connections.map((c) => (
                <div key={c.id} className="list-item">
                  <div>
                    <strong>{c.bank_name}</strong>
                    <p className="muted">
                      Fournisseur : {c.provider} · {connectionStatusLabel(c.status)} · Dernière
                      sync : {fmtDate(c.last_sync_at)}
                    </p>
                    {c.error_message ? <p className="form-error">{c.error_message}</p> : null}
                  </div>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    {c.status !== 'disconnected' ? (
                      <>
                        <button type="button" className="btn" disabled={busy} onClick={() => void sync(c.id)}>
                          Synchroniser
                        </button>
                        <button
                          type="button"
                          className="btn secondary"
                          disabled={busy}
                          onClick={() => void disconnect(c)}
                        >
                          Déconnecter
                        </button>
                      </>
                    ) : (
                      <span className="badge">Déconnectée</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="panel empty">
              <p>Aucune banque connectée pour le moment.</p>
            </div>
          )}
        </>
      ) : null}

      {!loading && tab === 'comptes' ? (
        accounts.length ? (
          <div className="panel" style={{ overflowX: 'auto' }}>
            <table className="entry-table">
              <thead>
                <tr>
                  <th>Compte</th>
                  <th>Banque</th>
                  <th>IBAN</th>
                  <th>Devise</th>
                  <th>Solde</th>
                  <th>Fournisseur</th>
                  <th>Dernière sync</th>
                </tr>
              </thead>
              <tbody>
                {accounts.map((a) => (
                  <tr key={a.id}>
                    <td>{a.label}</td>
                    <td>{a.bank_name}</td>
                    <td>{a.iban || '—'}</td>
                    <td>{a.currency}</td>
                    <td>{fmtAmount(a.balance, a.currency)}</td>
                    <td>{a.provider}</td>
                    <td>{fmtDate(a.last_sync_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="panel empty">
            <p>Aucun compte. Connectez une banque pour importer vos comptes.</p>
          </div>
        )
      ) : null}

      {!loading && tab === 'transactions' ? (
        <>
          <div className="panel" style={{ display: 'flex', gap: '0.5rem' }}>
            <input
              type="text"
              placeholder="Rechercher un libellé…"
              value={txSearch}
              onChange={(e) => setTxSearch(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') void searchTransactions()
              }}
            />
            <button type="button" className="btn secondary" disabled={busy} onClick={() => void searchTransactions()}>
              Rechercher
            </button>
            <span className="muted" style={{ alignSelf: 'center' }}>
              {txTotal} transaction(s)
            </span>
          </div>
          {transactions.length ? (
            <div className="panel" style={{ overflowX: 'auto' }}>
              <table className="entry-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Libellé</th>
                    <th>Montant</th>
                    <th>Catégorie</th>
                    <th>Statut</th>
                    <th>Source</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.map((t) => (
                    <tr key={t.id}>
                      <td>{t.booked_at}</td>
                      <td>
                        {t.label}
                        {t.is_duplicate ? <span className="badge"> doublon</span> : null}
                        {t.is_anomaly ? <span className="badge"> anomalie</span> : null}
                      </td>
                      <td style={{ color: t.amount < 0 ? '#b3261e' : '#0b3d2e' }}>
                        {fmtAmount(t.amount, t.currency)}
                      </td>
                      <td>{t.category}</td>
                      <td>{t.status === 'pending' ? 'En attente' : 'Comptabilisée'}</td>
                      <td>{t.source}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="panel empty">
              <p>Aucune transaction. Lancez une synchronisation.</p>
            </div>
          )}
        </>
      ) : null}

      {!loading && tab === 'synchronisation' ? (
        runs.length ? (
          <div className="panel" style={{ overflowX: 'auto' }}>
            <table className="entry-table">
              <thead>
                <tr>
                  <th>Démarrée</th>
                  <th>Type</th>
                  <th>Statut</th>
                  <th>Créées</th>
                  <th>Mises à jour</th>
                  <th>Doublons ignorés</th>
                  <th>Tentatives</th>
                  <th>Durée</th>
                  <th>Erreur</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((r) => (
                  <tr key={r.id}>
                    <td>{fmtDate(r.started_at)}</td>
                    <td>
                      {r.sync_type === 'initial' ? 'Initiale' : 'Incrémentale'}
                      {r.resumed_from_cursor ? ' (reprise)' : ''}
                    </td>
                    <td>{syncStatusLabel(r.status)}</td>
                    <td>{r.transactions_created}</td>
                    <td>{r.transactions_updated}</td>
                    <td>{r.duplicates_skipped}</td>
                    <td>
                      {r.attempt_count}/{r.max_attempts}
                    </td>
                    <td>{r.duration_ms != null ? `${Math.round(r.duration_ms)} ms` : '—'}</td>
                    <td>{r.error_message || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="panel empty">
            <p>Aucune synchronisation pour le moment.</p>
          </div>
        )
      ) : null}

      {!loading && tab === 'connexions' && health ? (
        <>
          <div className="panel">
            <h3>Fournisseurs</h3>
            <div className="list">
              {health.providers.map((p) => (
                <div key={p.provider} className="list-item">
                  <div>
                    <strong>{p.display_name}</strong>
                    <p className="muted">{p.message}</p>
                  </div>
                  <span className="badge">
                    {p.status === 'ok'
                      ? 'Opérationnel'
                      : p.status === 'not_configured'
                        ? 'Non configuré'
                        : 'Indisponible'}
                    {p.latency_ms != null ? ` · ${p.latency_ms} ms` : ''}
                  </span>
                </div>
              ))}
            </div>
          </div>
          {health.connections.length ? (
            <div className="panel" style={{ overflowX: 'auto' }}>
              <h3>Connexions</h3>
              <table className="entry-table">
                <thead>
                  <tr>
                    <th>Banque</th>
                    <th>Fournisseur</th>
                    <th>Statut</th>
                    <th>Dernière sync</th>
                    <th>Prochaine sync</th>
                    <th>Taux d'échec</th>
                    <th>Temps moyen</th>
                    <th>Dernière erreur</th>
                  </tr>
                </thead>
                <tbody>
                  {health.connections.map((c) => (
                    <tr key={c.connection_id}>
                      <td>{c.bank_name}</td>
                      <td>{c.provider}</td>
                      <td>{connectionStatusLabel(c.status)}</td>
                      <td>{fmtDate(c.last_sync_at)}</td>
                      <td>{fmtDate(c.next_sync_at)}</td>
                      <td>{Math.round(c.failure_rate * 100)} %</td>
                      <td>{c.avg_duration_ms != null ? `${Math.round(c.avg_duration_ms)} ms` : '—'}</td>
                      <td>{c.error_message || c.last_error || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </>
      ) : null}
    </>
  )
}

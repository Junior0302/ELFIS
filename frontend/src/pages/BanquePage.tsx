import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api, formatEuro, type BankOverview } from '../api'
import { useAuth } from '../auth'

export default function BanquePage() {
  const { token, orgId } = useAuth()
  const [data, setData] = useState<BankOverview | null>(null)
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [importing, setImporting] = useState(false)
  const [connecting, setConnecting] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [form, setForm] = useState({
    bank_name: '',
    label: 'Compte courant',
    iban: '',
    balance: 0,
  })

  const load = () => {
    setLoading(true)
    setError('')
    api
      .bankOverview(token, orgId)
      .then(setData)
      .catch((e) => setError(e.message || 'Erreur banque'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, orgId])

  const onConnect = async (e: FormEvent) => {
    e.preventDefault()
    setConnecting(true)
    setMessage('')
    setError('')
    try {
      const res = await api.bankConnect(form, token, orgId)
      setMessage(res.message)
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Connexion impossible')
    } finally {
      setConnecting(false)
    }
  }

  const onSync = async () => {
    setSyncing(true)
    setMessage('')
    setError('')
    try {
      const res = await api.bankSync(token, orgId)
      setMessage(res.message)
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sync impossible')
    } finally {
      setSyncing(false)
    }
  }

  const onImportCsv = async (file: File | null) => {
    if (!file || !token) return
    setImporting(true)
    setMessage('')
    setError('')
    try {
      const res = await api.bankImportCsv(file, token, orgId)
      setMessage(res.message)
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Import impossible')
    } finally {
      setImporting(false)
    }
  }

  if (loading && !data) return <div className="loading">Chargement banque…</div>

  const rawAccount = data?.account
  const isLegacyDemo =
    !!rawAccount &&
    (rawAccount.bank_name === 'Compte principal' ||
      rawAccount.bank_name.toLowerCase().includes('demo') ||
      rawAccount.label === 'Compte courant Pro' ||
      Math.abs(rawAccount.balance - 18450) < 0.01)
  const account = isLegacyDemo ? null : rawAccount
  const connected = Boolean(account?.connected)

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Banque</h2>
          <p>
            Enregistrez votre compte, puis importez l’export CSV réel de votre banque pour analyser
            les mouvements.
          </p>
        </div>
        <div className="actions" style={{ marginTop: 0 }}>
          {connected && (
            <button className="btn" type="button" onClick={onSync} disabled={syncing}>
              {syncing ? 'Sync…' : 'Synchroniser'}
            </button>
          )}
          <Link className="btn secondary" to="/tresorerie">
            Trésorerie
          </Link>
        </div>
      </div>

      {error && (
        <div className="panel form-error" style={{ marginBottom: '1rem' }}>
          {error}
        </div>
      )}
      {message && (
        <div className="auth-alert auth-alert-ok" style={{ marginBottom: '1rem' }}>
          {message}
        </div>
      )}

      {!connected ? (
        <form className="panel" onSubmit={onConnect}>
          <h3>Connecter un compte bancaire</h3>
          <p className="muted">
            Indiquez votre banque et le solde d’aujourd’hui. Vous pourrez ensuite importer vos
            mouvements depuis un fichier CSV.
          </p>
          <div className="form-grid">
            <div className="field">
              <label>Banque</label>
              <input
                required
                placeholder="BNP, Société Générale, Crédit Agricole…"
                value={form.bank_name}
                onChange={(e) => setForm({ ...form, bank_name: e.target.value })}
              />
            </div>
            <div className="field">
              <label>Libellé du compte</label>
              <input
                value={form.label}
                onChange={(e) => setForm({ ...form, label: e.target.value })}
              />
            </div>
            <div className="field">
              <label>IBAN (optionnel)</label>
              <input
                placeholder="FR76…"
                value={form.iban}
                onChange={(e) => setForm({ ...form, iban: e.target.value })}
              />
            </div>
            <div className="field">
              <label>Solde actuel (€)</label>
              <input
                type="number"
                step="0.01"
                value={form.balance}
                onChange={(e) => setForm({ ...form, balance: Number(e.target.value) })}
              />
            </div>
          </div>
          <div className="actions">
            <button className="btn" type="submit" disabled={connecting}>
              {connecting ? 'Connexion…' : 'Connecter mon compte'}
            </button>
          </div>
        </form>
      ) : (
        <>
          <section className="panel bank-import-panel">
            <div>
              <h3>Importer les mouvements réels</h3>
              <p className="muted">
                Exportez un CSV depuis votre banque avec les colonnes date, libellé et montant
                (ou débit/crédit). Aucun mouvement n’est inventé.
              </p>
            </div>
            <label className="btn" htmlFor="bank_csv">
              {importing ? 'Import…' : 'Choisir un CSV'}
            </label>
            <input
              id="bank_csv"
              className="visually-hidden"
              type="file"
              accept=".csv,text/csv"
              disabled={importing}
              onChange={(event) => void onImportCsv(event.target.files?.[0] || null)}
            />
          </section>

          <div className="stats">
            <div className="stat">
              <span>Solde</span>
              <strong>{formatEuro(account!.balance)}</strong>
            </div>
            <div className="stat">
              <span>Encaissements</span>
              <strong>{formatEuro(data!.stats.credits)}</strong>
            </div>
            <div className="stat">
              <span>Décaissements</span>
              <strong>{formatEuro(data!.stats.debits)}</strong>
            </div>
            <div className="stat">
              <span>Opérations</span>
              <strong>{isLegacyDemo ? 0 : data!.stats.count}</strong>
            </div>
          </div>

          <section className="panel">
            <h3>Mouvements</h3>
            {(isLegacyDemo ? [] : data!.transactions).length === 0 ? (
              <div className="empty">
                Aucun mouvement pour le moment.
                <p className="muted" style={{ marginTop: '0.75rem' }}>
                  Cliquez sur Synchroniser quand Open Banking sera disponible, ou continuez avec les
                  factures déposées.
                </p>
              </div>
            ) : (
              <div className="list">
                {data!.transactions.map((tx) => (
                  <div key={tx.id} className="list-item bank-row">
                    <div>
                      <strong>{tx.label}</strong>
                      <span>
                        {tx.booked_at} · {tx.category}
                      </span>
                    </div>
                    <div className={tx.amount >= 0 ? 'amount-pos' : 'amount-neg'}>
                      <strong>{formatEuro(tx.amount)}</strong>
                    </div>
                    <div>
                      {tx.reconciled ? (
                        <span className="badge">Rapproché</span>
                      ) : (
                        <span className="badge warn">Ouvert</span>
                      )}
                    </div>
                    <div>
                      {tx.is_duplicate && <span className="badge danger">Doublon</span>}
                      {tx.is_anomaly && !tx.is_duplicate && (
                        <span className="badge danger">Anomalie</span>
                      )}
                    </div>
                    <div className="muted">{tx.anomaly_reason || '—'}</div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </>
  )
}

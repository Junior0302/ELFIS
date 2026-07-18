import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type ProfessionalEmailRecord } from '../../api'
import { useAuth } from '../../auth'

function formatWhen(value?: string | null) {
  if (!value) return '—'
  try {
    return new Intl.DateTimeFormat('fr-FR', {
      dateStyle: 'short',
      timeStyle: 'short',
    }).format(new Date(value))
  } catch {
    return value
  }
}

function statusLabel(status: string) {
  const map: Record<string, string> = {
    pending: 'En attente',
    creating: 'Configuration',
    active: 'Active',
    suspended: 'Suspendue',
    rejected: 'Refusée',
  }
  return map[status] || status
}

function statusPillClass(status: string) {
  if (status === 'active') return 'platform-pill'
  if (status === 'pending' || status === 'creating') return 'platform-pill platform-pill-warn'
  if (status === 'suspended' || status === 'rejected') return 'platform-pill platform-pill-danger'
  return 'platform-pill'
}

type Counts = {
  all: number
  pending: number
  creating: number
  active: number
  suspended: number
  rejected: number
}

type MailStatus = {
  configured: boolean
  transport: string
  has_brevo_api_key: boolean
  brevo_key_looks_valid?: boolean
  brevo_key_prefix?: string
  brevo_key_suffix?: string
  brevo_key_length?: number
  has_platform_from: boolean
  platform_from: string
  notify_to: string
  hint: string
  brevo_ok?: boolean
  brevo_error?: string
  brevo_account_email?: string
}

export default function PlatformProfessionalEmailsPage() {
  const { token } = useAuth()
  const [items, setItems] = useState<ProfessionalEmailRecord[]>([])
  const [counts, setCounts] = useState<Counts | null>(null)
  const [filter, setFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [pendingId, setPendingId] = useState<number | null>(null)
  const [emailDrafts, setEmailDrafts] = useState<Record<number, string>>({})
  const [mailStatus, setMailStatus] = useState<MailStatus | null>(null)

  const load = (statusFilter = filter) => {
    if (!token) return
    setLoading(true)
    api
      .platformProfessionalEmailRequests(token, statusFilter || undefined)
      .then((res) => {
        setItems(res.requests)
        if (res.counts) setCounts(res.counts)
        const drafts: Record<number, string> = {}
        for (const row of res.requests) {
          drafts[row.id] = row.email || row.suggested_email || ''
        }
        setEmailDrafts(drafts)
      })
      .catch((reason) => setError(reason instanceof Error ? reason.message : 'Liste indisponible'))
      .finally(() => setLoading(false))
    api
      .platformEmailStatus(token)
      .then(setMailStatus)
      .catch(() => setMailStatus(null))
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  const activate = async (row: ProfessionalEmailRecord) => {
    if (!token) return
    const email = (emailDrafts[row.id] || row.suggested_email || '').trim()
    if (!email) {
      setError('Indiquez l’adresse créée dans Brevo.')
      return
    }
    if (
      !window.confirm(
        `Valider ${email} ?\n\nCréez d’abord la boîte dans Brevo (envoi + réception).`,
      )
    )
      return
    setPendingId(row.id)
    setError('')
    setMessage('')
    try {
      await api.platformActivateProfessionalEmail(row.id, { email, make_default: true }, token)
      setMessage(`Adresse ${email} activée.`)
      load()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Activation impossible')
    } finally {
      setPendingId(null)
    }
  }

  const reject = async (row: ProfessionalEmailRecord) => {
    if (!token) return
    if (!window.confirm('Refuser cette demande ?')) return
    setPendingId(row.id)
    try {
      await api.platformRejectProfessionalEmail(row.id, { notes: 'Refusée' }, token)
      setMessage('Demande refusée.')
      load()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Refus impossible')
    } finally {
      setPendingId(null)
    }
  }

  const suspend = async (row: ProfessionalEmailRecord) => {
    if (!token) return
    if (!window.confirm(`Suspendre ${row.email} ?`)) return
    setPendingId(row.id)
    try {
      await api.platformSuspendProfessionalEmail(row.id, { notes: 'Suspendue' }, token)
      setMessage('Adresse suspendue.')
      load()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Suspension impossible')
    } finally {
      setPendingId(null)
    }
  }

  const resend = async (row: ProfessionalEmailRecord) => {
    if (!token) return
    setPendingId(row.id)
    setError('')
    setMessage('')
    try {
      const res = await api.platformResendProfessionalEmail(row.id, token)
      if (res.notify.admin_notified) {
        setMessage(`Mails renvoyés vers ${res.notify.notify_to || 'urequest@'} et le client.`)
      } else {
        setError(res.notify.error || 'Échec d’envoi des mails automatiques.')
      }
      load()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Renvoi impossible')
    } finally {
      setPendingId(null)
    }
  }

  const resetOne = async (row: ProfessionalEmailRecord) => {
    if (!token) return
    if (
      !window.confirm(
        `Réinitialiser la demande de ${row.user?.email || row.id} ?\nLe client pourra redemander.`,
      )
    )
      return
    setPendingId(row.id)
    try {
      await api.platformResetProfessionalEmail(row.id, token)
      setMessage('Demande réinitialisée.')
      load()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Réinitialisation impossible')
    } finally {
      setPendingId(null)
    }
  }

  const resetAll = async () => {
    if (!token) return
    if (!window.confirm('Réinitialiser TOUTES les demandes e-mail pro ?')) return
    setPendingId(-1)
    setError('')
    setMessage('')
    try {
      const res = await api.platformResetAllProfessionalEmails(token)
      setMessage(`${res.deleted_count} demande(s) supprimée(s).`)
      load()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Réinitialisation globale impossible')
    } finally {
      setPendingId(null)
    }
  }

  return (
    <>
      <div className="platform-title platform-title-row">
        <div>
          <span>ELF Admin</span>
          <h1>Emails professionnels</h1>
          <p>
            Demandes d’adresses @elfis-core.com · validation Brevo · activation pour devis / factures.
          </p>
        </div>
        <div className="platform-title-actions">
          <a
            className="platform-action platform-action-primary"
            href="https://app.brevo.com/"
            target="_blank"
            rel="noreferrer"
          >
            Ouvrir Brevo
          </a>
          <Link className="platform-action" to="/elfadmin/utilisateurs">
            Utilisateurs
          </Link>
          <button
            type="button"
            className="platform-action platform-action-danger"
            disabled={pendingId === -1}
            onClick={() => void resetAll()}
          >
            {pendingId === -1 ? '…' : 'Tout réinitialiser'}
          </button>
        </div>
      </div>

      {mailStatus && (
        <div
          className={`platform-alert ${mailStatus.brevo_ok ? 'platform-alert-ok' : ''}`}
          role="status"
        >
          {mailStatus.brevo_ok ? (
            <>
              <strong>Brevo OK — clé acceptée</strong>
              <span>
                Compte Brevo : <code>{mailStatus.brevo_account_email || '—'}</code>
              </span>
              <span>
                De <code>{mailStatus.platform_from || '—'}</code> →{' '}
                <code>{mailStatus.notify_to}</code>
              </span>
            </>
          ) : (
            <>
              <strong>Brevo KO — la clé est refusée</strong>
              <span>{mailStatus.brevo_error || mailStatus.hint}</span>
              <span>
                Clé vue par le serveur :{' '}
                <code>
                  {mailStatus.brevo_key_prefix || '…'}…{mailStatus.brevo_key_suffix || ''}
                </code>{' '}
                ({mailStatus.brevo_key_length || 0} car.)
                {mailStatus.brevo_key_looks_valid === false
                  ? ' — format suspect (doit commencer par xkeysib-)'
                  : ''}
              </span>
              <span>
                From : <code>{mailStatus.platform_from || 'vide'}</code> · Régénérez la clé API dans
                Brevo, recollez-la dans Render <code>BREVO_API_KEY</code> sans guillemets, puis
                Manual Deploy.
              </span>
            </>
          )}
        </div>
      )}

      {error && <div className="platform-alert">{error}</div>}
      {message && <div className="platform-alert platform-alert-ok">{message}</div>}

      {counts && (
        <div className="platform-stats platform-stats-5">
          <article>
            <span>Total</span>
            <strong>{counts.all}</strong>
          </article>
          <article>
            <span>En attente</span>
            <strong>{counts.pending}</strong>
          </article>
          <article>
            <span>Actives</span>
            <strong>{counts.active}</strong>
          </article>
          <article>
            <span>Suspendues</span>
            <strong>{counts.suspended}</strong>
          </article>
          <article>
            <span>Refusées</span>
            <strong>{counts.rejected}</strong>
          </article>
        </div>
      )}

      <div className="platform-toolbar">
        <label className="platform-field">
          <span>Filtrer</span>
          <select
            value={filter}
            onChange={(e) => {
              const next = e.target.value
              setFilter(next)
              load(next)
            }}
          >
            <option value="">Tous les états</option>
            <option value="pending">En attente</option>
            <option value="creating">Configuration</option>
            <option value="active">Actives</option>
            <option value="suspended">Suspendues</option>
            <option value="rejected">Refusées</option>
          </select>
        </label>
        <button type="button" className="platform-action" onClick={() => load()}>
          Actualiser
        </button>
      </div>

      {loading ? (
        <div className="platform-loading">Chargement des demandes…</div>
      ) : items.length === 0 ? (
        <div className="platform-loading platform-empty">Aucune demande pour le moment.</div>
      ) : (
        <div className="platform-request-list">
          {items.map((row) => {
            const snap = row.request_snapshot || {}
            const name =
              `${row.user?.first_name || snap.first_name || ''} ${row.user?.last_name || snap.last_name || ''}`.trim() ||
              row.user?.email ||
              '—'
            const busy = pendingId === row.id
            const proposed = row.suggested_email || emailDrafts[row.id] || ''
            return (
              <article key={row.id} className="platform-request-card">
                <header className="platform-request-head">
                  <div>
                    <h2>{name}</h2>
                    <p>{row.user?.email || (snap.current_email as string) || '—'}</p>
                  </div>
                  <span className={statusPillClass(row.status)}>{statusLabel(row.status)}</span>
                </header>

                <dl className="platform-request-meta">
                  <div>
                    <dt>Compte</dt>
                    <dd>{row.user?.status || '—'}</dd>
                  </div>
                  <div>
                    <dt>Abonnement</dt>
                    <dd>{(snap.subscription as string) || '—'}</dd>
                  </div>
                  <div>
                    <dt>Demandé le</dt>
                    <dd>{formatWhen(row.created_at)}</dd>
                  </div>
                  <div>
                    <dt>Adresse proposée</dt>
                    <dd>
                      <code>{proposed || '—'}</code>
                    </dd>
                  </div>
                  {row.email ? (
                    <div>
                      <dt>Adresse active</dt>
                      <dd>
                        <code>{row.email}</code>
                      </dd>
                    </div>
                  ) : null}
                </dl>

                {(row.status === 'pending' || row.status === 'creating') && (
                  <label className="platform-field platform-field-grow">
                    <span>Adresse créée dans Brevo</span>
                    <input
                      value={emailDrafts[row.id] || ''}
                      onChange={(e) =>
                        setEmailDrafts((current) => ({ ...current, [row.id]: e.target.value }))
                      }
                      placeholder="prenom.nom@elfis-core.com"
                    />
                  </label>
                )}

                <footer className="platform-request-actions">
                  {(row.status === 'pending' || row.status === 'creating') && (
                    <>
                      <button
                        type="button"
                        className="platform-action platform-action-primary"
                        disabled={busy}
                        onClick={() => void activate(row)}
                      >
                        {busy ? '…' : 'Valider'}
                      </button>
                      <button
                        type="button"
                        className="platform-action"
                        disabled={busy}
                        onClick={() => void reject(row)}
                      >
                        Refuser
                      </button>
                    </>
                  )}
                  {row.status === 'active' && (
                    <button
                      type="button"
                      className="platform-action"
                      disabled={busy}
                      onClick={() => void suspend(row)}
                    >
                      Suspendre
                    </button>
                  )}
                  <button
                    type="button"
                    className="platform-action"
                    disabled={busy}
                    onClick={() => void resend(row)}
                  >
                    Renvoyer mails
                  </button>
                  <button
                    type="button"
                    className="platform-action platform-action-danger"
                    disabled={busy}
                    onClick={() => void resetOne(row)}
                  >
                    Réinit. demande
                  </button>
                </footer>
              </article>
            )
          })}
        </div>
      )}
    </>
  )
}

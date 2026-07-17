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
    active: 'Adresse créée',
    suspended: 'Suspendue',
    rejected: 'Refusée',
  }
  return map[status] || status
}

type Counts = {
  all: number
  pending: number
  creating: number
  active: number
  suspended: number
  rejected: number
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
    const ok = window.confirm(
      `Valider ${email} ?\n\nAssurez-vous d’avoir créé la boîte dans Brevo (SMTP/IMAP) avant de valider.`,
    )
    if (!ok) return
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
    if (!window.confirm(`Suspendre l’adresse ${row.email} ? Elle ne pourra plus servir d’expéditeur.`))
      return
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

  const resetOne = async (row: ProfessionalEmailRecord) => {
    if (!token) return
    if (
      !window.confirm(
        `Réinitialiser la demande de ${row.user?.email || row.id} ?\nLe client pourra refaire une demande.`,
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
    if (
      !window.confirm(
        'Réinitialiser TOUTES les demandes e-mail pro ?\nCette action est définitive (tests / reprise à zéro).',
      )
    )
      return
    setPendingId(-1)
    setError('')
    setMessage('')
    try {
      const res = await api.platformResetAllProfessionalEmails(token)
      setMessage(`${res.deleted_count} demande(s) supprimée(s). Les users peuvent redemander.`)
      load()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Réinitialisation globale impossible')
    } finally {
      setPendingId(null)
    }
  }

  return (
    <div>
      <div className="page-head">
        <div>
          <h2>Demandes Email Professionnel</h2>
          <p className="muted">
            Suivi des états : en attente → Brevo → validation → active. Réinitialisez une demande ou
            toutes pour les tests. Comptes users :{' '}
            <Link to="/elfadmin/utilisateurs">Utilisateurs</Link> (suspendre / bannir).
          </p>
          <p className="muted" style={{ marginTop: '0.35rem' }}>
            Lien admin :{' '}
            <a href="https://elfis-core.com/elfadmin/emails-pro">
              https://elfis-core.com/elfadmin/emails-pro
            </a>
            {' · '}
            <a href="https://app.brevo.com/" target="_blank" rel="noreferrer">
              Ouvrir Brevo
            </a>
          </p>
        </div>
        <div className="actions" style={{ margin: 0 }}>
          <button
            type="button"
            className="btn secondary"
            disabled={pendingId === -1}
            onClick={() => void resetAll()}
          >
            {pendingId === -1 ? '…' : 'Réinitialiser toutes les demandes'}
          </button>
        </div>
      </div>

      {counts && (
        <div className="stats" style={{ marginBottom: '1rem' }}>
          <div className="stat">
            <span>Total</span>
            <strong>{counts.all}</strong>
          </div>
          <div className="stat">
            <span>En attente</span>
            <strong>{counts.pending}</strong>
          </div>
          <div className="stat">
            <span>Actives</span>
            <strong>{counts.active}</strong>
          </div>
          <div className="stat">
            <span>Suspendues</span>
            <strong>{counts.suspended}</strong>
          </div>
          <div className="stat">
            <span>Refusées</span>
            <strong>{counts.rejected}</strong>
          </div>
        </div>
      )}

      <div className="sales-filters" style={{ marginBottom: '1rem' }}>
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
        <button className="btn secondary" type="button" onClick={() => load()}>
          Actualiser
        </button>
      </div>

      {error && <p className="form-error">{error}</p>}
      {message && <p className="muted">{message}</p>}
      {loading ? (
        <p className="muted">Chargement…</p>
      ) : items.length === 0 ? (
        <p className="muted">Aucune demande pour le moment.</p>
      ) : (
        <div className="list">
          {items.map((row) => {
            const snap = row.request_snapshot || {}
            const name =
              `${row.user?.first_name || snap.first_name || ''} ${row.user?.last_name || snap.last_name || ''}`.trim() ||
              row.user?.email ||
              '—'
            const userStatus = row.user?.status || ''
            return (
              <div
                key={row.id}
                className="list-item"
                style={{ gridTemplateColumns: '1fr auto', alignItems: 'start' }}
              >
                <div>
                  <strong>{name}</strong>
                  <span>
                    Compte user : {userStatus || '—'} · Demande : {statusLabel(row.status)} ·{' '}
                    {(snap.subscription as string) || '—'} · {formatWhen(row.created_at)}
                    {row.suggested_email ? ` · Proposé : ${row.suggested_email}` : ''}
                    {row.email ? ` · Adresse : ${row.email}` : ''}
                    {row.user?.email ? ` · ${row.user.email}` : ''}
                  </span>
                  {(row.status === 'pending' || row.status === 'creating') && (
                    <div className="field" style={{ marginTop: '0.65rem', maxWidth: 360 }}>
                      <label>Adresse créée dans Brevo</label>
                      <input
                        value={emailDrafts[row.id] || ''}
                        onChange={(e) =>
                          setEmailDrafts((current) => ({ ...current, [row.id]: e.target.value }))
                        }
                        placeholder="prenom.nom@elfis-core.com"
                      />
                    </div>
                  )}
                </div>
                <div className="actions" style={{ margin: 0, flexWrap: 'wrap' }}>
                  {(row.status === 'pending' || row.status === 'creating') && (
                    <>
                      <button
                        type="button"
                        className="btn"
                        disabled={pendingId === row.id}
                        onClick={() => void activate(row)}
                      >
                        {pendingId === row.id ? '…' : 'Valider'}
                      </button>
                      <button
                        type="button"
                        className="btn secondary"
                        disabled={pendingId === row.id}
                        onClick={() => void reject(row)}
                      >
                        Refuser
                      </button>
                    </>
                  )}
                  {row.status === 'active' && (
                    <>
                      <span className="badge">✓ Active</span>
                      <button
                        type="button"
                        className="btn secondary"
                        disabled={pendingId === row.id}
                        onClick={() => void suspend(row)}
                      >
                        Suspendre adresse
                      </button>
                    </>
                  )}
                  {row.status === 'suspended' && <span className="badge warn">Suspendue</span>}
                  <button
                    type="button"
                    className="btn secondary"
                    disabled={pendingId === row.id}
                    onClick={() => void resetOne(row)}
                  >
                    Réinit. demande
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

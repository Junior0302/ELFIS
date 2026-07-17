import { useEffect, useState } from 'react'
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

export default function PlatformProfessionalEmailsPage() {
  const { token } = useAuth()
  const [items, setItems] = useState<ProfessionalEmailRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [pendingId, setPendingId] = useState<number | null>(null)
  const [emailDrafts, setEmailDrafts] = useState<Record<number, string>>({})

  const load = () => {
    if (!token) return
    setLoading(true)
    api
      .platformProfessionalEmailRequests(token)
      .then((res) => {
        setItems(res.requests)
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

  return (
    <div>
      <div className="page-head">
        <div>
          <h2>Demandes Email Professionnel</h2>
          <p className="muted">
            1) Le client demande son adresse depuis Mon compte → mail à urequest@elfis-core.com.
            2) Vous créez la boîte dans Brevo (SMTP/IMAP, envoi + réception).
            3) Vous validez ici → l’adresse apparaît comme expéditeur dans Devis / Factures (envoi
            direct).
          </p>
          <p className="muted" style={{ marginTop: '0.35rem' }}>
            <a href="https://app.brevo.com/" target="_blank" rel="noreferrer">
              Ouvrir Brevo
            </a>
          </p>
        </div>
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
            return (
              <div
                key={row.id}
                className="list-item"
                style={{ gridTemplateColumns: '1fr auto', alignItems: 'start' }}
              >
                <div>
                  <strong>{name}</strong>
                  <span>
                    {(snap.subscription as string) || '—'} · {statusLabel(row.status)} ·{' '}
                    {formatWhen(row.created_at)}
                    {row.suggested_email ? ` · Proposé : ${row.suggested_email}` : ''}
                    {row.email && row.status === 'active' ? ` · Actif : ${row.email}` : ''}
                  </span>
                  {row.status === 'pending' || row.status === 'creating' ? (
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
                  ) : null}
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
                        {pendingId === row.id ? '…' : 'Créer / Valider'}
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
                  {row.status === 'active' && <span className="badge">✓ Adresse créée</span>}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

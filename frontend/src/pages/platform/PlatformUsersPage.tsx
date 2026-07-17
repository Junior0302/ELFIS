import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type PlatformUser } from '../../api'
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
  if (status === 'active') return 'Actif'
  if (status === 'suspended') return 'Suspendu'
  if (status === 'banned') return 'Banni'
  return status
}

export default function PlatformUsersPage() {
  const { token, user: me } = useAuth()
  const [items, setItems] = useState<PlatformUser[]>([])
  const [loading, setLoading] = useState(true)
  const [pendingId, setPendingId] = useState<number | null>(null)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  useEffect(() => {
    if (!token) return
    api
      .platformUsers(token)
      .then((result) => setItems(result.users))
      .catch((reason) => setError(reason instanceof Error ? reason.message : 'Liste indisponible'))
      .finally(() => setLoading(false))
  }, [token])

  const updateStatus = async (item: PlatformUser, status: 'active' | 'suspended' | 'banned') => {
    if (!token) return
    const labels = {
      suspended: `Suspendre ${item.email} ? Connexion bloquée temporairement.`,
      banned: `Bannir ${item.email} ? Connexion définitivement bloquée jusqu’à réactivation.`,
      active: `Réactiver ${item.email} ?`,
    }
    const confirmed = window.confirm(labels[status])
    if (!confirmed) return
    setPendingId(item.id)
    setError('')
    setMessage('')
    try {
      const result = await api.updatePlatformUser(item.id, { status }, token)
      setItems((current) =>
        current.map((row) => (row.id === result.user.id ? result.user : row)),
      )
      setMessage(
        status === 'active'
          ? `${item.email} réactivé.`
          : status === 'banned'
            ? `${item.email} banni.`
            : `${item.email} suspendu.`,
      )
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Mise à jour impossible')
    } finally {
      setPendingId(null)
    }
  }

  return (
    <>
      <div className="platform-title">
        <span>ELF Admin</span>
        <h1>Utilisateurs</h1>
        <p>
          Suivi des comptes : actif, suspendu ou banni. Demandes e-mail pro →{' '}
          <Link to="/elfadmin/emails-pro">Emails pro</Link>.
        </p>
        <p className="platform-muted">
          Lien :{' '}
          <a href="https://elfis-core.com/elfadmin/utilisateurs">
            https://elfis-core.com/elfadmin/utilisateurs
          </a>
        </p>
      </div>
      {error && <div className="platform-alert">{error}</div>}
      {message && <div className="platform-alert platform-alert-ok">{message}</div>}
      {loading ? (
        <div className="platform-loading">Chargement…</div>
      ) : (
        <div className="platform-table-wrap">
          <table className="platform-table">
            <thead>
              <tr>
                <th>Utilisateur</th>
                <th>Email</th>
                <th>Organisations</th>
                <th>Dernière connexion</th>
                <th>Statut</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => {
                const isSelf = item.id === me?.id
                const busy = pendingId === item.id
                return (
                  <tr key={item.id}>
                    <td>
                      <strong>{item.display_name || item.email}</strong>
                      <small>
                        #{item.id}
                        {item.is_platform_admin ? ' · ELF Admin' : ''}
                      </small>
                    </td>
                    <td>{item.email}</td>
                    <td>{item.organization_count}</td>
                    <td>{formatWhen(item.last_login)}</td>
                    <td>
                      <span
                        className={`platform-pill ${item.status === 'active' ? '' : 'warn'}`}
                      >
                        {statusLabel(item.status)}
                      </span>
                    </td>
                    <td>
                      {isSelf || item.is_platform_admin ? (
                        <span className="platform-muted">
                          {isSelf ? 'Votre compte' : 'Protégé'}
                        </span>
                      ) : (
                        <div className="actions" style={{ margin: 0, flexWrap: 'wrap', gap: '0.35rem' }}>
                          {item.status !== 'active' && (
                            <button
                              type="button"
                              className="platform-action"
                              disabled={busy}
                              onClick={() => void updateStatus(item, 'active')}
                            >
                              {busy ? '…' : 'Réactiver'}
                            </button>
                          )}
                          {item.status === 'active' && (
                            <button
                              type="button"
                              className="platform-action"
                              disabled={busy}
                              onClick={() => void updateStatus(item, 'suspended')}
                            >
                              Suspendre
                            </button>
                          )}
                          {item.status !== 'banned' && (
                            <button
                              type="button"
                              className="platform-action"
                              disabled={busy}
                              onClick={() => void updateStatus(item, 'banned')}
                            >
                              Bannir
                            </button>
                          )}
                        </div>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          {!items.length && <p className="platform-empty">Aucun utilisateur.</p>}
        </div>
      )}
    </>
  )
}

import { useEffect, useState } from 'react'
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

  const updateStatus = async (item: PlatformUser, status: 'active' | 'suspended') => {
    if (!token) return
    const confirmed = window.confirm(
      status === 'suspended'
        ? `Suspendre ${item.email} ? La personne ne pourra plus se connecter.`
        : `Réactiver ${item.email} ?`,
    )
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
        status === 'suspended'
          ? `${item.email} a été suspendu (connexion bloquée).`
          : `${item.email} a été réactivé.`,
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
        <p>Gérez tous les comptes ComptaPilot : statut, organisations et accès plateforme.</p>
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
                        {item.status === 'active' ? 'Actif' : 'Suspendu'}
                      </span>
                    </td>
                    <td>
                      {isSelf || item.is_platform_admin ? (
                        <span className="platform-muted">
                          {isSelf ? 'Votre compte' : 'Protégé'}
                        </span>
                      ) : (
                        <button
                          type="button"
                          className="platform-action"
                          disabled={busy}
                          onClick={() =>
                            void updateStatus(
                              item,
                              item.status === 'active' ? 'suspended' : 'active',
                            )
                          }
                        >
                          {busy
                            ? '…'
                            : item.status === 'active'
                              ? 'Suspendre'
                              : 'Réactiver'}
                        </button>
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

import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, type EmailConnection } from '../api'

type Props = {
  token: string
  orgId: number
  canManage: boolean
  userEmail?: string
}

const emptySmtp = {
  email_address: '',
  display_name: '',
  smtp_host: '',
  smtp_port: 587,
  smtp_username: '',
  smtp_password: '',
  smtp_security: 'starttls',
}

function providerLabel(provider: string) {
  const map: Record<string, string> = {
    platform: 'ComptaPilot',
    google: 'Google',
    microsoft: 'Microsoft',
    custom_smtp: 'SMTP',
  }
  return map[provider] || provider
}

function statusLabel(status: string) {
  const map: Record<string, string> = {
    connected: 'Connectée',
    expired: 'Expirée',
    revoked: 'Révoquée',
    error: 'Erreur',
    disconnected: 'Déconnectée',
  }
  return map[status] || status
}

export default function EmailConnectionsPanel({ token, orgId, canManage, userEmail }: Props) {
  const [searchParams, setSearchParams] = useSearchParams()
  const [connections, setConnections] = useState<EmailConnection[]>([])
  const [googleOk, setGoogleOk] = useState(false)
  const [microsoftOk, setMicrosoftOk] = useState(false)
  const [platformOk, setPlatformOk] = useState(false)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [showSmtp, setShowSmtp] = useState(false)
  const [smtp, setSmtp] = useState(emptySmtp)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await api.listEmailConnections(token, orgId)
      setConnections(data.connections)
      setGoogleOk(data.google_oauth_configured)
      setMicrosoftOk(data.microsoft_oauth_configured)
      setPlatformOk(data.platform_configured)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Chargement impossible')
    } finally {
      setLoading(false)
    }
  }, [token, orgId])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    const oauth = searchParams.get('email_oauth')
    const provider = searchParams.get('provider')
    if (!oauth) return
    if (oauth === 'success') {
      setMessage(`Connexion ${providerLabel(provider || '')} réussie.`)
      void load()
    } else {
      setError(`Échec de connexion ${providerLabel(provider || '')}. Réessayez.`)
    }
    const next = new URLSearchParams(searchParams)
    next.delete('email_oauth')
    next.delete('provider')
    next.delete('detail')
    setSearchParams(next, { replace: true })
  }, [searchParams, setSearchParams, load])

  const run = async (fn: () => Promise<void>) => {
    setBusy(true)
    setError('')
    setMessage('')
    try {
      await fn()
      await load()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Action impossible')
    } finally {
      setBusy(false)
    }
  }

  const connectGoogle = () =>
    void run(async () => {
      const { redirect_url } = await api.startGoogleEmailOAuth(token, orgId)
      window.location.assign(redirect_url)
    })

  const connectMicrosoft = () =>
    void run(async () => {
      const { redirect_url } = await api.startMicrosoftEmailOAuth(token, orgId)
      window.location.assign(redirect_url)
    })

  const activatePlatform = () =>
    void run(async () => {
      await api.activatePlatformEmail(token, orgId)
      setMessage('Mode ComptaPilot activé comme expéditeur par défaut.')
    })

  const onSmtpSubmit = (e: FormEvent) => {
    e.preventDefault()
    void run(async () => {
      await api.upsertCustomSmtp(
        {
          ...smtp,
          smtp_port: Number(smtp.smtp_port) || 587,
          make_default: true,
        },
        token,
        orgId,
      )
      setMessage('SMTP enregistré et testé.')
      setShowSmtp(false)
      setSmtp(emptySmtp)
    })
  }

  if (loading) {
    return <p className="muted">Chargement des boîtes mail…</p>
  }

  return (
    <section className="email-connections-panel" aria-label="Boîte mail d’expédition">
      <h4>Boîte mail d’expédition</h4>
      <p className="muted">
        Chaque organisation envoie depuis sa propre boîte. ComptaPilot ne demande jamais le mot de
        passe Google ou Microsoft.
      </p>

      {message && <p className="muted">{message}</p>}
      {error && <p className="form-error">{error}</p>}

      {canManage && (
        <div className="actions" style={{ flexWrap: 'wrap', marginBottom: '1rem' }}>
          <button
            type="button"
            className="btn secondary"
            disabled={busy || !platformOk}
            onClick={activatePlatform}
          >
            Utiliser l’adresse ComptaPilot
          </button>
          <button
            type="button"
            className="btn secondary"
            disabled={busy || !googleOk}
            onClick={connectGoogle}
            title={googleOk ? undefined : 'GOOGLE_CLIENT_* non configuré'}
          >
            Connecter Google
          </button>
          <button
            type="button"
            className="btn secondary"
            disabled={busy || !microsoftOk}
            onClick={connectMicrosoft}
            title={microsoftOk ? undefined : 'MICROSOFT_CLIENT_* non configuré'}
          >
            Connecter Microsoft
          </button>
          <button
            type="button"
            className="btn secondary"
            disabled={busy}
            onClick={() => setShowSmtp((v) => !v)}
          >
            Configurer un autre fournisseur
          </button>
        </div>
      )}

      {showSmtp && canManage && (
        <form className="form-grid" onSubmit={onSmtpSubmit} style={{ marginBottom: '1.25rem' }}>
          <div className="field">
            <label>Adresse d’expédition</label>
            <input
              type="email"
              required
              value={smtp.email_address}
              onChange={(e) => setSmtp({ ...smtp, email_address: e.target.value })}
            />
          </div>
          <div className="field">
            <label>Nom affiché</label>
            <input
              value={smtp.display_name}
              onChange={(e) => setSmtp({ ...smtp, display_name: e.target.value })}
            />
          </div>
          <div className="field">
            <label>Serveur SMTP</label>
            <input
              required
              value={smtp.smtp_host}
              onChange={(e) => setSmtp({ ...smtp, smtp_host: e.target.value })}
              placeholder="smtp.exemple.fr"
            />
          </div>
          <div className="field">
            <label>Port</label>
            <input
              type="number"
              value={smtp.smtp_port}
              onChange={(e) => setSmtp({ ...smtp, smtp_port: Number(e.target.value) })}
            />
          </div>
          <div className="field">
            <label>Chiffrement</label>
            <select
              value={smtp.smtp_security}
              onChange={(e) => setSmtp({ ...smtp, smtp_security: e.target.value })}
            >
              <option value="starttls">STARTTLS</option>
              <option value="ssl">SSL</option>
              <option value="none">Aucun</option>
            </select>
          </div>
          <div className="field">
            <label>Nom d’utilisateur</label>
            <input
              value={smtp.smtp_username}
              onChange={(e) => setSmtp({ ...smtp, smtp_username: e.target.value })}
              placeholder="souvent égal à l’adresse"
            />
          </div>
          <div className="field full">
            <label>Mot de passe / mot de passe d’application</label>
            <input
              type="password"
              required
              autoComplete="new-password"
              value={smtp.smtp_password}
              onChange={(e) => setSmtp({ ...smtp, smtp_password: e.target.value })}
            />
            <p className="muted" style={{ margin: '0.35rem 0 0', fontSize: '0.85rem' }}>
              Le mot de passe n’est jamais réaffiché après enregistrement. Préférez un mot de passe
              d’application.
            </p>
          </div>
          <div className="actions" style={{ gridColumn: '1 / -1' }}>
            <button type="submit" className="btn" disabled={busy}>
              Tester et activer
            </button>
            <button type="button" className="btn secondary" onClick={() => setShowSmtp(false)}>
              Annuler
            </button>
          </div>
        </form>
      )}

      {connections.length === 0 ? (
        <p className="muted">Aucune connexion pour le moment.</p>
      ) : (
        <div className="list">
          {connections.map((conn) => (
            <div
              key={conn.id}
              className="list-item"
              style={{ gridTemplateColumns: '1fr auto', alignItems: 'start' }}
            >
              <div>
                <strong>
                  {conn.from_preview || `${conn.display_name} <${conn.email_address}>`}
                </strong>
                <span>
                  {providerLabel(conn.provider)} · {statusLabel(conn.status)}
                  {conn.is_default ? ' · Par défaut' : ''}
                  {conn.created_at
                    ? ` · Connectée le ${new Date(conn.created_at).toLocaleString('fr-FR')}`
                    : ''}
                  {conn.last_used_at
                    ? ` · Dernier envoi ${new Date(conn.last_used_at).toLocaleString('fr-FR')}`
                    : ''}
                  {conn.last_error_message ? ` · ${conn.last_error_message}` : ''}
                </span>
              </div>
              {canManage && (
                <div className="actions" style={{ margin: 0, flexWrap: 'wrap' }}>
                  {!conn.is_default && conn.status === 'connected' && (
                    <button
                      type="button"
                      className="btn secondary btn-sm"
                      disabled={busy}
                      onClick={() =>
                        void run(async () => {
                          await api.setDefaultEmailConnection(conn.id, token, orgId)
                          setMessage('Expéditeur par défaut mis à jour.')
                        })
                      }
                    >
                      Par défaut
                    </button>
                  )}
                  <button
                    type="button"
                    className="btn secondary btn-sm"
                    disabled={busy}
                    onClick={() =>
                      void run(async () => {
                        await api.testEmailConnection(
                          conn.id,
                          userEmail || conn.email_address,
                          token,
                          orgId,
                        )
                        setMessage('E-mail de test envoyé.')
                      })
                    }
                  >
                    Tester
                  </button>
                  {conn.provider !== 'platform' && conn.provider !== 'custom_smtp' && (
                    <button
                      type="button"
                      className="btn secondary btn-sm"
                      disabled={busy}
                      onClick={() =>
                        void run(async () => {
                          const res = await api.reconnectEmailConnection(conn.id, token, orgId)
                          if (res.redirect_url) window.location.assign(res.redirect_url)
                        })
                      }
                    >
                      Reconnecter
                    </button>
                  )}
                  {conn.provider !== 'platform' && (
                    <button
                      type="button"
                      className="btn secondary btn-sm"
                      disabled={busy}
                      onClick={() =>
                        void run(async () => {
                          await api.disconnectEmailConnection(conn.id, token, orgId)
                          setMessage('Boîte déconnectée.')
                        })
                      }
                    >
                      Déconnecter
                    </button>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

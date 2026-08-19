import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type EmailConnection } from '../../api'
import { useAuth } from '../../auth'
import '../../platform-workspace/platform-workspace.css'

/**
 * Communications ELFIS Core — statut provider / connexions sans secrets.
 */
export default function PlatformCommunicationsPage() {
  const { token, orgId, user } = useAuth()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [platformConfigured, setPlatformConfigured] = useState(false)
  const [connections, setConnections] = useState<EmailConnection[]>([])
  const [canManage, setCanManage] = useState(false)
  const [adminStatus, setAdminStatus] = useState<Record<string, unknown> | null>(null)

  useEffect(() => {
    if (!token) return
    setLoading(true)
    setError('')
    const orgLoad = api
      .listEmailConnections(token, orgId)
      .then((data) => {
        setConnections(data.connections || [])
        setPlatformConfigured(Boolean(data.platform_configured))
        setCanManage(Boolean(data.can_manage))
      })
      .catch((e) => {
        setError(e instanceof Error ? e.message : 'Impossible de charger les communications')
      })

    const adminLoad =
      user?.is_platform_admin
        ? api
            .platformEmailStatus(token)
            .then((s) => setAdminStatus(s))
            .catch(() => setAdminStatus(null))
        : Promise.resolve()

    void Promise.all([orgLoad, adminLoad]).finally(() => setLoading(false))
  }, [token, orgId, user?.is_platform_admin])

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h2>Communications</h2>
          <p>Infrastructure e-mail ELFIS — provider, expéditeur et état. Aucun secret affiché.</p>
        </div>
      </div>

      <div className="platform-surface-banner">
        <strong>ELFIS Core</strong>
        <p>
          ComptaPilot et SalesPilot demandent <code>email.send</code> via ce service. Les modèles
          métier (sujet / message facture) restent dans chaque Pilot.
        </p>
        <div className="platform-surface-banner__actions">
          <Link className="btn secondary" to="/platform/communications/settings">
            Paramètres e-mail
          </Link>
          <Link className="btn secondary" to="/platform/settings">
            Paramètres plateforme
          </Link>
        </div>
      </div>

      {error ? (
        <div className="panel form-error" role="alert">
          {error}
        </div>
      ) : null}

      {loading ? (
        <div className="panel">Chargement…</div>
      ) : (
        <>
          <section className="panel" aria-labelledby="comms-status">
            <h3 id="comms-status">État du service</h3>
            <dl className="kv-list" style={{ display: 'grid', gap: '0.5rem' }}>
              <div>
                <dt className="muted">Plateforme e-mail</dt>
                <dd>
                  <strong>{platformConfigured ? 'Configuré' : 'Non configuré'}</strong>
                </dd>
              </div>
              {adminStatus ? (
                <>
                  <div>
                    <dt className="muted">Provider (admin)</dt>
                    <dd>{String(adminStatus.provider || adminStatus.transport || '—')}</dd>
                  </div>
                  <div>
                    <dt className="muted">Expéditeur</dt>
                    <dd>{String(adminStatus.platform_from || '—')}</dd>
                  </div>
                  <div>
                    <dt className="muted">État</dt>
                    <dd>
                      {adminStatus.configuration_valid || adminStatus.brevo_ok
                        ? 'Prêt'
                        : String(adminStatus.reason_code || 'À vérifier')}
                    </dd>
                  </div>
                  {adminStatus.hint ? (
                    <div>
                      <dt className="muted">Diagnostic</dt>
                      <dd className="muted">{String(adminStatus.hint)}</dd>
                    </div>
                  ) : null}
                </>
              ) : (
                <p className="muted">
                  Diagnostic détaillé réservé aux administrateurs plateforme. Les secrets (clés API,
                  mots de passe SMTP) ne sont jamais exposés ici.
                </p>
              )}
            </dl>
          </section>

          <section className="panel" aria-labelledby="comms-connections">
            <h3 id="comms-connections">Connexions organisation</h3>
            {connections.length === 0 ? (
              <p className="muted">
                Aucune connexion organisation. {canManage ? 'Configurez un expéditeur dans les paramètres.' : null}
              </p>
            ) : (
              <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                {connections.map((c) => (
                  <li
                    key={c.id}
                    style={{
                      padding: '0.65rem 0',
                      borderBottom: '1px solid rgba(0,0,0,0.06)',
                    }}
                  >
                    <strong>{c.display_name || c.email_address || c.provider}</strong>
                    <span className="muted"> · {c.provider}</span>
                    <span className="platform-role-chip">{c.status}</span>
                    {c.is_default ? <span className="platform-role-chip">Défaut</span> : null}
                    {c.last_error_code ? (
                      <p className="form-error" style={{ margin: '0.25rem 0 0' }}>
                        Dernière erreur : {c.last_error_code}
                        {c.last_error_message ? ` — ${c.last_error_message}` : ''}
                      </p>
                    ) : null}
                    {/* Jamais has_smtp_password détail ni token */}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="panel">
            <h3>Documentation</h3>
            <p className="muted">
              Configuration serveur (Brevo API / SMTP) : variables d’environnement backend uniquement.
              Voir la documentation ops e-mail du dépôt.
            </p>
          </section>
        </>
      )}
    </div>
  )
}

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type PlatformOrganization } from '../../api'
import { useAuth } from '../../auth'
import { subscriptionLabels, subscriptionTone } from '../../subscription'

function pillClass(status: string) {
  const tone = subscriptionTone(status as never)
  if (tone === 'warn') return 'platform-pill platform-pill-warn'
  if (tone === 'danger') return 'platform-pill platform-pill-danger'
  if (tone === 'neutral') return 'platform-pill platform-pill-neutral'
  return 'platform-pill'
}

export default function PlatformOrganizationsPage() {
  const { token } = useAuth()
  const [items, setItems] = useState<PlatformOrganization[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) return
    api
      .platformOrganizations(token)
      .then((result) => setItems(result.organizations))
      .catch((reason) => setError(reason instanceof Error ? reason.message : 'Liste indisponible'))
      .finally(() => setLoading(false))
  }, [token])

  return (
    <>
      <div className="platform-title platform-title-row">
        <div>
          <span>ELF Admin</span>
          <h1>Organisations</h1>
          <p>{items.length} organisation(s) sur la plateforme.</p>
        </div>
        <Link className="platform-action" to="/elfadmin/abonnements">
          Voir abonnements
        </Link>
      </div>
      {error && <div className="platform-alert">{error}</div>}
      {loading ? (
        <div className="platform-loading">Chargement…</div>
      ) : items.length === 0 ? (
        <div className="platform-loading platform-empty">Aucune organisation.</div>
      ) : (
        <div className="platform-request-list">
          {items.map((item) => (
            <article key={item.id} className="platform-request-card">
              <header className="platform-request-head">
                <div>
                  <h2>{item.legal_name || item.name}</h2>
                  <p>
                    #{item.id} · {item.country || '—'}
                  </p>
                </div>
                <span className={pillClass(item.subscription.status)}>
                  {subscriptionLabels[item.subscription.status] || item.subscription.status}
                </span>
              </header>
              <dl className="platform-request-meta">
                <div>
                  <dt>Utilisateurs</dt>
                  <dd>{item.member_count}</dd>
                </div>
                <div>
                  <dt>Offre</dt>
                  <dd>{item.subscription.plan || 'pro'}</dd>
                </div>
                <div>
                  <dt>Statut</dt>
                  <dd>
                    <code>{item.subscription.status}</code>
                  </dd>
                </div>
              </dl>
            </article>
          ))}
        </div>
      )}
    </>
  )
}

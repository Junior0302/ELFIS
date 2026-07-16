import { useEffect, useState } from 'react'
import { api, type PlatformOverview } from '../../api'
import { useAuth } from '../../auth'

export default function PlatformOverviewPage() {
  const { token } = useAuth()
  const [overview, setOverview] = useState<PlatformOverview | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) return
    api.platformOverview(token).then(setOverview).catch((reason) => {
      setError(reason instanceof Error ? reason.message : 'Synthèse indisponible')
    })
  }, [token])

  return (
    <>
      <div className="platform-title">
        <span>ELF Admin</span>
        <h1>Pilotage plateforme</h1>
        <p>Vue consolidée des utilisateurs, organisations et abonnements ComptaPilot.</p>
      </div>
      {error && <div className="platform-alert">{error}</div>}
      {!overview && !error ? (
        <div className="platform-loading">Chargement des indicateurs…</div>
      ) : overview ? (
        <div className="platform-stats">
          <article><span>Organisations</span><strong>{overview.organizations}</strong></article>
          <article><span>Utilisateurs</span><strong>{overview.users}</strong></article>
          <article><span>Membres actifs</span><strong>{overview.active_memberships}</strong></article>
          <article><span>Abonnements actifs</span><strong>{overview.subscriptions_by_status.active ?? 0}</strong></article>
          <article><span>En essai</span><strong>{overview.subscriptions_by_status.trialing ?? 0}</strong></article>
          <article>
            <span>Incidents de paiement</span>
            <strong>
              {(overview.subscriptions_by_status.past_due ?? 0) +
                (overview.subscriptions_by_status.unpaid ?? 0) +
                (overview.subscriptions_by_status.incomplete ?? 0) +
                (overview.subscriptions_by_status.incomplete_expired ?? 0)}
            </strong>
          </article>
        </div>
      ) : null}
    </>
  )
}

import { useEffect, useState } from 'react'
import { api } from '../../api'
import { useAuth } from '../../auth'
import { EmptyState, ErrorState, Skeleton } from '../../ui/UiStates'

export default function PlatformNotificationsAdminPage() {
  const { token } = useAuth()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [items, setItems] = useState<Array<Record<string, unknown>>>([])
  const [jobsFailed, setJobsFailed] = useState(0)

  async function load() {
    if (!token) return
    setLoading(true)
    setError('')
    try {
      const [n, jobs] = await Promise.all([
        api.platformNotificationsAdmin(token, { page: 1, page_size: 40 }),
        api.platformJobs(token, { status: 'failed', page: 1, page_size: 1 }),
      ])
      setItems(n.notifications || [])
      setJobsFailed(jobs.total || 0)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Notifications plateforme indisponibles')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [token])

  return (
    <>
      <div className="platform-title">
        <span>Notifications</span>
        <h1>Centre notifications plateforme</h1>
        <p>Emails, jobs, events — API `/platform/notifications` et `/platform/jobs`.</p>
      </div>
      <p className="muted">Jobs en échec : {jobsFailed}</p>
      {loading ? <Skeleton rows={5} /> : null}
      {error ? <ErrorState message={error} onRetry={() => void load()} /> : null}
      {!loading && !error && items.length === 0 ? (
        <EmptyState title="Aucune notification" />
      ) : null}
      {!loading && items.length > 0 ? (
        <ul className="platform-service-list">
          {items.map((n, i) => (
            <li key={String(n.notification_id || n.id || i)}>
              <strong>{String(n.title || n.event_type || 'Notification')}</strong>
              <span className="muted">
                {' '}
                · org {String(n.organization_id ?? '—')} · {String(n.status || n.channel || '')}
              </span>
            </li>
          ))}
        </ul>
      ) : null}
    </>
  )
}

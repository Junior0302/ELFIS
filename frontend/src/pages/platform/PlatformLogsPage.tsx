import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api'
import { useAuth } from '../../auth'
import { getSystemLogs } from '../../services/systemHealthApi'
import { ErrorState, Skeleton } from '../../ui/UiStates'

export default function PlatformLogsPage() {
  const { token } = useAuth()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [logs, setLogs] = useState<unknown>(null)
  const [audit, setAudit] = useState<unknown>(null)

  async function load() {
    if (!token) return
    setLoading(true)
    setError('')
    try {
      const [l, a] = await Promise.all([
        getSystemLogs(token, { limit: 50 }),
        api.platformAudit(token),
      ])
      setLogs(l)
      setAudit(a)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Logs indisponibles')
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
        <span>Logs</span>
        <h1>Logs & audit</h1>
        <p>
          Lecture seule — <code>/admin/system/logs</code> + <code>/platform/audit</code>.{' '}
          <Link to="/elfadmin/activity">Activity Center</Link>
        </p>
      </div>
      {loading ? <Skeleton rows={6} /> : null}
      {error ? <ErrorState message={error} onRetry={() => void load()} /> : null}
      {!loading && !error ? (
        <div className="ui-card-grid">
          <section className="panel">
            <h2>System logs</h2>
            <pre className="platform-pre">{JSON.stringify(logs, null, 2).slice(0, 4000)}</pre>
          </section>
          <section className="panel">
            <h2>Audit récent</h2>
            <pre className="platform-pre">{JSON.stringify(audit, null, 2).slice(0, 4000)}</pre>
          </section>
        </div>
      ) : null}
    </>
  )
}

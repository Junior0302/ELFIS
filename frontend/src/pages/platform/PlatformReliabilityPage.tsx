import { useEffect, useState } from 'react'
import { api } from '../../api'
import { useAuth } from '../../auth'

export default function PlatformReliabilityPage() {
  const { token } = useAuth()
  const [retention, setRetention] = useState<unknown[]>([])
  const [readiness, setReadiness] = useState<Record<string, unknown> | null>(null)
  const [backup, setBackup] = useState<Record<string, unknown> | null>(null)
  const [cleanup, setCleanup] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!token) return
    Promise.all([
      api.platformReliabilityRetention(token),
      api.platformReliabilityReadiness(token),
      api.platformReliabilityBackupPolicy(token),
    ])
      .then(([ret, ready, bak]) => {
        setRetention(ret.policies)
        setReadiness(ready)
        setBackup(bak)
      })
      .catch((reason) => setError(reason instanceof Error ? reason.message : 'Fiabilité indisponible'))
  }, [token])

  const runDryCleanup = () => {
    if (!token) return
    setBusy(true)
    api
      .platformReliabilityCleanupDryRun(token)
      .then(setCleanup)
      .catch((reason) => setError(reason instanceof Error ? reason.message : 'Cleanup indisponible'))
      .finally(() => setBusy(false))
  }

  return (
    <>
      <div className="platform-title">
        <h1>Fiabilité</h1>
        <p>Readiness, rétention, cleanup dry-run, backup / recovery (non automatique).</p>
      </div>
      {error && <div className="platform-alert">{error}</div>}
      <div className="platform-toolbar">
        <button type="button" className="btn" disabled={busy} onClick={runDryCleanup}>
          Cleanup dry-run
        </button>
      </div>
      {cleanup && (
        <pre className="platform-pre" style={{ whiteSpace: 'pre-wrap', fontSize: 12 }}>
          {JSON.stringify(cleanup, null, 2)}
        </pre>
      )}
      <h2>Rétention</h2>
      <div className="platform-table-wrap">
        <table className="platform-table">
          <thead>
            <tr>
              <th>Catégorie</th>
              <th>Jours</th>
              <th>Notes</th>
            </tr>
          </thead>
          <tbody>
            {(retention as Array<{ category: string; days: number; notes?: string }>).map((p) => (
              <tr key={p.category}>
                <td>{p.category}</td>
                <td>{p.days}</td>
                <td>{p.notes || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {readiness && (
        <>
          <h2>Readiness / stale</h2>
          <pre className="platform-pre" style={{ whiteSpace: 'pre-wrap', fontSize: 12 }}>
            {JSON.stringify(readiness, null, 2)}
          </pre>
        </>
      )}
      {backup && (
        <>
          <h2>Backup & recovery</h2>
          <pre className="platform-pre" style={{ whiteSpace: 'pre-wrap', fontSize: 12 }}>
            {JSON.stringify(backup, null, 2)}
          </pre>
        </>
      )}
    </>
  )
}

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type PlatformDashboard } from '../../api'
import { useAuth } from '../../auth'
import { ErrorState, Skeleton, UiBadge } from '../../ui/UiStates'

function downloadBlob(filename: string, content: string, mime: string) {
  const blob = new Blob([content], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

/** Rapports = composition / export des payloads API existants (pas de calcul métier). */
export default function PlatformReportsAdminPage() {
  const { token } = useAuth()
  const [dash, setDash] = useState<PlatformDashboard | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!token) return
    api
      .platformDashboard(token, '30d')
      .then(setDash)
      .catch((e) => setError(e instanceof Error ? e.message : 'Rapport indisponible'))
      .finally(() => setLoading(false))
  }, [token])

  function exportJson() {
    if (!dash) return
    downloadBlob(
      `platform-dashboard-30d.json`,
      JSON.stringify(dash, null, 2),
      'application/json',
    )
  }

  function exportCsv() {
    if (!dash) return
    const rows = Object.entries(dash).map(([k, v]) => `${k},${JSON.stringify(v)}`)
    downloadBlob(`platform-dashboard-30d.csv`, `key,value\n${rows.join('\n')}`, 'text/csv')
  }

  function exportPdfPlaceholder() {
    // Pas de générateur PDF backend dédié : export texte imprimable
    if (!dash) return
    const text = `ELFIS Platform Report\n${JSON.stringify(dash, null, 2)}`
    downloadBlob(`platform-dashboard-30d.txt`, text, 'application/pdf')
  }

  return (
    <>
      <div className="platform-title">
        <span>Rapports</span>
        <h1>Exports plateforme</h1>
        <p>
          JSON / CSV / impression — données dashboard API. Audit détaillé :{' '}
          <Link to="/elfadmin/activity">Activity Center</Link>.
        </p>
      </div>
      {loading ? <Skeleton rows={4} /> : null}
      {error ? <ErrorState message={error} /> : null}
      {dash ? (
        <>
          <div className="platform-toolbar">
            <button type="button" className="btn" onClick={exportJson}>
              Export JSON
            </button>
            <button type="button" className="btn secondary" onClick={exportCsv}>
              Export CSV
            </button>
            <button type="button" className="btn secondary" onClick={exportPdfPlaceholder}>
              Export imprimable
            </button>
            <UiBadge>période {dash.period}</UiBadge>
          </div>
          <pre className="platform-pre">{JSON.stringify(dash, null, 2)}</pre>
        </>
      ) : null}
    </>
  )
}

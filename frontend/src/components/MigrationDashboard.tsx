import { useCallback, useEffect, useState } from 'react'
import {
  smartMigrationApi,
  type SmartDashboard,
  type SmartReport,
} from '../services/smartMigrationApi'

type Props = {
  token: string
  orgId: number
  migrationSessionId: string
}

export default function MigrationDashboard({ token, orgId, migrationSessionId }: Props) {
  const [dash, setDash] = useState<SmartDashboard | null>(null)
  const [metrics, setMetrics] = useState<Record<string, unknown> | null>(null)
  const [report, setReport] = useState<SmartReport | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [statusMessage, setStatusMessage] = useState('Supervision Enterprise')

  const reload = useCallback(async () => {
    const [d, m] = await Promise.all([
      smartMigrationApi.dashboard(token, orgId, migrationSessionId),
      smartMigrationApi.metrics(token, orgId, migrationSessionId),
    ])
    setDash(d)
    setMetrics(m)
  }, [token, orgId, migrationSessionId])

  useEffect(() => {
    let cancelled = false
    async function boot() {
      try {
        await reload()
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Chargement impossible')
      }
    }
    void boot()
    const timer = window.setInterval(() => {
      void reload().catch(() => undefined)
    }, 5000)
    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [reload])

  async function startOrch() {
    if (busy) return
    setBusy(true)
    setError('')
    setStatusMessage('Orchestration en cours…')
    try {
      const res = await smartMigrationApi.start(token, orgId, migrationSessionId, {
        batch_size: 25,
        run_now: true,
      })
      setStatusMessage(`Run ${res.status} · ${Math.round(res.progress_percent)}%`)
      await reload()
      try {
        setReport(await smartMigrationApi.report(token, orgId, migrationSessionId, 'json'))
      } catch {
        setReport(null)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Démarrage impossible')
    } finally {
      setBusy(false)
    }
  }

  async function resume() {
    if (busy) return
    setBusy(true)
    try {
      await smartMigrationApi.resume(token, orgId, migrationSessionId)
      await reload()
      setStatusMessage('Reprise effectuée')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Reprise impossible')
    } finally {
      setBusy(false)
    }
  }

  async function cancel() {
    if (busy) return
    setBusy(true)
    try {
      await smartMigrationApi.cancel(token, orgId, migrationSessionId)
      await reload()
      setStatusMessage('Migration annulée')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Annulation impossible')
    } finally {
      setBusy(false)
    }
  }

  async function retryFailed() {
    if (busy) return
    setBusy(true)
    try {
      await smartMigrationApi.retryFailed(token, orgId, migrationSessionId)
      await reload()
      setStatusMessage('Relance des échecs')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Relance impossible')
    } finally {
      setBusy(false)
    }
  }

  async function loadReport(format: 'json' | 'csv' | 'pdf') {
    try {
      const r = await smartMigrationApi.report(token, orgId, migrationSessionId, format)
      setReport(r)
      if (format === 'csv' && r.csv) {
        const blob = new Blob([r.csv], { type: 'text/csv;charset=utf-8' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `migration-report-v${r.version}.csv`
        a.click()
        URL.revokeObjectURL(url)
      }
      if (format === 'pdf' && r.pdf_base64) {
        const bin = atob(r.pdf_base64)
        const bytes = new Uint8Array(bin.length)
        for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i)
        const blob = new Blob([bytes], { type: 'application/pdf' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `migration-report-v${r.version}.pdf`
        a.click()
        URL.revokeObjectURL(url)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Rapport impossible')
    }
  }

  const pct = dash?.progress_percent ?? 0
  const chartMax = Math.max(1, ...(dash?.chart.values || [1]))

  return (
    <div className="migration-analysis-panel">
      <header className="migration-analysis-toolbar" style={{ justifyContent: 'space-between' }}>
        <div>
          <h3>Migration Dashboard</h3>
          <p className="muted">
            Supervision Enterprise — batch, reprise, métriques (calcul serveur)
          </p>
        </div>
        <span className="muted">
          {statusMessage}
          {dash?.correlation_id ? ` · ${dash.correlation_id}` : ''}
        </span>
      </header>

      {error ? <div className="form-error">{error}</div> : null}

      <div className="migration-analysis-toolbar">
        <button type="button" className="btn" disabled={busy} onClick={() => void startOrch()}>
          Lancer l&apos;orchestration
        </button>
        <button type="button" className="btn secondary" disabled={busy} onClick={() => void resume()}>
          Reprendre
        </button>
        <button
          type="button"
          className="btn secondary"
          disabled={busy}
          onClick={() => void retryFailed()}
        >
          Relancer les échecs
        </button>
        <button type="button" className="btn secondary" disabled={busy} onClick={() => void cancel()}>
          Annuler
        </button>
      </div>

      <section style={{ marginTop: '1.25rem' }}>
        <h4>Progression globale</h4>
        <div className="migration-progress-bar" aria-label="Progression globale">
          <span style={{ width: `${Math.min(100, pct)}%` }} />
        </div>
        <p className="muted">
          {Math.round(pct)}% · ETA{' '}
          {dash?.eta_seconds != null ? `${Math.round(dash.eta_seconds)}s` : '—'} · débit{' '}
          {dash?.throughput_per_min?.toFixed?.(2) ?? '0'} doc/min
        </p>
      </section>

      {dash ? (
        <section style={{ marginTop: '1rem' }}>
          <h4>Indicateurs</h4>
          <ul className="migration-analysis-list">
            <li>
              <strong>Documents</strong>
              <p className="muted">
                Total {dash.documents_total} · Terminés {dash.documents_completed} · En attente{' '}
                {dash.documents_pending} · Erreurs {dash.documents_failed} · Importés{' '}
                {dash.documents_imported}
              </p>
            </li>
            <li>
              <strong>Workers / lots</strong>
              <p className="muted">
                Lots actifs {dash.active_batches} · Workers {dash.active_workers} · Temps moyen{' '}
                {Math.round(dash.avg_duration_ms)} ms
              </p>
            </li>
            <li>
              <strong>Coût</strong>
              <p className="muted">
                Estimé {dash.estimated_cost.toFixed(4)} € · Réel {dash.actual_cost.toFixed(4)} €
              </p>
            </li>
          </ul>
        </section>
      ) : null}

      {dash?.chart ? (
        <section style={{ marginTop: '1rem' }}>
          <h4>Graphique progression</h4>
          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-end', minHeight: 120 }}>
            {dash.chart.labels.map((label, i) => {
              const v = dash.chart.values[i] || 0
              const h = Math.max(8, Math.round((v / chartMax) * 100))
              return (
                <div key={label} style={{ flex: 1, textAlign: 'center' }}>
                  <div
                    style={{
                      height: h,
                      background: 'var(--accent, #2a6)',
                      opacity: 0.85,
                      marginBottom: 4,
                    }}
                    title={`${label}: ${v}`}
                  />
                  <span className="muted" style={{ fontSize: '0.75rem' }}>
                    {label}
                    <br />
                    {v}
                  </span>
                </div>
              )
            })}
          </div>
        </section>
      ) : null}

      <section style={{ marginTop: '1.25rem' }}>
        <h4>Lots</h4>
        <ul className="migration-analysis-list">
          {(dash?.batches || []).map((b) => (
            <li key={b.batch_id} className={`is-${b.status}`}>
              <div className="migration-progress-bar" aria-label={`Lot ${b.batch_index}`}>
                <span style={{ width: `${b.progress_percent}%` }} />
              </div>
              <strong>
                Lot #{b.batch_index} · {b.status}
              </strong>
              <p className="muted">
                {b.completed}/{b.documents} · échecs {b.failed}
              </p>
            </li>
          ))}
        </ul>
        {!dash?.batches?.length ? (
          <p className="muted">Aucun lot. Lancez l&apos;orchestration après validation/import.</p>
        ) : null}
      </section>

      <section style={{ marginTop: '1.25rem' }}>
        <h4>Rapport & téléchargement</h4>
        <div className="migration-analysis-toolbar">
          <button type="button" className="btn secondary" onClick={() => void loadReport('json')}>
            Voir rapport
          </button>
          <button type="button" className="btn secondary" onClick={() => void loadReport('csv')}>
            CSV
          </button>
          <button type="button" className="btn secondary" onClick={() => void loadReport('pdf')}>
            PDF
          </button>
        </div>
        {report ? (
          <div className="migration-extraction-detail" style={{ marginTop: '0.75rem' }}>
            <h5>
              Rapport v{report.version} · {report.format}
            </h5>
            <pre className="muted" style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem' }}>
              {JSON.stringify(report.summary, null, 2)}
            </pre>
            <p className="muted">
              Erreurs {(report.errors || []).length} · Warnings {(report.warnings || []).length} ·
              Objets créés {(report.created_objects || []).length}
            </p>
          </div>
        ) : null}
      </section>

      {metrics ? (
        <section style={{ marginTop: '1.25rem' }}>
          <h4>Métriques (historique)</h4>
          <p className="muted" style={{ fontSize: '0.85rem' }}>
            retries {String(metrics.retries)} · OCR {String(metrics.ocr_used)} · IA{' '}
            {String(metrics.ai_used)} · corrigés {String(metrics.documents_corrected)} · rejetés{' '}
            {String(metrics.documents_rejected)}
          </p>
        </section>
      ) : null}
    </div>
  )
}

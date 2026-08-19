import { useCallback, useEffect, useState } from 'react'
import {
  importApi,
  importStatusLabel,
  type ImportReport,
  type ImportRun,
  type ReadyDocument,
} from '../services/importApi'

type Props = {
  token: string
  orgId: number
  migrationSessionId: string
}

export default function MigrationImportPanel({ token, orgId, migrationSessionId }: Props) {
  const [ready, setReady] = useState<ReadyDocument[]>([])
  const [history, setHistory] = useState<ImportRun[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [statusMessage, setStatusMessage] = useState('Import métier')
  const [active, setActive] = useState<ImportRun | null>(null)
  const [report, setReport] = useState<ImportReport | null>(null)

  const reload = useCallback(async () => {
    const [r, h] = await Promise.all([
      importApi.listReady(token, orgId, migrationSessionId),
      importApi.listImports(token, orgId, migrationSessionId),
    ])
    setReady(r.items)
    setHistory(h.items)
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
    return () => {
      cancelled = true
    }
  }, [reload])

  async function runOne(documentId: string) {
    if (busy) return
    setBusy(true)
    setError('')
    setStatusMessage('Import en cours…')
    try {
      const run = await importApi.runImport(token, orgId, documentId)
      setActive(run)
      if (run.report_id) {
        try {
          setReport(await importApi.getReport(token, orgId, run.id))
        } catch {
          setReport(null)
        }
      }
      await reload()
      setStatusMessage(
        run.status === 'completed'
          ? `Import terminé · ${run.created_objects.length} créé(s) · ${run.linked_objects.length} lié(s)`
          : importStatusLabel(run.status),
      )
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Import impossible')
    } finally {
      setBusy(false)
    }
  }

  async function openRun(run: ImportRun) {
    setActive(run)
    setReport(null)
    if (run.status === 'completed' || run.report_id) {
      try {
        setReport(await importApi.getReport(token, orgId, run.id))
      } catch {
        setReport(null)
      }
    }
  }

  async function retryRun(id: string) {
    if (busy) return
    setBusy(true)
    setError('')
    try {
      const run = await importApi.retry(token, orgId, id)
      setActive(run)
      await reload()
      setStatusMessage(`Relance · ${importStatusLabel(run.status)}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Relance impossible')
    } finally {
      setBusy(false)
    }
  }

  async function rollbackRun(id: string) {
    if (busy) return
    setBusy(true)
    setError('')
    try {
      const run = await importApi.rollback(token, orgId, id)
      setActive(run)
      await reload()
      setStatusMessage('Rollback terminé')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Rollback impossible')
    } finally {
      setBusy(false)
    }
  }

  const pendingReady = ready.filter((d) => !d.already_imported)

  return (
    <div className="migration-analysis-panel">
      <header className="migration-analysis-toolbar" style={{ justifyContent: 'space-between' }}>
        <div>
          <h3>Import Engine</h3>
          <p className="muted">
            Documents validés → données métier ComptaPilot (transactionnel, idempotent)
          </p>
        </div>
        <span className="muted">
          {statusMessage} · Prêts : {pendingReady.length} · Historique : {history.length}
        </span>
      </header>

      {error ? <div className="form-error">{error}</div> : null}

      <section>
        <h4>Documents prêts</h4>
        <ul className="migration-analysis-list">
          {pendingReady.map((d) => (
            <li key={d.document_id}>
              <div>
                <strong>
                  {d.universal_document_id || d.document_id.slice(0, 8)} · validation v
                  {d.validation_version}
                </strong>
                <p className="muted">Session {d.validation_session_id.slice(0, 8)}…</p>
                <div className="migration-analysis-toolbar">
                  <button
                    type="button"
                    className="btn"
                    disabled={busy}
                    onClick={() => void runOne(d.document_id)}
                  >
                    Importer
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
        {!pendingReady.length ? (
          <p className="muted">
            Aucun document prêt. Validez d’abord les documents dans le Validation & Mapping Center.
          </p>
        ) : null}
      </section>

      <section style={{ marginTop: '1.5rem' }}>
        <h4>Historique des imports</h4>
        <ul className="migration-analysis-list">
          {history.map((r) => (
            <li key={r.id} className={`is-${r.status}`}>
              <div className="migration-progress-bar" aria-label="Progression">
                <span style={{ width: `${r.progress_percent}%` }} />
              </div>
              <div>
                <strong>
                  {r.universal_document_id || r.document_id.slice(0, 8)} ·{' '}
                  {importStatusLabel(r.status)}
                </strong>
                <p className="muted">
                  Créés {r.created_objects?.length || 0} · Liés {r.linked_objects?.length || 0}
                  {r.duration_ms != null ? ` · ${r.duration_ms} ms` : ''}
                  {r.error_message ? ` · ${r.error_message}` : ''}
                </p>
                <div className="migration-analysis-toolbar">
                  <button
                    type="button"
                    className="btn secondary"
                    onClick={() => void openRun(r)}
                  >
                    Rapport
                  </button>
                  {r.status === 'failed' ? (
                    <button
                      type="button"
                      className="btn"
                      disabled={busy}
                      onClick={() => void retryRun(r.id)}
                    >
                      Relancer
                    </button>
                  ) : null}
                  {r.status === 'completed' ? (
                    <button
                      type="button"
                      className="btn secondary"
                      disabled={busy}
                      onClick={() => void rollbackRun(r.id)}
                    >
                      Rollback
                    </button>
                  ) : null}
                </div>
              </div>
            </li>
          ))}
        </ul>
      </section>

      {active ? (
        <div className="migration-extraction-detail" style={{ marginTop: '1.5rem' }}>
          <h4>Résumé — {importStatusLabel(active.status)}</h4>
          <p className="muted">
            Fingerprint {active.fingerprint.slice(0, 16)}… · schéma {active.schema_name || '—'}
          </p>
          <h5>Objets créés</h5>
          <ul>
            {(active.created_objects || []).map((o, i) => (
              <li key={`c-${i}`}>
                {String(o.kind)} #{String(o.id)} {o.label ? `· ${String(o.label)}` : ''}
              </li>
            ))}
          </ul>
          <h5>Objets liés</h5>
          <ul>
            {(active.linked_objects || []).map((o, i) => (
              <li key={`l-${i}`}>
                {String(o.kind)} #{String(o.id)} {o.role ? `· ${String(o.role)}` : ''}
              </li>
            ))}
          </ul>
          {report ? (
            <>
              <h5>Rapport v{report.version}</h5>
              <pre className="muted" style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem' }}>
                {JSON.stringify(report.report, null, 2)}
              </pre>
            </>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}

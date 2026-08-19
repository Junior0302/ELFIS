import { useCallback, useEffect, useState } from 'react'
import {
  classificationLabel,
  documentAnalysisApi,
  languageLabel,
  warningLabel,
  type AnalysisReport,
} from '../services/documentAnalysisApi'

type Props = {
  token: string
  orgId: number
  migrationSessionId: string
}

export default function MigrationAnalysisPanel({ token, orgId, migrationSessionId }: Props) {
  const [reports, setReports] = useState<AnalysisReport[]>([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [statusMessage, setStatusMessage] = useState('Analyse en cours')

  const reload = useCallback(async () => {
    const data = await documentAnalysisApi.listReports(token, orgId, migrationSessionId)
    setReports(data.items)
  }, [token, orgId, migrationSessionId])

  useEffect(() => {
    let cancelled = false
    async function boot() {
      try {
        await reload()
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Chargement analyse impossible')
      }
    }
    void boot()
    return () => {
      cancelled = true
    }
  }, [reload])

  async function runAnalysis() {
    setBusy(true)
    setError('')
    setStatusMessage('Analyse en cours')
    try {
      const result = await documentAnalysisApi.analyzeSession(token, orgId, migrationSessionId)
      await reload()
      if (result.errors.length) {
        setStatusMessage(`Analyse terminée avec ${result.errors.length} avertissement(s)`)
      } else {
        setStatusMessage(`${result.analyzed} document(s) prêts pour l’IA`)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Analyse impossible')
      setStatusMessage('Échec de l’analyse')
    } finally {
      setBusy(false)
    }
  }

  const completed = reports.filter((r) => r.status === 'completed')
  const avgQuality =
    completed.length > 0
      ? Math.round(
          completed.reduce((acc, r) => acc + (r.quality_score || 0), 0) / completed.length,
        )
      : null

  return (
    <div className="migration-analysis panel">
      <h3>Analyse documentaire</h3>
      <p className="muted">
        Préparation technique uniquement : qualité, langue, orientation, type détecté et décision
        OCR. Aucune extraction métier ni IA générative.
      </p>

      <div className="migration-analysis-toolbar">
        <button type="button" className="btn" disabled={busy} onClick={() => void runAnalysis()}>
          {busy ? 'Analyse en cours…' : 'Lancer l’analyse'}
        </button>
        <span className="muted">{statusMessage}</span>
      </div>

      {avgQuality != null ? (
        <p className="muted">Qualité moyenne : {avgQuality}/100 · {completed.length} rapport(s)</p>
      ) : null}

      {error ? <div className="form-error">{error}</div> : null}

      <ul className="migration-analysis-list">
        {reports.map((r) => (
          <li key={r.id} className={`is-${r.status}`}>
            <div className="migration-progress-bar" aria-label="Progression">
              <span style={{ width: `${r.progress_percent}%` }} />
            </div>
            <div>
              <strong>
                {r.universal_document_id || r.document_intake_item_id.slice(0, 8)}
                {r.detected_format ? ` · ${r.detected_format.toUpperCase()}` : ''}
              </strong>
              <p className="muted">
                ✔ Qualité {r.quality_score ?? '—'}
                {' · '}✔ Langue {languageLabel(r.language_code)}
                {' · '}✔ Orientation {r.orientation_degrees ?? 0}°
                {' · '}✔ Type {classificationLabel(r.classification_label)}
                {' · '}✔ OCR {r.need_ocr ? 'nécessaire' : 'inutile'}
              </p>
              {r.warnings?.length ? (
                <p className="muted">
                  Avertissements : {r.warnings.map(warningLabel).join(', ')}
                </p>
              ) : null}
              {r.error_message ? <p className="form-error">{r.error_message}</p> : null}
            </div>
          </li>
        ))}
      </ul>
      {!reports.length ? (
        <p className="muted">Aucun rapport. Déposez des fichiers puis lancez l’analyse.</p>
      ) : null}
    </div>
  )
}

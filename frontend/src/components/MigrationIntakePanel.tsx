import { useCallback, useEffect, useRef, useState } from 'react'
import {
  documentIntakeApi,
  formatBytes,
  intakeIcon,
  intakeStatusLabel,
  uploadSessionStatusLabel,
  type FormatCatalogItem,
  type IntakeItem,
  type UploadAnalytics,
  type UploadSession,
} from '../services/documentIntakeApi'

type Props = {
  token: string
  orgId: number
  migrationSessionId: string
}

type LocalProgress = { name: string; percent: number; done: boolean; error?: string }

export default function MigrationIntakePanel({ token, orgId, migrationSessionId }: Props) {
  const [items, setItems] = useState<IntakeItem[]>([])
  const [formats, setFormats] = useState<FormatCatalogItem[]>([])
  const [uploadSession, setUploadSession] = useState<UploadSession | null>(null)
  const [analytics, setAnalytics] = useState<UploadAnalytics | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const [progress, setProgress] = useState<LocalProgress[]>([])
  const [statusMessage, setStatusMessage] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  const folderRef = useRef<HTMLInputElement>(null)
  const resumeGuard = useRef(false)

  const accept = formats.flatMap((f) => f.extensions).join(',')
  const storageKey = documentIntakeApi.sessionStorageKey(migrationSessionId)

  const reloadAnalytics = useCallback(
    async (sessionId: string) => {
      const data = await documentIntakeApi.getAnalytics(token, orgId, sessionId)
      setAnalytics(data)
    },
    [token, orgId],
  )

  const reload = useCallback(async () => {
    const data = await documentIntakeApi.listItems(token, orgId, {
      migration_session_id: migrationSessionId,
      limit: 200,
    })
    setItems(data.items)
  }, [token, orgId, migrationSessionId])

  const ensureSession = useCallback(async () => {
    const stored = localStorage.getItem(storageKey)
    if (stored) {
      try {
        const existing = await documentIntakeApi.getUploadSession(token, orgId, stored)
        if (!['cancelled', 'expired', 'failed'].includes(existing.status)) {
          setUploadSession(existing)
          await reloadAnalytics(existing.id)
          return existing
        }
      } catch {
        localStorage.removeItem(storageKey)
      }
    }
    const created = await documentIntakeApi.createUploadSession(token, orgId, {
      migration_session_id: migrationSessionId,
    })
    localStorage.setItem(storageKey, created.id)
    setUploadSession(created)
    await reloadAnalytics(created.id)
    return created
  }, [token, orgId, migrationSessionId, storageKey, reloadAnalytics])

  useEffect(() => {
    let cancelled = false
    async function boot() {
      try {
        const [fmt] = await Promise.all([
          documentIntakeApi.formats(token, orgId),
          reload(),
          ensureSession(),
        ])
        if (!cancelled) setFormats(fmt.items)
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Chargement intake impossible')
      }
    }
    void boot()
    return () => {
      cancelled = true
    }
  }, [token, orgId, reload, ensureSession])

  useEffect(() => {
    const el = folderRef.current
    if (!el) return
    el.setAttribute('webkitdirectory', '')
    el.setAttribute('directory', '')
  }, [])

  async function refreshSession(sessionId: string) {
    const s = await documentIntakeApi.getUploadSession(token, orgId, sessionId)
    setUploadSession(s)
    await reloadAnalytics(sessionId)
  }

  async function uploadFiles(fileList: FileList | File[], relativePaths?: string[]) {
    const files = Array.from(fileList)
    if (!files.length) return
    setBusy(true)
    setError('')
    setStatusMessage('Dépôt en cours')
    setProgress(files.map((f) => ({ name: f.name, percent: 10, done: false })))
    try {
      let session = uploadSession
      if (!session || ['paused', 'cancelled', 'expired'].includes(session.status)) {
        if (session?.status === 'paused') {
          session = await documentIntakeApi.resumeUploadSession(token, orgId, session.id)
          setUploadSession(session)
          setStatusMessage('Reprise du dépôt')
        } else {
          session = await ensureSession()
        }
      }
      setProgress((prev) => prev.map((p) => ({ ...p, percent: 55 })))
      const keys = files.map((f, i) => `${session!.id}:${f.name}:${f.size}:${i}`)
      if (files.length === 1 && !relativePaths?.[0]) {
        await documentIntakeApi.uploadOne(token, orgId, files[0], {
          migration_session_id: migrationSessionId,
          upload_session_id: session.id,
          idempotency_key: keys[0],
          client_upload_id: keys[0],
        })
      } else {
        await documentIntakeApi.uploadBatch(token, orgId, files, {
          migration_session_id: migrationSessionId,
          upload_session_id: session.id,
          relative_paths: relativePaths,
          idempotency_keys: keys,
        })
      }
      setProgress((prev) => prev.map((p) => ({ ...p, percent: 100, done: true })))
      setStatusMessage('Validation des fichiers')
      await reload()
      await refreshSession(session.id)
      const a = await documentIntakeApi.getAnalytics(token, orgId, session.id)
      setAnalytics(a)
      if ((a.duplicate_count || 0) + (a.rejected_count || 0) + (a.quarantined_count || 0) > 0) {
        setStatusMessage('Dépôt terminé avec avertissements')
      } else {
        setStatusMessage('Dépôt en cours')
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload impossible')
      setProgress((prev) =>
        prev.map((p) => ({ ...p, done: true, error: e instanceof Error ? e.message : 'Erreur' })),
      )
    } finally {
      setBusy(false)
    }
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault()
    setDragOver(false)
    const dt = e.dataTransfer
    if (!dt.files?.length) return
    const paths: string[] = []
    for (const f of Array.from(dt.files)) {
      const rel = (f as File & { webkitRelativePath?: string }).webkitRelativePath
      paths.push(rel || f.name)
    }
    void uploadFiles(dt.files, paths)
  }

  async function cancelItem(id: string) {
    setBusy(true)
    setError('')
    try {
      await documentIntakeApi.cancel(token, orgId, id)
      await reload()
      if (uploadSession) await refreshSession(uploadSession.id)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Annulation impossible')
    } finally {
      setBusy(false)
    }
  }

  async function pauseSession() {
    if (!uploadSession) return
    setBusy(true)
    setError('')
    try {
      const s = await documentIntakeApi.pauseUploadSession(token, orgId, uploadSession.id)
      setUploadSession(s)
      setStatusMessage('Dépôt interrompu')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Pause impossible')
    } finally {
      setBusy(false)
    }
  }

  async function resumeSession() {
    if (!uploadSession || resumeGuard.current) return
    resumeGuard.current = true
    setBusy(true)
    setError('')
    try {
      const s = await documentIntakeApi.resumeUploadSession(token, orgId, uploadSession.id)
      setUploadSession(s)
      setStatusMessage('Reprise du dépôt')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Reprise impossible')
    } finally {
      resumeGuard.current = false
      setBusy(false)
    }
  }

  async function cancelSession() {
    if (!uploadSession) return
    setBusy(true)
    setError('')
    try {
      const s = await documentIntakeApi.cancelUploadSession(token, orgId, uploadSession.id)
      setUploadSession(s)
      localStorage.removeItem(storageKey)
      setStatusMessage('Dépôt annulé')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Annulation du lot impossible')
    } finally {
      setBusy(false)
    }
  }

  const globalPercent = analytics?.completion_percent ?? 0

  return (
    <div className="migration-intake panel">
      <h3>Dépôt de documents</h3>
      <p className="muted">
        Glissez vos fichiers ou un dossier. Les ZIP sont inventoriés sans extraction. Aucune analyse
        IA dans cette étape.
      </p>

      {uploadSession ? (
        <div className="migration-intake-session">
          <div>
            <strong>{uploadSession.display_label || 'Lot de dépôt'}</strong>
            <p className="muted">
              {uploadSessionStatusLabel(uploadSession.status)}
              {statusMessage ? ` · ${statusMessage}` : ''}
            </p>
            <p className="muted technical-ref">
              Référence interne · {uploadSession.internal_reference || uploadSession.id}
            </p>
          </div>
          <div className="migration-intake-session-actions">
            {uploadSession.status === 'uploading' || uploadSession.status === 'created' ? (
              <button type="button" className="btn secondary" disabled={busy} onClick={() => void pauseSession()}>
                Pause
              </button>
            ) : null}
            {uploadSession.status === 'paused' ? (
              <button type="button" className="btn secondary" disabled={busy} onClick={() => void resumeSession()}>
                Reprendre
              </button>
            ) : null}
            {!['cancelled', 'completed', 'expired'].includes(uploadSession.status) ? (
              <button type="button" className="btn secondary" disabled={busy} onClick={() => void cancelSession()}>
                Annuler le lot
              </button>
            ) : null}
          </div>
        </div>
      ) : null}

      {analytics ? (
        <div className="migration-intake-analytics">
          <div className="migration-progress-bar" aria-label="Progression globale">
            <span style={{ width: `${globalPercent}%` }} />
          </div>
          <p className="muted">
            {analytics.file_count} fichiers · {formatBytes(analytics.received_bytes)} ·{' '}
            {analytics.validated_count} validés · {analytics.duplicate_count} doublons ·{' '}
            {analytics.rejected_count} rejetés · {analytics.quarantined_count} quarantaine
            {analytics.average_upload_speed_bps != null
              ? ` · ${formatBytes(analytics.average_upload_speed_bps)}/s`
              : ''}
          </p>
        </div>
      ) : null}

      <div
        className={`migration-intake-dropzone ${dragOver ? 'is-dragover' : ''}`}
        onDragOver={(e) => {
          e.preventDefault()
          setDragOver(true)
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click()
        }}
        onClick={() => inputRef.current?.click()}
      >
        <strong>Glisser-déposer ici</strong>
        <span className="muted">PDF, Excel, CSV, images, ZIP, XML, JSON…</span>
        <div className="migration-intake-actions">
          <button
            type="button"
            className="btn secondary"
            disabled={busy || uploadSession?.status === 'paused'}
            onClick={(e) => {
              e.stopPropagation()
              inputRef.current?.click()
            }}
          >
            Choisir des fichiers
          </button>
          <button
            type="button"
            className="btn secondary"
            disabled={busy || uploadSession?.status === 'paused'}
            onClick={(e) => {
              e.stopPropagation()
              folderRef.current?.click()
            }}
          >
            Choisir un dossier
          </button>
        </div>
      </div>

      <input
        ref={inputRef}
        type="file"
        multiple
        accept={accept || undefined}
        hidden
        onChange={(e) => {
          if (e.target.files) void uploadFiles(e.target.files)
          e.target.value = ''
        }}
      />
      <input
        ref={folderRef}
        type="file"
        multiple
        hidden
        onChange={(e) => {
          if (!e.target.files) return
          const paths = Array.from(e.target.files).map(
            (f) => (f as File & { webkitRelativePath?: string }).webkitRelativePath || f.name,
          )
          void uploadFiles(e.target.files, paths)
          e.target.value = ''
        }}
      />

      {error ? <div className="form-error">{error}</div> : null}

      {progress.length > 0 ? (
        <ul className="migration-intake-progress">
          {progress.map((p) => (
            <li key={p.name}>
              <span>{p.name}</span>
              <div className="migration-progress-bar">
                <span style={{ width: `${p.percent}%` }} />
              </div>
              {p.error ? <span className="form-error">{p.error}</span> : null}
            </li>
          ))}
        </ul>
      ) : null}

      <ul className="migration-intake-list">
        {items.map((it) => (
          <li key={it.id} className={`is-${it.status}`}>
            <span className="migration-intake-icon">{intakeIcon(it.format_id)}</span>
            <div>
              <strong>{it.normalized_filename}</strong>
              <p className="muted">
                {intakeStatusLabel(it.lifecycle_status || it.status)} · {formatBytes(it.size_bytes)}
                {it.universal_document_id ? ` · ${it.universal_document_id}` : ''}
                {it.relative_path ? ` · ${it.relative_path}` : ''}
                {it.duplicate_type === 'exact' || it.is_duplicate ? ' · Doublon exact détecté' : ''}
                {it.status === 'quarantined' ? ' · Fichier placé en quarantaine' : ''}
                {it.status === 'rejected' ? ' · Fichier rejeté' : ''}
                {it.extract_later ? ' · extraction future' : ''}
              </p>
            </div>
            {it.status !== 'cancelled' ? (
              <button
                type="button"
                className="btn secondary"
                disabled={busy}
                onClick={() => void cancelItem(it.id)}
              >
                Annuler
              </button>
            ) : null}
          </li>
        ))}
      </ul>
      {!items.length ? <p className="muted">Aucun fichier déposé pour cette session.</p> : null}
    </div>
  )
}

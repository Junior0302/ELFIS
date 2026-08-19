import { useRef, useState } from 'react'
import { can } from '../../types/permissions'
import { uploadRegistryDocument, type RegistryDocument } from '../../services/documentRegistryApi'
import DocumentFileSummary from './DocumentFileSummary'
import DocumentUploadError from './DocumentUploadError'
import DocumentUploadProgress from './DocumentUploadProgress'

type Props = {
  token: string
  orgId?: number | null
  permissions?: readonly string[]
  onUploaded?: (doc: RegistryDocument) => void
}

export default function DocumentUpload({ token, orgId, permissions, onUploaded }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const abortRef = useRef<AbortController | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [progress, setProgress] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const allowed = can(permissions, 'documents.create') || can(permissions, 'documents.write') || can(permissions, '*')
  if (!allowed) return null

  async function startUpload() {
    if (!file || busy) return
    setError(null)
    setBusy(true)
    setProgress(0)
    abortRef.current = new AbortController()
    try {
      const doc = await uploadRegistryDocument({
        file,
        token,
        orgId,
        title: file.name,
        onProgress: setProgress,
        signal: abortRef.current.signal,
      })
      setFile(null)
      setProgress(100)
      onUploaded?.(doc)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Échec upload')
    } finally {
      setBusy(false)
      abortRef.current = null
    }
  }

  function cancel() {
    abortRef.current?.abort()
  }

  return (
    <div className="doc-upload">
      <input
        ref={inputRef}
        type="file"
        hidden
        onChange={(e) => {
          setFile(e.target.files?.[0] || null)
          setError(null)
          setProgress(0)
        }}
      />
      <div className="doc-upload__actions">
        <button type="button" className="platform-action" onClick={() => inputRef.current?.click()} disabled={busy}>
          Choisir un fichier
        </button>
        <button type="button" className="platform-action" onClick={startUpload} disabled={!file || busy}>
          Envoyer
        </button>
        {busy ? (
          <button type="button" className="platform-action" onClick={cancel}>
            Annuler
          </button>
        ) : null}
      </div>
      {file ? <DocumentFileSummary name={file.name} sizeBytes={file.size} mime={file.type} /> : null}
      {busy || progress > 0 ? <DocumentUploadProgress percent={progress} /> : null}
      {error ? <DocumentUploadError message={error} /> : null}
    </div>
  )
}

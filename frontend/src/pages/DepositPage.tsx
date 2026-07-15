import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'

const STEPS = ['OCR Document', 'Financial Validator', 'Accounting Mapper']

const ACCEPT = 'application/pdf,.pdf,image/jpeg,.jpg,.jpeg,image/png,.png,image/webp,.webp'

function isAllowed(file: File) {
  const name = file.name.toLowerCase()
  return (
    name.endsWith('.pdf') ||
    name.endsWith('.jpg') ||
    name.endsWith('.jpeg') ||
    name.endsWith('.png') ||
    name.endsWith('.webp')
  )
}

export default function DepositPage() {
  const navigate = useNavigate()
  const { token, orgId } = useAuth()
  const [active, setActive] = useState(false)
  const [loading, setLoading] = useState(false)
  const [step, setStep] = useState(0)
  const [error, setError] = useState('')
  const [fileName, setFileName] = useState('')

  useEffect(() => {
    if (!loading) return
    setStep(0)
    const timers = [
      window.setTimeout(() => setStep(1), 700),
      window.setTimeout(() => setStep(2), 1400),
    ]
    return () => timers.forEach((t) => window.clearTimeout(t))
  }, [loading])

  const upload = useCallback(
    async (file: File) => {
      setError('')
      setFileName(file.name)
      setLoading(true)
      try {
        if (!token) throw new Error('Authentification requise')
        const invoice = await api.uploadDocument(file, token, orgId)
        navigate(`/result/${invoice.id}`)
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Upload impossible')
        setLoading(false)
      }
    },
    [navigate, token, orgId],
  )

  const onFiles = (files: FileList | null) => {
    const file = files?.[0]
    if (!file) return
    if (!isAllowed(file)) {
      setError('Formats acceptés : PDF, JPG, PNG, WEBP.')
      return
    }
    if (file.size > 15 * 1024 * 1024) {
      setError('Fichier trop volumineux (max 15 Mo).')
      return
    }
    void upload(file)
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Déposer une facture</h2>
          <p>
            Glissez un PDF ou une photo : lecture automatique, extraction des montants et
            proposition d’écritures.
          </p>
        </div>
      </div>

      <div
        className={`dropzone ${active ? 'active' : ''} ${loading ? 'busy' : ''}`}
        onDragEnter={(e) => {
          e.preventDefault()
          setActive(true)
        }}
        onDragOver={(e) => {
          e.preventDefault()
          setActive(true)
        }}
        onDragLeave={() => setActive(false)}
        onDrop={(e) => {
          e.preventDefault()
          setActive(false)
          onFiles(e.dataTransfer.files)
        }}
      >
        <div>
          <h3>{loading ? 'Analyse en cours…' : 'PDF ou photo de facture'}</h3>
          <p>{loading ? fileName : 'Glissez-déposez. L’IA prépare la comptabilité fournisseur.'}</p>

          {loading ? (
            <ol className="pipeline-steps">
              {STEPS.map((label, index) => (
                <li key={label} className={index <= step ? 'done' : ''}>
                  {label}
                </li>
              ))}
            </ol>
          ) : (
            <label className="btn" style={{ cursor: 'pointer' }}>
              Choisir un fichier
              <input type="file" accept={ACCEPT} hidden onChange={(e) => onFiles(e.target.files)} />
            </label>
          )}

          {error && <p className="form-error">{error}</p>}
        </div>
      </div>
    </>
  )
}

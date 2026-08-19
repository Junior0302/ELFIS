import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, type PlatformOrgOpsDetail } from '../../api'
import { useAuth } from '../../auth'

export default function PlatformOrganizationDetailPage() {
  const { organizationId } = useParams()
  const { token } = useAuth()
  const [detail, setDetail] = useState<PlatformOrgOpsDetail | null>(null)
  const [error, setError] = useState('')
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const orgId = Number(organizationId)

  const reload = () => {
    if (!token || !orgId) return
    return api
      .platformOrgOpsDetail(orgId, token)
      .then(setDetail)
      .catch((reason) => setError(reason instanceof Error ? reason.message : 'Fiche indisponible'))
  }

  useEffect(() => {
    void reload()
  }, [token, orgId])

  const runAction = async (kind: 'suspend' | 'restore') => {
    if (!token || !orgId) return
    if (reason.trim().length < 3) {
      setError('Indiquez une raison administrative (min. 3 caractères).')
      return
    }
    const label = kind === 'suspend' ? 'suspendre' : 'restaurer'
    if (!window.confirm(`Confirmer : ${label} cette organisation ?`)) return
    setBusy(true)
    setError('')
    setMessage('')
    try {
      if (kind === 'suspend') await api.platformSuspendOrganization(orgId, reason.trim(), token)
      else await api.platformRestoreOrganization(orgId, reason.trim(), token)
      setMessage(kind === 'suspend' ? 'Organisation suspendue.' : 'Organisation restaurée.')
      setReason('')
      await reload()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Action impossible')
    } finally {
      setBusy(false)
    }
  }

  if (!detail && !error) return <div className="platform-loading">Chargement…</div>
  if (error && !detail) return <div className="platform-alert">{error}</div>
  if (!detail) return null

  const org = detail.organization
  const suspended = org.platform_status === 'suspended'

  return (
    <>
      <div className="platform-title">
        <Link to="/elfadmin/organisations">← Organisations</Link>
        <h1>{org.name}</h1>
        <p>
          Statut plateforme : <strong>{org.platform_status}</strong>
        </p>
      </div>
      {message && <div className="platform-return">{message}</div>}
      {error && <div className="platform-alert">{error}</div>}

      <section className="panel">
        <h2>Vue générale</h2>
        <ul>
          <li>Documents : {detail.counts.documents ?? 0}</li>
          <li>Exécutions IA : {detail.counts.ai_executions ?? 0}</li>
          <li>Propositions comptables : {detail.counts.accounting_proposals ?? 0}</li>
          <li>Jobs failed : {detail.counts.jobs_failed ?? 0}</li>
        </ul>
      </section>

      <section className="panel">
        <h2>Utilisateurs</h2>
        <ul>
          {detail.users.map((u) => (
            <li key={u.user_id}>
              {u.email} — {u.role} ({u.status})
            </li>
          ))}
        </ul>
      </section>

      <section className="panel">
        <h2>Action sensible</h2>
        <p>
          La suspension bloque les traitements coûteux (IA, uploads, e-mails) tout en conservant la
          consultation des données. Stripe n’est pas annulé automatiquement.
        </p>
        <label>
          Raison administrative
          <textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={3} />
        </label>
        <div className="platform-toolbar">
          {!suspended ? (
            <button type="button" className="btn" disabled={busy} onClick={() => void runAction('suspend')}>
              Suspendre
            </button>
          ) : (
            <button type="button" className="btn" disabled={busy} onClick={() => void runAction('restore')}>
              Restaurer
            </button>
          )}
        </div>
      </section>
    </>
  )
}

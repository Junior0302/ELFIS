import { useEffect, useState } from 'react'
import { api, type PlatformAuditRow } from '../../api'
import { useAuth } from '../../auth'

export default function PlatformAuditPage() {
  const { token } = useAuth()
  const [rows, setRows] = useState<PlatformAuditRow[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) return
    api
      .platformAudit(token)
      .then((r) => setRows(r.audits))
      .catch((reason) => setError(reason instanceof Error ? reason.message : 'Audit indisponible'))
  }, [token])

  return (
    <>
      <div className="platform-title">
        <h1>Audit administratif</h1>
        <p>Actions plateforme filtrées — sans secrets ni payloads sensibles.</p>
      </div>
      {error && <div className="platform-alert">{error}</div>}
      <div className="platform-table-wrap">
        <table className="platform-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Acteur</th>
              <th>Action</th>
              <th>Cible</th>
              <th>Org</th>
              <th>Statut</th>
              <th>Raison</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.audit_id}>
                <td>{r.created_at}</td>
                <td>{r.actor_email}</td>
                <td>{r.action}</td>
                <td>
                  {r.target_type}:{r.target_id}
                </td>
                <td>{r.organization_id ?? '—'}</td>
                <td>{r.status}</td>
                <td>{r.reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}

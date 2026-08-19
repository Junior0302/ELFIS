import type { SystemLogEntry } from '../../types/systemHealth'

export default function SystemLogTable({ entries }: { entries: SystemLogEntry[] }) {
  if (!entries.length) {
    return <p>Aucun journal pour ces filtres.</p>
  }
  return (
    <div className="platform-table-wrap">
      <table className="platform-table">
        <thead>
          <tr>
            <th>Date / heure</th>
            <th>Niveau</th>
            <th>Service</th>
            <th>Événement</th>
            <th>Message</th>
            <th>Correlation</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((e) => (
            <tr key={e.log_id}>
              <td>{new Date(e.timestamp).toLocaleString('fr-FR')}</td>
              <td>
                <span className={`platform-pill health-log-${e.level}`}>{e.level}</span>
              </td>
              <td>{e.service_id || '—'}</td>
              <td>{e.event_type}</td>
              <td>{e.message}</td>
              <td>
                <code>{e.correlation_id || '—'}</code>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

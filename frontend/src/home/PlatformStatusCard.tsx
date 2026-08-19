type PlatformStatusCardProps = {
  orgName: string
  /** Connexion utilisateur authentifiée. */
  connected?: boolean
  /** Sync notifications active (SSE/polling). */
  syncOk?: boolean
  /** Dernière vérif affichée (libellé relatif). */
  lastCheckLabel?: string
}

type CheckItem = {
  id: string
  label: string
  ok: boolean
  detail: string
}

export function PlatformStatusCard({
  orgName,
  connected = true,
  syncOk = true,
  lastCheckLabel = 'à l’instant',
}: PlatformStatusCardProps) {
  const orgOk = Boolean(orgName && orgName !== '—')
  const checks: CheckItem[] = [
    {
      id: 'connection',
      label: 'Connexion',
      ok: connected,
      detail: connected ? 'Active' : 'Hors ligne',
    },
    {
      id: 'org',
      label: 'Organisation',
      ok: orgOk,
      detail: orgOk ? 'OK' : 'Non sélectionnée',
    },
    {
      id: 'sync',
      label: 'Synchronisation',
      ok: syncOk,
      detail: syncOk ? 'OK' : 'En attente',
    },
    {
      id: 'services',
      label: 'Services',
      ok: connected,
      detail: connected ? 'Opérationnels' : 'Indisponibles',
    },
  ]

  const allOk = checks.every((c) => c.ok)

  return (
    <section
      className="home-status"
      id="home-status"
      aria-labelledby="home-status-title"
    >
      <div className="home-status__card">
        <p className="home-status__eyebrow" id="home-status-title">
          Statut plateforme
        </p>
        <p className="home-status__ok" role="status">
          {allOk ? 'Tout fonctionne parfaitement' : 'Certains éléments demandent attention'}
        </p>
        <ul className="home-status__checklist">
          {checks.map((item) => (
            <li key={item.id} className={item.ok ? 'is-ok' : 'is-warn'}>
              <span className="home-status__check" aria-hidden>
                {item.ok ? '✓' : '!'}
              </span>
              <span className="home-status__check-label">
                {item.label} {item.detail}
              </span>
            </li>
          ))}
        </ul>
        <p className="home-status__footer">Dernière vérification : {lastCheckLabel}</p>
      </div>
    </section>
  )
}

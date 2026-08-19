/** Types Permission Engine — préparation RC2.2 (décision réelle = backend). */

export type Permission =
  | 'system.health.read'
  | 'system.health.refresh'
  | 'system.metrics.read'
  | 'system.alerts.read'
  | 'system.logs.read'
  | 'jobs.read'
  | 'events.read'
  | 'platform.dashboard.read'
  | 'security.audit.read'
  | 'security.audit.export'
  | 'security.audit.retention.read'
  | 'security.audit.retention.manage'
  | 'documents.read'
  | 'documents.create'
  | 'documents.write'
  | 'documents.download'
  | 'documents.archive'
  | 'documents.manage'
  | 'storage.quarantine.read'
  | 'storage.quarantine.manage'
  | string

/**
 * Vérifie si un ensemble de permissions (serveur) contient la permission demandée.
 * Limite actuelle : le frontend org utilise les permissions membership ComptaPilot ;
 * le catalogue IAM plateforme complet n'est pas toujours chargé côté client.
 */
export function can(granted: readonly string[] | Set<string> | undefined, permission: Permission): boolean {
  if (!granted) return false
  if (granted instanceof Set) return granted.has(permission) || granted.has('*')
  return granted.includes(permission) || granted.includes('*')
}

import { useRef } from 'react'
import type { AuditEvent } from '../../types/audit'
import { Drawer } from '../../design-system'
import AuditCategoryBadge from './AuditCategoryBadge'
import AuditSeverityBadge from './AuditSeverityBadge'
import AuditStatusBadge from './AuditStatusBadge'
import {
  formatLocalTime,
  formatUtcFull,
  maskIp,
  narrativeForEvent,
  safeMetadataEntries,
  simplifyUserAgent,
} from './auditDisplay'

type Props = {
  event: AuditEvent | null
  open: boolean
  onClose: () => void
}

/**
 * E1.4.1 — migrated to ELFIS Drawer (API props inchangée).
 */
export default function AuditEventDetailsDrawer({ event, open, onClose }: Props) {
  const closeRef = useRef<HTMLButtonElement>(null)
  const meta = event ? safeMetadataEntries(event.metadata) : []

  return (
    <Drawer
      open={open && Boolean(event)}
      onOpenChange={(next) => {
        if (!next) onClose()
      }}
      side="right"
      size="md"
      modal
      title="Détail de l'événement"
      description={event ? narrativeForEvent(event) : undefined}
      initialFocusRef={closeRef}
      footer={
        <button ref={closeRef} type="button" className="platform-btn" onClick={onClose}>
          Fermer
        </button>
      }
    >
      {event ? (
        <>
          <dl className="audit-drawer-grid">
            <div>
              <dt>Identifiant</dt>
              <dd>
                <code>{event.id}</code>
              </dd>
            </div>
            <div>
              <dt>Date (locale)</dt>
              <dd>{formatLocalTime(event.occurred_at)}</dd>
            </div>
            <div>
              <dt>Date UTC</dt>
              <dd>{formatUtcFull(event.occurred_at)}</dd>
            </div>
            <div>
              <dt>Catégorie</dt>
              <dd>
                <AuditCategoryBadge category={event.category} />
              </dd>
            </div>
            <div>
              <dt>Action</dt>
              <dd>{event.action}</dd>
            </div>
            <div>
              <dt>Statut</dt>
              <dd>
                <AuditStatusBadge status={event.status} success={event.success} />
              </dd>
            </div>
            <div>
              <dt>Sévérité</dt>
              <dd>
                <AuditSeverityBadge severity={event.severity} />
              </dd>
            </div>
            <div>
              <dt>Succès</dt>
              <dd>{event.success ? 'oui' : 'non'}</dd>
            </div>
            <div>
              <dt>Acteur</dt>
              <dd>
                {event.actor_email || '—'}
                {event.actor_user_id != null ? ` (#${event.actor_user_id})` : ''}
              </dd>
            </div>
            <div>
              <dt>Cible</dt>
              <dd>
                {event.target_display || event.target_id || '—'}
                {event.target_type ? ` (${event.target_type})` : ''}
              </dd>
            </div>
            <div>
              <dt>Organisation</dt>
              <dd>{event.organization_id != null ? `#${event.organization_id}` : '—'}</dd>
            </div>
            <div>
              <dt>Produit</dt>
              <dd>{event.product || '—'}</dd>
            </div>
            <div>
              <dt>Service</dt>
              <dd>{event.service || '—'}</dd>
            </div>
            <div>
              <dt>request_id</dt>
              <dd>
                <code>{event.request_id || '—'}</code>
              </dd>
            </div>
            <div>
              <dt>correlation_id</dt>
              <dd>
                <code>{event.correlation_id || '—'}</code>
              </dd>
            </div>
            <div>
              <dt>Durée</dt>
              <dd>{event.duration_ms != null ? `${event.duration_ms} ms` : '—'}</dd>
            </div>
            <div>
              <dt>IP</dt>
              <dd>{maskIp(event.ip_address)}</dd>
            </div>
            <div>
              <dt>User-Agent</dt>
              <dd>{simplifyUserAgent(event.user_agent)}</dd>
            </div>
            <div>
              <dt>Message</dt>
              <dd>{event.message || '—'}</dd>
            </div>
          </dl>
          <section className="audit-drawer-meta" aria-label="Métadonnées">
            <h3>Métadonnées</h3>
            {meta.length === 0 ? (
              <p className="audit-muted">Aucune métadonnée affichable.</p>
            ) : (
              <ul>
                {meta.map(([k, v]) => (
                  <li key={k}>
                    <strong>{k}</strong>: {v}
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      ) : null}
    </Drawer>
  )
}

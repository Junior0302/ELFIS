/**
 * Sales Focus card — priorité commerciale principale (backend-driven).
 */
import { Link } from 'react-router-dom'
import { Badge, Section } from '../design-system'
import {
  focusToneLabel,
  intelligencePath,
  severityTone,
  type SalesFocus,
} from './salesIntelligence'

type Props = {
  focus: SalesFocus
  compact?: boolean
}

export function SalesFocusCard({ focus, compact = false }: Props) {
  const detailHref =
    focus.insight_id != null ? intelligencePath(focus.insight_id) : focus.route || intelligencePath()

  return (
    <Section
      title="Priorité du moment"
      spacing="compact"
      className={compact ? 'sales-focus sales-focus--compact' : 'sales-focus'}
    >
      <div className="sales-workspace__header-meta">
        <Badge tone={severityTone(focus.severity)}>{focusToneLabel(focus.tone)}</Badge>
        <Badge tone="neutral">{focus.severity}</Badge>
      </div>
      <h3 className="sales-focus__title">{focus.title}</h3>
      <p>{focus.summary}</p>
      {!compact ? (
        <p className="muted">
          <strong>Pourquoi maintenant :</strong> {focus.reason}
        </p>
      ) : null}
      <div className="sales-deal__header-actions">
        {focus.route || focus.insight_id != null ? (
          <Link to={detailHref} className="ds-btn btn primary">
            {focus.action_label || 'Ouvrir'}
          </Link>
        ) : (
          <Link to="/sales/pipeline" className="ds-btn btn primary">
            {focus.action_label || 'Examiner le pipeline'}
          </Link>
        )}
        <Link to={intelligencePath()} className="ds-btn btn secondary">
          Voir toutes les recommandations
        </Link>
      </div>
      <p className="muted">
        Mis à jour : {new Date(focus.generated_at).toLocaleString('fr-FR')}
      </p>
    </Section>
  )
}

import { UiBadge } from '../ui/UiStates'
import type { DecisionEvidence } from '../decisionCenter'

type Props = {
  evidence: DecisionEvidence[]
}

export default function DecisionEvidenceList({ evidence }: Props) {
  if (!evidence.length) {
    return <p className="muted">Aucune preuve structurée disponible pour cette décision.</p>
  }
  return (
    <ul className="decision-evidence-list" aria-label="Preuves">
      {evidence.map((item, index) => (
        <li key={`${item.type}-${index}`} className="decision-evidence-item">
          <div className="decision-evidence-head">
            <UiBadge tone="neutral">{item.label}</UiBadge>
            {item.value ? <strong>{item.value}</strong> : null}
          </div>
          {item.description ? <p className="muted">{item.description}</p> : null}
        </li>
      ))}
    </ul>
  )
}

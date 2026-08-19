import { executionStatusLabel } from '../decisionCenter'
import { UiBadge } from '../ui/UiStates'

type Props = {
  status?: string | null
  errorMessage?: string | null
}

export default function DecisionExecutionStatusBadge({ status, errorMessage }: Props) {
  const value = status || 'idle'
  return (
    <div className="decision-execution-status">
      <UiBadge tone={value === 'failed' ? 'warn' : value === 'succeeded' ? 'ok' : 'neutral'}>
        Exécution : {executionStatusLabel(value)}
      </UiBadge>
      {errorMessage ? (
        <p className="form-error" role="alert">
          {errorMessage}
        </p>
      ) : null}
    </div>
  )
}

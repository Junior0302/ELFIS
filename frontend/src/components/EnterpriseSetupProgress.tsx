import { enterpriseSetupProgress, type EnterpriseSetupStepId } from '../enterpriseSetup'

type Props = {
  stepId: EnterpriseSetupStepId
}

/** Indicateur de progression léger — source = ENTERPRISE_SETUP_STEPS. */
export default function EnterpriseSetupProgress({ stepId }: Props) {
  const { label, current, total } = enterpriseSetupProgress(stepId)
  return (
    <p
      className="enterprise-setup-progress"
      aria-label={`Progression : ${label}`}
    >
      <span aria-hidden="true">
        Étape {current} sur {total}
      </span>
    </p>
  )
}

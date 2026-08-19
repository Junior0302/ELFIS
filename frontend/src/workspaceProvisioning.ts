/** Helpers UI — mapping étapes backend → libellés accessibles. */

export type ProvisionUiStepId =
  | 'validating_setup'
  | 'saving_company_profile'
  | 'configuring_workspace'
  | 'completing_setup'

export const PROVISION_UI_STEPS: { id: ProvisionUiStepId; label: string }[] = [
  { id: 'validating_setup', label: 'Vérification de vos informations' },
  { id: 'saving_company_profile', label: 'Enregistrement de votre entreprise' },
  { id: 'configuring_workspace', label: 'Configuration de votre espace' },
  { id: 'completing_setup', label: 'Finalisation' },
]

export type ProvisionUiStepState = 'upcoming' | 'current' | 'done' | 'error'

const STEP_ORDER: ProvisionUiStepId[] = PROVISION_UI_STEPS.map((s) => s.id)

export function resolveProvisionUiStepState(
  stepId: ProvisionUiStepId,
  currentStep: string,
  status: string,
): ProvisionUiStepState {
  if (status === 'failed') {
    const currentIdx = STEP_ORDER.indexOf(currentStep as ProvisionUiStepId)
    const thisIdx = STEP_ORDER.indexOf(stepId)
    if (currentIdx < 0) return stepId === 'validating_setup' ? 'error' : 'upcoming'
    if (thisIdx < currentIdx) return 'done'
    if (thisIdx === currentIdx) return 'error'
    return 'upcoming'
  }
  if (status === 'completed' || currentStep === 'completed') {
    return 'done'
  }
  const currentIdx = STEP_ORDER.indexOf(
    currentStep === 'pending' ? 'validating_setup' : (currentStep as ProvisionUiStepId),
  )
  const thisIdx = STEP_ORDER.indexOf(stepId)
  if (currentIdx < 0) return thisIdx === 0 ? 'current' : 'upcoming'
  if (thisIdx < currentIdx) return 'done'
  if (thisIdx === currentIdx) return 'current'
  return 'upcoming'
}

export function provisionStepLabel(state: ProvisionUiStepState): string {
  if (state === 'done') return 'terminée'
  if (state === 'current') return 'en cours'
  if (state === 'error') return 'erreur'
  return 'à venir'
}

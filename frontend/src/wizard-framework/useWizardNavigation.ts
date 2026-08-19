/**
 * Hook de navigation générique pour wizards multi-étapes.
 * Pas de logique métier — uniquement ordre / index / transitions.
 */
import { useCallback, useMemo, useState } from 'react'
import type { WizardStepDefinition, WizardStepId, WizardStepStatus } from './types'

export type UseWizardNavigationOptions = {
  steps: readonly WizardStepDefinition[]
  initialStepId?: WizardStepId
  /** Empêche d’avancer tant que false */
  canLeaveStep?: (stepId: WizardStepId) => boolean
  onStepChange?: (stepId: WizardStepId, previousId: WizardStepId) => void
}

export type UseWizardNavigationResult = {
  steps: readonly WizardStepDefinition[]
  currentStepId: WizardStepId
  currentIndex: number
  currentStep: WizardStepDefinition | undefined
  isFirst: boolean
  isLast: boolean
  canGoNext: boolean
  canGoBack: boolean
  goNext: () => void
  goBack: () => void
  goToStep: (stepId: WizardStepId) => void
  stepStatuses: Record<WizardStepId, WizardStepStatus>
  completedStepIds: Set<WizardStepId>
  markCompleted: (stepId: WizardStepId) => void
}

function visibleSteps(steps: readonly WizardStepDefinition[]): WizardStepDefinition[] {
  return steps.filter((s) => !s.hidden)
}

export function useWizardNavigation(
  options: UseWizardNavigationOptions,
): UseWizardNavigationResult {
  const { steps, initialStepId, canLeaveStep, onStepChange } = options
  const ordered = useMemo(() => visibleSteps(steps), [steps])

  const initial =
    initialStepId && ordered.some((s) => s.id === initialStepId)
      ? initialStepId
      : ordered[0]?.id ?? ''

  const [currentStepId, setCurrentStepId] = useState<WizardStepId>(initial)
  const [completed, setCompleted] = useState<Set<WizardStepId>>(() => new Set())

  const currentIndex = Math.max(
    0,
    ordered.findIndex((s) => s.id === currentStepId),
  )
  const currentStep = ordered[currentIndex]
  const isFirst = currentIndex <= 0
  const isLast = currentIndex >= ordered.length - 1

  const canGoBack = !isFirst
  const canGoNext =
    !isLast && (canLeaveStep ? canLeaveStep(currentStepId) : true)

  const goToStep = useCallback(
    (stepId: WizardStepId) => {
      if (!ordered.some((s) => s.id === stepId)) return
      const targetIndex = ordered.findIndex((s) => s.id === stepId)
      // Navigation libre vers étapes déjà atteintes / complétées, ou adjacente
      const maxReachable = Math.max(
        currentIndex,
        ...[...completed].map((id) => ordered.findIndex((s) => s.id === id)),
      )
      if (targetIndex > maxReachable + 1) return
      setCurrentStepId((prev) => {
        if (prev !== stepId) onStepChange?.(stepId, prev)
        return stepId
      })
    },
    [ordered, currentIndex, completed, onStepChange],
  )

  const goNext = useCallback(() => {
    if (!canGoNext || isLast) return
    const next = ordered[currentIndex + 1]
    if (!next) return
    setCompleted((prev) => {
      const nextSet = new Set(prev)
      nextSet.add(currentStepId)
      return nextSet
    })
    setCurrentStepId((prev) => {
      onStepChange?.(next.id, prev)
      return next.id
    })
  }, [canGoNext, isLast, ordered, currentIndex, currentStepId, onStepChange])

  const goBack = useCallback(() => {
    if (!canGoBack) return
    const prevStep = ordered[currentIndex - 1]
    if (!prevStep) return
    setCurrentStepId((cur) => {
      onStepChange?.(prevStep.id, cur)
      return prevStep.id
    })
  }, [canGoBack, ordered, currentIndex, onStepChange])

  const markCompleted = useCallback((stepId: WizardStepId) => {
    setCompleted((prev) => {
      const next = new Set(prev)
      next.add(stepId)
      return next
    })
  }, [])

  const stepStatuses = useMemo(() => {
    const map: Record<string, WizardStepStatus> = {}
    ordered.forEach((step, index) => {
      if (step.id === currentStepId) {
        map[step.id] = 'current'
      } else if (completed.has(step.id) || index < currentIndex) {
        map[step.id] = 'completed'
      } else {
        map[step.id] = 'upcoming'
      }
    })
    return map
  }, [ordered, currentStepId, completed, currentIndex])

  return {
    steps: ordered,
    currentStepId,
    currentIndex,
    currentStep,
    isFirst,
    isLast,
    canGoNext,
    canGoBack,
    goNext,
    goBack,
    goToStep,
    stepStatuses,
    completedStepIds: completed,
    markCompleted,
  }
}

import type { ReactNode } from 'react'
import { cx } from '../design-system'
import type {
  WizardActionDef,
  WizardContainerProps,
  WizardDefinition,
  WizardNavigationHandlers,
  WizardStepDefinition,
  WizardStepStatus,
  WizardValidationIssue,
} from './types'
import './wizard-framework.css'

function statusLabel(status: WizardStepStatus): string {
  switch (status) {
    case 'current':
      return 'En cours'
    case 'completed':
      return 'Terminé'
    case 'skipped':
      return 'Ignoré'
    case 'error':
      return 'Erreur'
    case 'blocked':
      return 'Bloqué'
    default:
      return 'À venir'
  }
}

export function WizardProgress({
  steps,
  currentStepId,
  stepStatuses,
}: {
  steps: readonly WizardStepDefinition[]
  currentStepId: string
  stepStatuses?: Partial<Record<string, WizardStepStatus>>
}) {
  const currentIndex = Math.max(
    0,
    steps.findIndex((s) => s.id === currentStepId),
  )
  const pct = steps.length <= 1 ? 100 : Math.round((currentIndex / (steps.length - 1)) * 100)

  return (
    <div
      className="elf-wiz-progress"
      role="progressbar"
      aria-valuenow={pct}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={`Progression : étape ${currentIndex + 1} sur ${steps.length}`}
    >
      <div className="elf-wiz-progress__track">
        <div className="elf-wiz-progress__fill" style={{ width: `${pct}%` }} />
      </div>
      <ol className="elf-wiz-progress__dots" aria-hidden="true">
        {steps.map((step) => {
          const status = stepStatuses?.[step.id] ?? 'upcoming'
          return (
            <li
              key={step.id}
              className={cx('elf-wiz-progress__dot', `elf-wiz-progress__dot--${status}`)}
              title={step.label}
            />
          )
        })}
      </ol>
    </div>
  )
}

export function WizardSidebar({
  definition,
  onSelectStep,
}: {
  definition: WizardDefinition
  onSelectStep?: (stepId: string) => void
}) {
  const visible = definition.steps.filter((s) => !s.hidden)
  return (
    <nav className="elf-wiz-sidebar" aria-label="Étapes du parcours">
      <ol className="elf-wiz-sidebar__list">
        {visible.map((step, index) => {
          const status =
            definition.stepStatuses?.[step.id] ??
            (step.id === definition.currentStepId
              ? 'current'
              : 'upcoming')
          const isCurrent = step.id === definition.currentStepId
          return (
            <li key={step.id}>
              <button
                type="button"
                className={cx(
                  'elf-wiz-sidebar__item',
                  `elf-wiz-sidebar__item--${status}`,
                  isCurrent && 'is-current',
                )}
                aria-current={isCurrent ? 'step' : undefined}
                disabled={status === 'upcoming' && !onSelectStep}
                onClick={() => onSelectStep?.(step.id)}
              >
                <span className="elf-wiz-sidebar__index" aria-hidden="true">
                  {status === 'completed' ? '✓' : index + 1}
                </span>
                <span className="elf-wiz-sidebar__text">
                  <span className="elf-wiz-sidebar__label">{step.label}</span>
                  {step.description ? (
                    <span className="elf-wiz-sidebar__desc">{step.description}</span>
                  ) : null}
                  <span className="elf-wiz-sidebar__status">{statusLabel(status)}</span>
                </span>
              </button>
            </li>
          )
        })}
      </ol>
    </nav>
  )
}

export function WizardStep({
  id,
  title,
  description,
  children,
  active = true,
}: {
  id: string
  title?: string
  description?: string
  children?: ReactNode
  active?: boolean
}) {
  if (!active) return null
  return (
    <section
      className="elf-wiz-step"
      data-wizard-step={id}
      aria-labelledby={title ? `elf-wiz-step-title-${id}` : undefined}
    >
      {title ? (
        <header className="elf-wiz-step__header">
          <h2 className="elf-wiz-step__title" id={`elf-wiz-step-title-${id}`}>
            {title}
          </h2>
          {description ? <p className="elf-wiz-step__desc">{description}</p> : null}
        </header>
      ) : null}
      <div className="elf-wiz-step__body">{children}</div>
    </section>
  )
}

export function WizardActions({ actions }: { actions: WizardActionDef[] }) {
  if (!actions.length) return null
  return (
    <div className="elf-wiz-actions" role="group" aria-label="Actions">
      {actions.map((action) => {
        const className = cx(
          'elf-wiz-action',
          `elf-wiz-action--${action.tone ?? 'secondary'}`,
          action.loading && 'is-loading',
        )
        const title = action.disabled && action.disabledReason ? action.disabledReason : undefined
        if (action.href && !action.disabled) {
          return (
            <a key={action.id} className={className} href={action.href} title={title}>
              {action.label}
            </a>
          )
        }
        return (
          <button
            key={action.id}
            type="button"
            className={className}
            onClick={action.onClick}
            disabled={action.disabled || action.loading}
            title={title}
            aria-busy={action.loading || undefined}
          >
            {action.label}
          </button>
        )
      })}
    </div>
  )
}

export function WizardNavigation({
  navigation,
  extraActions,
}: {
  navigation?: WizardNavigationHandlers
  extraActions?: WizardActionDef[]
}) {
  if (!navigation && !extraActions?.length) return null
  return (
    <div className="elf-wiz-nav">
      <div className="elf-wiz-nav__start">
        {navigation?.goBack ? (
          <button
            type="button"
            className="elf-wiz-action elf-wiz-action--ghost"
            onClick={navigation.goBack}
            disabled={!navigation.canGoBack}
          >
            {navigation.backLabel ?? 'Retour'}
          </button>
        ) : null}
      </div>
      <div className="elf-wiz-nav__end">
        {extraActions ? <WizardActions actions={extraActions} /> : null}
        {navigation?.goNext ? (
          <button
            type="button"
            className="elf-wiz-action elf-wiz-action--primary"
            onClick={navigation.goNext}
            disabled={!navigation.canGoNext}
          >
            {navigation.nextLabel ?? 'Continuer'}
          </button>
        ) : null}
      </div>
    </div>
  )
}

export function WizardFooter({ children }: { children?: ReactNode }) {
  return <footer className="elf-wiz-footer">{children}</footer>
}

export function WizardSummary({
  title = 'Résumé',
  items,
  children,
}: {
  title?: string
  items?: Array<{ label: string; value: ReactNode }>
  children?: ReactNode
}) {
  return (
    <aside className="elf-wiz-summary" aria-label={title}>
      <h3 className="elf-wiz-summary__title">{title}</h3>
      {items?.length ? (
        <dl className="elf-wiz-summary__list">
          {items.map((item) => (
            <div key={item.label} className="elf-wiz-summary__row">
              <dt>{item.label}</dt>
              <dd>{item.value}</dd>
            </div>
          ))}
        </dl>
      ) : null}
      {children}
    </aside>
  )
}

export function WizardValidation({
  issues,
  emptyMessage = 'Aucun contrôle à signaler',
}: {
  issues: WizardValidationIssue[]
  emptyMessage?: string
}) {
  if (!issues.length) {
    return (
      <div className="elf-wiz-validation elf-wiz-validation--empty" role="status">
        <p>{emptyMessage}</p>
      </div>
    )
  }
  return (
    <ul className="elf-wiz-validation" aria-label="Contrôles">
      {issues.map((issue) => (
        <li
          key={issue.id}
          className={cx('elf-wiz-validation__item', `elf-wiz-validation__item--${issue.severity}`)}
        >
          <span className="elf-wiz-validation__severity">{issue.severity}</span>
          <span className="elf-wiz-validation__msg">{issue.message}</span>
        </li>
      ))}
    </ul>
  )
}

export function WizardContainer({
  definition,
  navigation,
  children,
  sidebar,
  footer,
  summary,
  className,
  showSidebar = true,
  showProgress = true,
}: WizardContainerProps) {
  const visibleSteps = definition.steps.filter((s) => !s.hidden)
  return (
    <div
      className={cx('elf-wiz', className)}
      data-wizard-id={definition.id}
      data-wizard-step={definition.currentStepId}
    >
      <header className="elf-wiz__header">
        <div className="elf-wiz__intro">
          <h1 className="elf-wiz__title">{definition.title}</h1>
          {definition.description ? (
            <p className="elf-wiz__description">{definition.description}</p>
          ) : null}
        </div>
        {showProgress ? (
          <WizardProgress
            steps={visibleSteps}
            currentStepId={definition.currentStepId}
            stepStatuses={definition.stepStatuses}
          />
        ) : null}
      </header>

      <div className={cx('elf-wiz__layout', showSidebar && 'elf-wiz__layout--with-sidebar')}>
        {showSidebar ? (
          <div className="elf-wiz__sidebar-slot">
            {sidebar ?? (
              <WizardSidebar definition={definition} onSelectStep={navigation?.goToStep} />
            )}
          </div>
        ) : null}

        <div className="elf-wiz__main">
          <div className="elf-wiz__content">{children}</div>
          {summary ? <div className="elf-wiz__summary-slot">{summary}</div> : null}
        </div>
      </div>

      <WizardFooter>
        {footer ?? <WizardNavigation navigation={navigation} />}
      </WizardFooter>
    </div>
  )
}

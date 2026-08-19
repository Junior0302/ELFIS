import type { ReactNode } from 'react'
import { cx } from '../design-system'
import {
  InsightList,
  mapComposerIssuesToInsights,
} from '../insight-framework'
import type {
  ComposerActionDef,
  ComposerAutosaveState,
  ComposerDefinition,
  ComposerDocStatus,
  ComposerLayoutProps,
  ComposerNavigationHandlers,
  ComposerPreviewState,
  ComposerStepDefinition,
  ComposerStepStatus,
  ComposerValidationIssue,
} from './types'
import './composer-framework.css'

function stepStatusLabel(status: ComposerStepStatus): string {
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

function formatSavedAgo(savedAt: number, now = Date.now()): string {
  const sec = Math.max(0, Math.floor((now - savedAt) / 1000))
  if (sec < 5) return 'à l’instant'
  if (sec < 60) return `il y a ${sec} s`
  const min = Math.floor(sec / 60)
  return `il y a ${min} min`
}

export function ComposerStatus({
  autosave,
  statusLabel,
  documentType,
  status,
  statusHint,
  statusIcon,
}: {
  autosave?: ComposerAutosaveState
  statusLabel?: string
  documentType?: string
  status?: ComposerDocStatus
  statusHint?: string
  statusIcon?: string
}) {
  return (
    <div className="elf-cmp-status" role="status" aria-live="polite" aria-atomic="true">
      {documentType ? <span className="elf-cmp-status__type">{documentType}</span> : null}
      {statusLabel ? (
        <span className="elf-cmp-status__badge" data-doc-status={status ?? 'unknown'}>
          {statusIcon ? <span aria-hidden="true">{statusIcon} </span> : null}
          {statusLabel}
        </span>
      ) : null}
      {statusHint ? <span className="elf-cmp-status__hint">{statusHint}</span> : null}
      {autosave?.status === 'saving' ? (
        <span className="elf-cmp-status__save is-saving">Enregistrement…</span>
      ) : null}
      {autosave?.status === 'saved' ? (
        <span className="elf-cmp-status__save is-saved">
          Sauvegardé — {formatSavedAgo(autosave.savedAt)}
        </span>
      ) : null}
      {autosave?.status === 'error' ? (
        <span className="elf-cmp-status__save is-error">
          Erreur{autosave.message ? ` — ${autosave.message}` : ''}
          {autosave.onRetry ? (
            <button type="button" className="elf-cmp-status__retry" onClick={autosave.onRetry}>
              Nouvelle tentative
            </button>
          ) : null}
        </span>
      ) : null}
    </div>
  )
}

export function ComposerProgress({
  steps,
  currentStepId,
  stepStatuses,
  progressPercent,
  onSelectStep,
}: {
  steps: readonly ComposerStepDefinition[]
  currentStepId: string
  stepStatuses?: Partial<Record<string, ComposerStepStatus>>
  progressPercent?: number
  /** Étapes completed cliquables ; blocked/upcoming ignorées V1 */
  onSelectStep?: (stepId: string) => void
}) {
  const currentIndex = Math.max(
    0,
    steps.findIndex((s) => s.id === currentStepId),
  )
  const pct =
    progressPercent ??
    (steps.length <= 1 ? 100 : Math.round((currentIndex / (steps.length - 1)) * 100))

  return (
    <nav
      className="elf-cmp-progress"
      role="navigation"
      aria-label={`Progression : étape ${currentIndex + 1} sur ${steps.length}`}
    >
      <div
        className="elf-cmp-progress__track"
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Avancement ${pct} %`}
      >
        <div className="elf-cmp-progress__fill" style={{ width: `${pct}%` }} />
      </div>
      <ol className="elf-cmp-progress__steps">
        {steps.map((step) => {
          const status = stepStatuses?.[step.id] ?? 'upcoming'
          const isCurrent = step.id === currentStepId
          const canJump = status === 'completed' && Boolean(onSelectStep)
          return (
            <li
              key={step.id}
              className={cx(
                'elf-cmp-progress__item',
                `elf-cmp-progress__item--${status}`,
                isCurrent && 'is-current',
              )}
              data-step-status={status}
              data-step-id={step.id}
            >
              <button
                type="button"
                className={cx(
                  'elf-cmp-progress__dot',
                  `elf-cmp-progress__dot--${status}`,
                  canJump && 'is-clickable',
                )}
                title={step.label}
                aria-label={step.label}
                aria-current={isCurrent ? 'step' : undefined}
                disabled={!canJump && !isCurrent}
                onClick={() => {
                  if (canJump) onSelectStep?.(step.id)
                }}
              >
                <span className="elf-cmp-progress__label">{step.label}</span>
              </button>
            </li>
          )
        })}
      </ol>
    </nav>
  )
}

export function ComposerSidebar({
  definition,
  onSelectStep,
}: {
  definition: ComposerDefinition
  onSelectStep?: (stepId: string) => void
}) {
  const visible = definition.steps.filter((s) => !s.hidden)
  return (
    <nav className="elf-cmp-sidebar" aria-label="Étapes du document">
      <ol className="elf-cmp-sidebar__list">
        {visible.map((step, index) => {
          const status =
            definition.stepStatuses?.[step.id] ??
            (step.id === definition.currentStepId ? 'current' : 'upcoming')
          const isCurrent = step.id === definition.currentStepId
          const blocked = status === 'blocked'
          return (
            <li key={step.id}>
              <button
                type="button"
                className={cx(
                  'elf-cmp-sidebar__item',
                  `elf-cmp-sidebar__item--${status}`,
                  isCurrent && 'is-current',
                )}
                aria-current={isCurrent ? 'step' : undefined}
                disabled={blocked || (status === 'upcoming' && !onSelectStep)}
                onClick={() => onSelectStep?.(step.id)}
              >
                <span className="elf-cmp-sidebar__index" aria-hidden="true">
                  {status === 'completed' ? '✓' : status === 'error' ? '!' : index + 1}
                </span>
                <span className="elf-cmp-sidebar__text">
                  <span className="elf-cmp-sidebar__label">{step.label}</span>
                  {step.description ? (
                    <span className="elf-cmp-sidebar__desc">{step.description}</span>
                  ) : null}
                  <span className="elf-cmp-sidebar__status">{stepStatusLabel(status)}</span>
                </span>
              </button>
            </li>
          )
        })}
      </ol>
    </nav>
  )
}

export function ComposerHeader({
  definition,
  showProgress = true,
  primaryActions,
  secondaryActions,
  extra,
}: {
  definition: ComposerDefinition
  showProgress?: boolean
  primaryActions?: ComposerActionDef[]
  secondaryActions?: ComposerActionDef[]
  extra?: ReactNode
}) {
  const visibleSteps = definition.steps.filter((s) => !s.hidden)
  return (
    <header className="elf-cmp-header">
      <div className="elf-cmp-header__main">
        <div className="elf-cmp-header__intro">
          <h1 className="elf-cmp-header__title">{definition.title}</h1>
          <ComposerStatus
            autosave={definition.autosave}
            statusLabel={definition.statusLabel}
            documentType={definition.documentType}
            status={definition.status}
            statusHint={definition.statusHint}
            statusIcon={definition.statusIcon}
          />
          {definition.description ? (
            <p className="elf-cmp-header__desc">{definition.description}</p>
          ) : null}
        </div>
        <div className="elf-cmp-header__actions">
          {secondaryActions?.length ? <ComposerActions actions={secondaryActions} /> : null}
          {primaryActions?.length ? <ComposerActions actions={primaryActions.slice(0, 2)} /> : null}
        </div>
      </div>
      {showProgress ? (
        <ComposerProgress
          steps={visibleSteps}
          currentStepId={definition.currentStepId}
          stepStatuses={definition.stepStatuses}
          progressPercent={definition.progressPercent}
        />
      ) : null}
      {extra}
    </header>
  )
}

export function ComposerToolbar({ children }: { children?: ReactNode }) {
  if (!children) return null
  return (
    <div className="elf-cmp-toolbar" role="toolbar" aria-label="Outils document">
      {children}
    </div>
  )
}

export function ComposerBody({ children }: { children?: ReactNode }) {
  return <div className="elf-cmp-body">{children}</div>
}

export function ComposerInspector({
  title = 'Propriétés',
  children,
}: {
  title?: string
  children?: ReactNode
}) {
  return (
    <aside className="elf-cmp-inspector" aria-label={title}>
      <h2 className="elf-cmp-inspector__title">{title}</h2>
      <div className="elf-cmp-inspector__body">{children}</div>
    </aside>
  )
}

export function ComposerPreview({
  state = 'empty',
  title = 'Aperçu',
  errorMessage,
  onRetry,
  onDownload,
  zoomLabel,
  children,
  toolbar,
  zoomPercent = 100,
  onZoomIn,
  onZoomOut,
  onZoomReset,
  onFitWidth,
  fitWidth,
  onToggleFullscreen,
  fullscreen,
  page,
  pageCount,
  onPageChange,
  className,
}: {
  state?: ComposerPreviewState
  title?: string
  errorMessage?: string
  onRetry?: () => void
  onDownload?: () => void
  zoomLabel?: string
  children?: ReactNode
  toolbar?: ReactNode
  zoomPercent?: number
  onZoomIn?: () => void
  onZoomOut?: () => void
  onZoomReset?: () => void
  onFitWidth?: () => void
  fitWidth?: boolean
  onToggleFullscreen?: () => void
  fullscreen?: boolean
  page?: number
  pageCount?: number
  onPageChange?: (page: number) => void
  className?: string
}) {
  const showPdfTools = Boolean(
    onZoomIn || onZoomOut || onFitWidth || onToggleFullscreen || onPageChange,
  )
  return (
    <aside
      className={cx('elf-cmp-preview', fullscreen && 'is-fullscreen', className)}
      aria-label={title}
      data-preview-state={state}
    >
      <div className="elf-cmp-preview__bar">
        <h2 className="elf-cmp-preview__title">{title}</h2>
        <div className="elf-cmp-preview__tools">
          {zoomLabel || showPdfTools ? (
            <span className="elf-cmp-preview__zoom" aria-live="polite">
              {zoomLabel ?? `${zoomPercent} %`}
            </span>
          ) : null}
          {showPdfTools ? (
            <div className="ld-preview-toolbar" role="group" aria-label="Contrôles aperçu">
              {onZoomOut ? (
                <button type="button" className="elf-cmp-action elf-cmp-action--ghost" onClick={onZoomOut}>
                  −
                </button>
              ) : null}
              {onZoomIn ? (
                <button type="button" className="elf-cmp-action elf-cmp-action--ghost" onClick={onZoomIn}>
                  +
                </button>
              ) : null}
              {onZoomReset ? (
                <button type="button" className="elf-cmp-action elf-cmp-action--ghost" onClick={onZoomReset}>
                  100 %
                </button>
              ) : null}
              {onFitWidth ? (
                <button
                  type="button"
                  className="elf-cmp-action elf-cmp-action--ghost"
                  aria-pressed={fitWidth || undefined}
                  onClick={onFitWidth}
                >
                  Largeur
                </button>
              ) : null}
              {onPageChange ? (
                <label className="ld-preview-page">
                  Page
                  <input
                    type="number"
                    min={1}
                    max={pageCount ?? 99}
                    value={page ?? 1}
                    aria-label="Numéro de page PDF"
                    onChange={(e) => onPageChange(Math.max(1, Number(e.target.value) || 1))}
                  />
                  {pageCount != null ? <span>/ {pageCount}</span> : null}
                </label>
              ) : null}
              {onToggleFullscreen ? (
                <button
                  type="button"
                  className="elf-cmp-action elf-cmp-action--ghost"
                  aria-pressed={fullscreen || undefined}
                  onClick={onToggleFullscreen}
                >
                  {fullscreen ? 'Quitter plein écran' : 'Plein écran'}
                </button>
              ) : null}
            </div>
          ) : null}
          {toolbar}
          {onDownload ? (
            <button type="button" className="elf-cmp-action elf-cmp-action--ghost" onClick={onDownload}>
              Télécharger
            </button>
          ) : null}
        </div>
      </div>
      <div className="elf-cmp-preview__frame">
        {state === 'loading' ? (
          <div className="elf-cmp-preview__state" role="status">
            Chargement de l’aperçu…
          </div>
        ) : null}
        {state === 'error' ? (
          <div className="elf-cmp-preview__state elf-cmp-preview__state--error" role="alert">
            <p>{errorMessage || 'Aperçu indisponible'}</p>
            {onRetry ? (
              <button type="button" className="elf-cmp-action elf-cmp-action--secondary" onClick={onRetry}>
                Réessayer
              </button>
            ) : null}
          </div>
        ) : null}
        {state === 'empty' && !children ? (
          <div className="elf-cmp-preview__state" role="status">
            Enregistrez un brouillon pour afficher le PDF officiel, ou consultez l’aperçu structuré.
          </div>
        ) : null}
        {children}
      </div>
    </aside>
  )
}

export function ComposerFooter({ children }: { children?: ReactNode }) {
  return <footer className="elf-cmp-footer">{children}</footer>
}

export function ComposerActions({ actions }: { actions: ComposerActionDef[] }) {
  if (!actions.length) return null
  return (
    <div className="elf-cmp-actions" role="group" aria-label="Actions">
      {actions.map((action) => {
        const className = cx(
          'elf-cmp-action',
          `elf-cmp-action--${action.tone ?? 'secondary'}`,
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

export function ComposerNavigation({
  navigation,
  extraActions,
}: {
  navigation?: ComposerNavigationHandlers
  extraActions?: ComposerActionDef[]
}) {
  if (!navigation && !extraActions?.length) return null
  return (
    <div className="elf-cmp-nav">
      <div className="elf-cmp-nav__start">
        {navigation?.goBack ? (
          <button
            type="button"
            className="elf-cmp-action elf-cmp-action--ghost"
            onClick={navigation.goBack}
            disabled={!navigation.canGoBack}
          >
            {navigation.backLabel ?? 'Retour'}
          </button>
        ) : null}
      </div>
      <div className="elf-cmp-nav__end">
        {extraActions ? <ComposerActions actions={extraActions} /> : null}
        {navigation?.goNext ? (
          <button
            type="button"
            className="elf-cmp-action elf-cmp-action--primary"
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

export function ComposerValidation({
  issues,
  emptyMessage = 'Aucun contrôle à signaler',
}: {
  issues: ComposerValidationIssue[]
  emptyMessage?: string
}) {
  const insights = mapComposerIssuesToInsights(issues)
  return (
    <InsightList
      className="elf-cmp-validation elf-cmp-validation--insights"
      insights={insights}
      emptyMessage={emptyMessage}
      variant="inline"
    />
  )
}

export function ComposerSection({
  id,
  title,
  description,
  children,
}: {
  id: string
  title?: string
  description?: string
  children?: ReactNode
}) {
  return (
    <section
      className="elf-cmp-section"
      data-composer-section={id}
      aria-labelledby={title ? `elf-cmp-section-${id}` : undefined}
    >
      {title ? (
        <header className="elf-cmp-section__header">
          <h2 className="elf-cmp-section__title" id={`elf-cmp-section-${id}`}>
            {title}
          </h2>
          {description ? <p className="elf-cmp-section__desc">{description}</p> : null}
        </header>
      ) : null}
      <div className="elf-cmp-section__body">{children}</div>
    </section>
  )
}

export function ComposerCard({
  children,
  selected,
  onClick,
  className,
}: {
  children?: ReactNode
  selected?: boolean
  onClick?: () => void
  className?: string
}) {
  if (onClick) {
    return (
      <button
        type="button"
        className={cx('elf-cmp-card', selected && 'is-selected', className)}
        onClick={onClick}
        aria-pressed={selected}
      >
        {children}
      </button>
    )
  }
  return <div className={cx('elf-cmp-card', selected && 'is-selected', className)}>{children}</div>
}

/** Alias layout principal — ComposerLayout */
export function ComposerLayout({
  definition,
  children,
  sidebar,
  inspector,
  preview,
  footer,
  headerExtra,
  toolbar,
  className,
  focusMode = false,
  previewCollapsed = false,
  onTogglePreview,
  showSidebar = true,
  showInspector = true,
  showPreview = true,
  showProgress = true,
  primaryActions,
  secondaryActions,
  onSelectStep,
}: ComposerLayoutProps) {
  return (
    <div
      className={cx(
        'elf-cmp',
        focusMode && 'elf-cmp--focus',
        previewCollapsed && 'elf-cmp--preview-collapsed',
        className,
      )}
      data-composer-id={definition.id}
      data-composer-step={definition.currentStepId}
      data-focus-mode={focusMode ? 'true' : 'false'}
    >
      <ComposerHeader
        definition={definition}
        showProgress={showProgress}
        primaryActions={primaryActions}
        secondaryActions={secondaryActions}
        extra={headerExtra}
      />

      {toolbar ? <ComposerToolbar>{toolbar}</ComposerToolbar> : null}

      <div
        className={cx(
          'elf-cmp__layout',
          showSidebar && 'elf-cmp__layout--sidebar',
          showInspector && 'elf-cmp__layout--inspector',
          showPreview && !previewCollapsed && 'elf-cmp__layout--preview',
        )}
      >
        {showSidebar ? (
          <div className="elf-cmp__sidebar-slot">
            {sidebar ?? <ComposerSidebar definition={definition} onSelectStep={onSelectStep} />}
          </div>
        ) : null}

        <div className="elf-cmp__editor">
          <ComposerBody>{children}</ComposerBody>
          {showInspector && inspector ? (
            <div className="elf-cmp__inspector-slot">{inspector}</div>
          ) : null}
        </div>

        {showPreview ? (
          <div className={cx('elf-cmp__preview-slot', previewCollapsed && 'is-collapsed')}>
            {onTogglePreview ? (
              <button
                type="button"
                className="elf-cmp-preview-toggle"
                onClick={onTogglePreview}
                aria-expanded={!previewCollapsed}
              >
                {previewCollapsed ? 'Afficher l’aperçu' : 'Masquer l’aperçu'}
              </button>
            ) : null}
            {!previewCollapsed ? preview : null}
          </div>
        ) : null}
      </div>

      <ComposerFooter>
        {footer ?? null}
      </ComposerFooter>
    </div>
  )
}

/** Alias rétrocompat naming */
export const ComposerContainer = ComposerLayout

/**
 * Full Focus layout — plein viewport création document.
 * Réutilise ComposerHeader / Preview / Actions ; pas de second shell produit.
 */
import type { ReactNode } from 'react'
import { cx } from '../design-system'
import {
  ComposerActions,
  ComposerBody,
  ComposerFooter,
  ComposerProgress,
  ComposerStatus,
} from './ComposerContainer'
import type {
  ComposerActionDef,
  ComposerDefinition,
  ComposerLayoutProps,
} from './types'
import './composer-framework.css'

export type ComposerFocusLayoutProps = {
  definition: ComposerDefinition
  children?: ReactNode
  preview?: ReactNode
  footer?: ReactNode
  confirmation?: ReactNode
  className?: string
  /** Retour Documents (ou autre) */
  onBack?: () => void
  backLabel?: string
  /** Résumé centre (ex. points à vérifier) */
  headerCenter?: ReactNode
  headerExtra?: ReactNode
  previewCollapsed?: boolean
  onTogglePreview?: () => void
  showProgress?: boolean
  primaryActions?: ComposerActionDef[]
  secondaryActions?: ComposerActionDef[]
  /** Jump vers une étape completed (barre progression) */
  onSelectStep?: (stepId: string) => void
}

export function ComposerFocusLayout({
  definition,
  children,
  preview,
  footer,
  confirmation,
  className,
  onBack,
  backLabel = 'Documents',
  headerCenter,
  headerExtra,
  previewCollapsed = false,
  onTogglePreview,
  showProgress = true,
  primaryActions,
  secondaryActions,
  onSelectStep,
}: ComposerFocusLayoutProps) {
  const visibleSteps = definition.steps.filter((s) => !s.hidden)
  const primary = primaryActions?.slice(0, 1) ?? []
  const secondary = secondaryActions?.slice(0, 2) ?? []

  return (
    <div
      className={cx('elf-cmp', 'elf-cmp--focus', 'elf-cmp-focus', className)}
      data-composer-id={definition.id}
      data-composer-step={definition.currentStepId}
      data-focus-mode="true"
      data-composer-full-focus="true"
      role="region"
      aria-label="Création de document"
    >
      <header className="elf-cmp-focus__header" aria-label="Barre Focus document">
        <div className="elf-cmp-focus__header-left">
          {onBack ? (
            <button
              type="button"
              className="elf-cmp-action elf-cmp-action--ghost elf-cmp-focus__back"
              onClick={onBack}
              aria-label={backLabel}
            >
              ← {backLabel}
            </button>
          ) : null}
          <div className="elf-cmp-focus__intro">
            <h1 className="elf-cmp-header__title">{definition.title}</h1>
            <ComposerStatus
              autosave={undefined}
              statusLabel={definition.statusLabel}
              documentType={definition.documentType}
              status={definition.status}
              statusHint={definition.statusHint}
              statusIcon={definition.statusIcon}
            />
          </div>
        </div>

        <div className="elf-cmp-focus__header-center" aria-live="polite">
          <ComposerStatus
            autosave={definition.autosave}
            statusLabel={undefined}
            documentType={undefined}
            status={undefined}
          />
          {headerCenter}
        </div>

        <div className="elf-cmp-focus__header-right" role="group" aria-label="Actions document">
          {secondary.length ? <ComposerActions actions={secondary} /> : null}
          {primary.length ? <ComposerActions actions={primary} /> : null}
        </div>
      </header>

      {showProgress ? (
        <ComposerProgress
          steps={visibleSteps}
          currentStepId={definition.currentStepId}
          stepStatuses={definition.stepStatuses}
          progressPercent={definition.progressPercent}
          onSelectStep={onSelectStep}
        />
      ) : null}

      {headerExtra}

      <div
        className={cx(
          'elf-cmp-focus__workspace',
          'elf-cmp__layout',
          'elf-cmp__layout--preview',
          previewCollapsed && 'elf-cmp-focus__workspace--preview-collapsed',
        )}
      >
        <div className="elf-cmp-focus__editor elf-cmp__editor">
          <ComposerBody>{children}</ComposerBody>
        </div>

        <aside
          className={cx(
            'elf-cmp-focus__preview',
            'elf-cmp__preview-slot',
            previewCollapsed && 'is-collapsed',
          )}
          aria-label="Aperçu document"
        >
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
        </aside>
      </div>

      {confirmation ? (
        <div className="elf-cmp-focus__confirmation" role="status" aria-live="polite">
          {confirmation}
        </div>
      ) : null}

      <ComposerFooter>{footer ?? null}</ComposerFooter>
    </div>
  )
}

/** Props compatibles ComposerLayout pour migration douce */
export type ComposerFocusFromLayoutProps = ComposerLayoutProps &
  Pick<ComposerFocusLayoutProps, 'onBack' | 'backLabel' | 'headerCenter' | 'confirmation'>

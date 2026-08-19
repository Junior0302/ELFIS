/**
 * ExitConfirmationDialog — sortie Composer premium (F1.3.2.1).
 */

import { useEffect, useId, useRef } from 'react'
import { Dialog } from '../../design-system/overlays'
import type { CommercialDocType } from './workflow'

export type ExitConfirmationDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  docType: CommercialDocType | null
  busy?: boolean
  saveError?: string
  onContinue: () => void
  onDiscard: () => void
  onSaveAndQuit: () => void
}

function typeTitle(docType: CommercialDocType | null): string {
  if (docType === 'devis') return 'Quitter ce devis ?'
  if (docType === 'avoir') return 'Quitter cet avoir ?'
  return 'Quitter cette facture ?'
}

export function ExitConfirmationDialog({
  open,
  onOpenChange,
  docType,
  busy = false,
  saveError = '',
  onContinue,
  onDiscard,
  onSaveAndQuit,
}: ExitConfirmationDialogProps) {
  const continueRef = useRef<HTMLButtonElement>(null)
  const titleId = useId()
  const title = typeTitle(docType)

  useEffect(() => {
    if (!open) return
    const t = window.setTimeout(() => continueRef.current?.focus(), 0)
    return () => window.clearTimeout(t)
  }, [open])

  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title={title}
      description={`Vos modifications ne sont pas enregistrées. Vous pouvez enregistrer le brouillon, continuer la création, ou quitter sans enregistrer.`}
      size="sm"
      overlayType="confirm_dialog"
      closeOnEscape
      closeOnBackdrop={false}
      dismissible={!busy}
      initialFocusRef={continueRef}
      className="fp-composer-exit-confirm fp-exit-confirm-premium"
      aria-label={title}
      footer={
        <div className="fp-exit-confirm-premium__actions">
          <button
            type="button"
            className="btn"
            disabled={busy}
            onClick={onSaveAndQuit}
          >
            {busy ? 'Enregistrement…' : 'Enregistrer brouillon et quitter'}
          </button>
          <button
            ref={continueRef}
            type="button"
            className="btn secondary"
            disabled={busy}
            onClick={onContinue}
          >
            Continuer la création
          </button>
          <button
            type="button"
            className="btn fp-exit-confirm-premium__discard"
            disabled={busy}
            onClick={onDiscard}
          >
            Quitter sans enregistrer
          </button>
          {saveError ? (
            <p className="error fp-exit-confirm-premium__error" role="alert">
              {saveError}{' '}
              <button type="button" className="btn secondary" disabled={busy} onClick={onSaveAndQuit}>
                Réessayer
              </button>
            </p>
          ) : null}
        </div>
      }
    >
      <p id={titleId} className="fp-exit-confirm-premium__hint">
        Le document restera un brouillon tant qu’il n’est pas validé.
      </p>
    </Dialog>
  )
}

/**
 * Pop-in « Nouveau document » — choix de type (STATE 1).
 * Préférer DocumentCreateFlow pour le workflow modal complet (F1.3.1.2).
 * Conservé pour tests unitaires / compat.
 */

import { useCallback, useId, useRef, useState, type KeyboardEvent, type RefObject } from 'react'
import { useNavigate } from 'react-router-dom'
import { Dialog } from '../../design-system/overlays'
import {
  DOC_TYPE_CARDS,
  type CommercialDocType,
} from './workflow'

const DOC_ICON: Record<string, string> = {
  invoice: 'F',
  quote: 'D',
  credit: 'A',
}

export type NewDocumentDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** Prefill client optionnel (query existante). */
  customerId?: number | null
  returnFocusRef?: RefObject<HTMLElement | null>
  /** Si fourni, appelé à la place de navigate (transition continue). */
  onCreateType?: (type: CommercialDocType) => void
}

export function NewDocumentDialog({
  open,
  onOpenChange,
  customerId,
  returnFocusRef,
  onCreateType,
}: NewDocumentDialogProps) {
  const navigate = useNavigate()
  const [selected, setSelected] = useState<CommercialDocType | null>(null)
  const groupId = useId()
  const engaged = selected != null

  const close = useCallback(() => {
    setSelected(null)
    onOpenChange(false)
  }, [onOpenChange])

  const create = useCallback(() => {
    if (!selected) return
    if (onCreateType) {
      onCreateType(selected)
      setSelected(null)
      return
    }
    const qs = new URLSearchParams()
    qs.set('type', selected)
    if (customerId != null && !Number.isNaN(customerId)) {
      qs.set('customer_id', String(customerId))
    }
    setSelected(null)
    onOpenChange(false)
    navigate(`/facturation/documents/new?${qs.toString()}`)
  }, [selected, customerId, navigate, onOpenChange, onCreateType])

  const onRadioKeyDown = (e: KeyboardEvent, index: number) => {
    const types = DOC_TYPE_CARDS.map((c) => c.type)
    let next = index
    if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
      e.preventDefault()
      next = (index + 1) % types.length
    } else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
      e.preventDefault()
      next = (index - 1 + types.length) % types.length
    } else if (e.key === ' ' || e.key === 'Enter') {
      e.preventDefault()
      setSelected(types[index])
      return
    } else {
      return
    }
    setSelected(types[next])
    const el = document.getElementById(`${groupId}-opt-${next}`)
    el?.focus()
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) {
          setSelected(null)
        }
        onOpenChange(next)
      }}
      title="Nouveau document"
      description="Que souhaitez-vous créer ?"
      size="sm"
      closeOnBackdrop={!engaged}
      closeOnEscape
      dismissible
      returnFocusRef={returnFocusRef}
      className="fp-new-doc-dialog"
      footer={
        <>
          <button type="button" className="btn secondary" onClick={close}>
            Annuler
          </button>
          <button type="button" className="btn" disabled={!selected} onClick={create}>
            Créer le document
          </button>
        </>
      }
    >
      <div
        className="fp-new-doc-options"
        role="radiogroup"
        aria-label="Type de document"
        aria-labelledby={undefined}
      >
        {DOC_TYPE_CARDS.map((card, index) => {
          const isSelected = selected === card.type
          return (
            <button
              key={card.type}
              id={`${groupId}-opt-${index}`}
              type="button"
              role="radio"
              aria-checked={isSelected}
              aria-label={card.name}
              className={isSelected ? 'fp-new-doc-option is-selected' : 'fp-new-doc-option'}
              onClick={() => setSelected(card.type)}
              onKeyDown={(e) => onRadioKeyDown(e, index)}
            >
              <span className="fp-new-doc-option__icon" aria-hidden="true">
                {DOC_ICON[card.icon]}
              </span>
              <span className="fp-new-doc-option__body">
                <strong className="fp-new-doc-option__name">{card.name}</strong>
                <span className="fp-new-doc-option__desc">{card.description}</span>
              </span>
            </button>
          )
        })}
      </div>
    </Dialog>
  )
}

/** Hook léger pour ouvrir le pop-in depuis Documents. */
export function useNewDocumentDialog(initialOpen = false) {
  const [open, setOpen] = useState(initialOpen)
  const triggerRef = useRef<HTMLButtonElement>(null)
  return { open, setOpen, triggerRef }
}

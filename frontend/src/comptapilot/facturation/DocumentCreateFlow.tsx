/**
 * Flux création document — state machine unique (F1.3.1.3).
 * Stages : closed → type_selection → composer → confirmation | closed
 * Même root overlay ; URL sync `/facturation/documents/new?type=` sans fermer le modal.
 */

import {
  useCallback,
  useEffect,
  useId,
  useReducer,
  useRef,
  type KeyboardEvent,
  type RefObject,
} from 'react'
import { useMatch, useNavigate, useSearchParams } from 'react-router-dom'
import { DocumentCreationModalRoot } from './ComposerDialog'
import {
  DOC_TYPE_CARDS,
  type CommercialDocType,
} from './workflow'
import {
  composerModalReducer,
  INITIAL_COMPOSER_MODAL_STATE,
  isComposerModalOpen,
  type ComposerModalStage,
} from './workflow/composerModalMachine'
import FacturationComposerPage from '../../pages/facturation/FacturationComposerPage'
import type { OverlayCloseReason } from '../../design-system/overlays/manager/types'

const DOC_ICON: Record<string, string> = {
  invoice: 'F',
  quote: 'D',
  credit: 'A',
}

function parseDocType(raw: string | null): CommercialDocType | null {
  if (raw === 'facture' || raw === 'devis' || raw === 'avoir') return raw
  return null
}

function initialStage(
  typeOpen: boolean,
  composerMatch: boolean,
  typeFromUrl: CommercialDocType | null,
): typeof INITIAL_COMPOSER_MODAL_STATE {
  if (composerMatch && typeFromUrl) {
    return {
      stage: 'composer',
      selectedType: typeFromUrl,
      blocksDismiss: false,
    }
  }
  if (composerMatch || typeOpen) {
    return {
      stage: 'type_selection',
      selectedType: null,
      blocksDismiss: false,
    }
  }
  return INITIAL_COMPOSER_MODAL_STATE
}

export type DocumentCreateCloseOptions = {
  docId?: number | null
  reopenCreate?: boolean
}

export type DocumentCreateFlowProps = {
  typeOpen: boolean
  onTypeOpenChange: (open: boolean) => void
  customerId?: number | null
  returnFocusRef?: RefObject<HTMLElement | null>
  onDocumentsRefresh?: (docId?: number | null) => void
}

export function DocumentCreateFlow({
  typeOpen,
  onTypeOpenChange,
  customerId,
  returnFocusRef,
  onDocumentsRefresh,
}: DocumentCreateFlowProps) {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const composerMatch = useMatch({ path: '/facturation/documents/new', end: true })
  const typeFromUrl = parseDocType(searchParams.get('type'))
  const groupId = useId()

  const [state, dispatch] = useReducer(
    composerModalReducer,
    undefined,
    () => initialStage(typeOpen, Boolean(composerMatch), typeFromUrl),
  )

  /** Évite flash Documents entre ENTER_COMPOSER et match URL (sans setTimeout) */
  const pendingComposerRef = useRef(false)
  const prevComposerMatchRef = useRef(Boolean(composerMatch))

  /* Deep link / URL → machine (idempotent) */
  useEffect(() => {
    const hadMatch = prevComposerMatchRef.current
    prevComposerMatchRef.current = Boolean(composerMatch)

    if (composerMatch && typeFromUrl) {
      pendingComposerRef.current = false
      if (
        state.stage !== 'composer' &&
        state.stage !== 'confirmation'
      ) {
        dispatch({ type: 'HYDRATE_COMPOSER', docType: typeFromUrl })
      } else if (state.selectedType !== typeFromUrl) {
        dispatch({ type: 'HYDRATE_COMPOSER', docType: typeFromUrl })
      }
      return
    }

    if (composerMatch && !typeFromUrl) {
      pendingComposerRef.current = false
      if (state.stage === 'closed' || state.stage === 'composer') {
        dispatch({ type: 'OPEN_TYPE_SELECTION' })
        onTypeOpenChange(true)
      }
      return
    }

    /* Back navigateur : /new → /documents */
    if (
      hadMatch &&
      !composerMatch &&
      !pendingComposerRef.current &&
      (state.stage === 'composer' || state.stage === 'confirmation')
    ) {
      dispatch({ type: 'CLOSE' })
      onTypeOpenChange(false)
    }
  }, [composerMatch, typeFromUrl]) // eslint-disable-line react-hooks/exhaustive-deps

  /* Bouton Créer / ?create=1 */
  useEffect(() => {
    if (typeOpen && state.stage === 'closed' && !composerMatch) {
      dispatch({ type: 'OPEN_TYPE_SELECTION' })
    }
  }, [typeOpen, state.stage, composerMatch])

  const closeAll = useCallback(
    (opts?: DocumentCreateCloseOptions) => {
      pendingComposerRef.current = false
      dispatch({ type: 'CLOSE' })
      onTypeOpenChange(false)
      if (opts?.reopenCreate) {
        navigate('/facturation/documents?create=1')
        onTypeOpenChange(true)
        dispatch({ type: 'OPEN_TYPE_SELECTION' })
        return
      }
      if (opts?.docId != null) {
        onDocumentsRefresh?.(opts.docId)
        navigate(`/facturation/documents?doc=${opts.docId}`)
        return
      }
      onDocumentsRefresh?.(null)
      navigate('/facturation/documents')
    },
    [navigate, onTypeOpenChange, onDocumentsRefresh],
  )

  /** Transition type → composer : stage ONLY */
  const createFromType = useCallback(() => {
    const docType = state.selectedType
    if (!docType) return
    const qs = new URLSearchParams()
    qs.set('type', docType)
    if (customerId != null && !Number.isNaN(customerId)) {
      qs.set('customer_id', String(customerId))
    }
    pendingComposerRef.current = true
    dispatch({ type: 'ENTER_COMPOSER', docType })
    onTypeOpenChange(true)
    navigate(`/facturation/documents/new?${qs.toString()}`)
  }, [state.selectedType, customerId, navigate, onTypeOpenChange])

  const onFlowOpenChange = useCallback(
    (next: boolean) => {
      if (next) return
      if (state.stage === 'composer' || state.stage === 'confirmation') return
      dispatch({ type: 'CLOSE' })
      onTypeOpenChange(false)
    },
    [state.stage, onTypeOpenChange],
  )

  const onDialogRequestClose = useCallback(
    (reason: OverlayCloseReason) => {
      if (reason === 'route_change') return

      if (state.stage === 'type_selection') {
        dispatch({ type: 'CLOSE' })
        onTypeOpenChange(false)
        if (composerMatch) navigate('/facturation/documents')
        return
      }
      if (state.stage === 'confirmation') {
        closeAll()
        return
      }
      if (!state.blocksDismiss) {
        closeAll()
      }
    },
    [state.stage, state.blocksDismiss, onTypeOpenChange, closeAll, composerMatch, navigate],
  )

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
      dispatch({ type: 'SELECT_TYPE', docType: types[index] })
      return
    } else {
      return
    }
    dispatch({ type: 'SELECT_TYPE', docType: types[next] })
    document.getElementById(`${groupId}-opt-${next}`)?.focus()
  }

  const onComposerRequestClose = useCallback(
    (opts?: DocumentCreateCloseOptions) => {
      closeAll(opts)
    },
    [closeAll],
  )

  const onDismissBlockChange = useCallback((blocked: boolean) => {
    dispatch({ type: 'SET_BLOCKS_DISMISS', blocked })
  }, [])

  const onCreationConfirmChange = useCallback((openConfirm: boolean) => {
    dispatch({
      type: openConfirm ? 'ENTER_CONFIRMATION' : 'BACK_TO_COMPOSER',
    })
  }, [])

  const open = isComposerModalOpen(state.stage)
  if (!open) return null

  const engaged = state.selectedType != null
  const showComposer =
    (state.stage === 'composer' || state.stage === 'confirmation') &&
    Boolean(state.selectedType ?? typeFromUrl)
  const composerType = state.selectedType ?? typeFromUrl

  return (
    <DocumentCreationModalRoot
      open={open}
      stage={state.stage}
      onOpenChange={onFlowOpenChange}
      onRequestClose={onDialogRequestClose}
      title={state.stage === 'type_selection' ? 'Nouveau document' : undefined}
      description={
        state.stage === 'type_selection' ? 'Que souhaitez-vous créer ?' : undefined
      }
      returnFocusRef={returnFocusRef}
      dismissible={state.stage === 'type_selection' ? true : !state.blocksDismiss}
      closeOnBackdrop={
        state.stage === 'type_selection' ? !engaged : !state.blocksDismiss
      }
      closeOnEscape={state.stage === 'type_selection' ? true : !state.blocksDismiss}
      className="fp-document-create-flow"
      footer={
        state.stage === 'type_selection' ? (
          <>
            <button
              type="button"
              className="btn secondary"
              onClick={() => {
                dispatch({ type: 'CLOSE' })
                onTypeOpenChange(false)
                if (composerMatch) navigate('/facturation/documents')
              }}
            >
              Annuler
            </button>
            <button
              type="button"
              className="btn"
              disabled={!state.selectedType}
              onClick={createFromType}
            >
              Créer le document
            </button>
          </>
        ) : null
      }
    >
      {state.stage === 'type_selection' ? (
        <div className="fp-new-doc-options" role="radiogroup" aria-label="Type de document">
          {DOC_TYPE_CARDS.map((card, index) => {
            const isSelected = state.selectedType === card.type
            return (
              <button
                key={card.type}
                id={`${groupId}-opt-${index}`}
                type="button"
                role="radio"
                aria-checked={isSelected}
                aria-label={card.name}
                className={isSelected ? 'fp-new-doc-option is-selected' : 'fp-new-doc-option'}
                onClick={() => dispatch({ type: 'SELECT_TYPE', docType: card.type })}
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
      ) : showComposer && composerType ? (
        <FacturationComposerPage
          presentation="modal"
          forcedDocType={composerType}
          onRequestClose={onComposerRequestClose}
          onDismissBlockChange={onDismissBlockChange}
          onCreationConfirmChange={onCreationConfirmChange}
        />
      ) : (
        <div className="fp-composer-dialog__bridging" aria-busy="true" aria-live="polite">
          Ouverture du document…
        </div>
      )}
    </DocumentCreationModalRoot>
  )
}

export type { ComposerModalStage }

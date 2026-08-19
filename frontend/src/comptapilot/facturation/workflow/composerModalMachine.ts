/**
 * State machine unique — workflow modal création document (F1.3.1.3).
 * Une seule source de vérité : pas de booléens concurrents incompatibles.
 */

import type { CommercialDocType } from './types'

export type ComposerModalStage =
  | 'closed'
  | 'type_selection'
  | 'composer'
  | 'confirmation'

export type ComposerModalState = {
  stage: ComposerModalStage
  selectedType: CommercialDocType | null
  /** Bloque Escape/backdrop (dirty confirm enfant) */
  blocksDismiss: boolean
}

export type ComposerModalAction =
  | { type: 'OPEN_TYPE_SELECTION' }
  | { type: 'SELECT_TYPE'; docType: CommercialDocType | null }
  | { type: 'ENTER_COMPOSER'; docType: CommercialDocType }
  | { type: 'HYDRATE_COMPOSER'; docType: CommercialDocType }
  | { type: 'ENTER_CONFIRMATION' }
  | { type: 'BACK_TO_COMPOSER' }
  | { type: 'SET_BLOCKS_DISMISS'; blocked: boolean }
  | { type: 'CLOSE' }

export const INITIAL_COMPOSER_MODAL_STATE: ComposerModalState = {
  stage: 'closed',
  selectedType: null,
  blocksDismiss: false,
}

/**
 * Transitions autorisées :
 * closed → type_selection → composer → confirmation | closed
 * confirmation → closed | composer
 * type_selection → closed
 * composer → closed
 */
export function composerModalReducer(
  state: ComposerModalState,
  action: ComposerModalAction,
): ComposerModalState {
  switch (action.type) {
    case 'OPEN_TYPE_SELECTION':
      if (state.stage === 'composer' || state.stage === 'confirmation') return state
      return {
        ...state,
        stage: 'type_selection',
        selectedType: null,
        blocksDismiss: false,
      }

    case 'SELECT_TYPE':
      if (state.stage !== 'type_selection') return state
      return { ...state, selectedType: action.docType }

    case 'ENTER_COMPOSER':
      if (state.stage !== 'type_selection' && state.stage !== 'closed') {
        /* déjà composer / confirmation : maj type seulement si besoin */
        if (state.stage === 'composer' || state.stage === 'confirmation') {
          return { ...state, selectedType: action.docType }
        }
        return state
      }
      return {
        stage: 'composer',
        selectedType: action.docType,
        blocksDismiss: false,
      }

    case 'HYDRATE_COMPOSER':
      if (
        state.stage === 'composer' &&
        state.selectedType === action.docType
      ) {
        return state
      }
      if (
        state.stage === 'confirmation' &&
        state.selectedType === action.docType
      ) {
        return state
      }
      return {
        stage: 'composer',
        selectedType: action.docType,
        blocksDismiss:
          state.stage === 'composer' || state.stage === 'confirmation'
            ? state.blocksDismiss
            : false,
      }

    case 'ENTER_CONFIRMATION':
      if (state.stage !== 'composer') return state
      return { ...state, stage: 'confirmation', blocksDismiss: false }

    case 'BACK_TO_COMPOSER':
      if (state.stage !== 'confirmation') return state
      return { ...state, stage: 'composer' }

    case 'SET_BLOCKS_DISMISS':
      if (state.stage !== 'composer' && state.stage !== 'confirmation') return state
      if (state.blocksDismiss === action.blocked) return state
      return { ...state, blocksDismiss: action.blocked }

    case 'CLOSE':
      return { ...INITIAL_COMPOSER_MODAL_STATE }

    default:
      return state
  }
}

export function isComposerModalOpen(stage: ComposerModalStage): boolean {
  return stage !== 'closed'
}

export function composerDialogPhase(
  stage: ComposerModalStage,
): 'type' | 'composer' | null {
  if (stage === 'type_selection') return 'type'
  if (stage === 'composer' || stage === 'confirmation') return 'composer'
  return null
}

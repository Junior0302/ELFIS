/**
 * Unit tests — composerModalMachine (F1.3.1.3)
 */
import { describe, expect, it } from 'vitest'
import {
  composerModalReducer,
  INITIAL_COMPOSER_MODAL_STATE,
  isComposerModalOpen,
  composerDialogPhase,
} from './composerModalMachine'

describe('composerModalMachine', () => {
  it('closed → type_selection', () => {
    const next = composerModalReducer(INITIAL_COMPOSER_MODAL_STATE, {
      type: 'OPEN_TYPE_SELECTION',
    })
    expect(next.stage).toBe('type_selection')
    expect(isComposerModalOpen(next.stage)).toBe(true)
    expect(composerDialogPhase(next.stage)).toBe('type')
  })

  it('type_selection → composer conserve le type', () => {
    let s = composerModalReducer(INITIAL_COMPOSER_MODAL_STATE, {
      type: 'OPEN_TYPE_SELECTION',
    })
    s = composerModalReducer(s, { type: 'SELECT_TYPE', docType: 'facture' })
    s = composerModalReducer(s, { type: 'ENTER_COMPOSER', docType: 'facture' })
    expect(s.stage).toBe('composer')
    expect(s.selectedType).toBe('facture')
    expect(composerDialogPhase(s.stage)).toBe('composer')
  })

  it('composer → confirmation → composer | closed', () => {
    let s = composerModalReducer(INITIAL_COMPOSER_MODAL_STATE, {
      type: 'HYDRATE_COMPOSER',
      docType: 'devis',
    })
    s = composerModalReducer(s, { type: 'ENTER_CONFIRMATION' })
    expect(s.stage).toBe('confirmation')
    s = composerModalReducer(s, { type: 'BACK_TO_COMPOSER' })
    expect(s.stage).toBe('composer')
    s = composerModalReducer(s, { type: 'ENTER_CONFIRMATION' })
    s = composerModalReducer(s, { type: 'CLOSE' })
    expect(s).toEqual(INITIAL_COMPOSER_MODAL_STATE)
  })

  it('n’ouvre pas type_selection depuis composer', () => {
    const s = composerModalReducer(
      { stage: 'composer', selectedType: 'avoir', blocksDismiss: false },
      { type: 'OPEN_TYPE_SELECTION' },
    )
    expect(s.stage).toBe('composer')
  })
})

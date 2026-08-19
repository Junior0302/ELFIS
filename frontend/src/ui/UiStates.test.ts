import { describe, expect, it } from 'vitest'
import { EmptyState, ErrorState, ProgressBar, UiBadge } from './UiStates'

describe('UI states Phase 1', () => {
  it('exporte les primitives UX', () => {
    expect(EmptyState).toBeTypeOf('function')
    expect(ErrorState).toBeTypeOf('function')
    expect(ProgressBar).toBeTypeOf('function')
    expect(UiBadge).toBeTypeOf('function')
  })
})

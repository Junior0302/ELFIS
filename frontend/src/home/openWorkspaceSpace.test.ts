/**
 * @vitest-environment node
 */
import { describe, expect, it, vi } from 'vitest'
import { openWorkspaceSpace } from './openWorkspaceSpace'
import * as lastProduct from './lastProduct'

describe('openWorkspaceSpace', () => {
  it('navigue et mémorise Finance / Commercial comme le launcher', () => {
    const navigate = vi.fn()
    const spy = vi.spyOn(lastProduct, 'setLastProductId')

    openWorkspaceSpace(navigate, { route: '/dashboard', engineProductId: 'comptapilot' })
    expect(spy).toHaveBeenCalledWith('comptapilot')
    expect(navigate).toHaveBeenCalledWith('/dashboard')

    openWorkspaceSpace(navigate, { route: '/sales', engineProductId: 'salespilot' })
    expect(spy).toHaveBeenCalledWith('salespilot')

    spy.mockClear()
    openWorkspaceSpace(navigate, { route: '/platform/documents', engineProductId: 'docpilot' })
    expect(spy).not.toHaveBeenCalled()
    expect(navigate).toHaveBeenCalledWith('/platform/documents')

    spy.mockRestore()
  })
})

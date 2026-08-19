/**
 * Unit tests — Overlay Manager (pure, node environment)
 */
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import {
  createOverlayManager,
  resolvePriority,
  computeOverlayZIndex,
  assertSafeEventDetail,
  type OverlayDescriptor,
  type OverlayCloseReason,
} from './design-system'
import { sortStack } from './design-system/overlays/manager/overlayStack'

function makeInput(
  id: string,
  type: OverlayDescriptor['type'],
  extras: Partial<{
    modal: boolean
    dismissible: boolean
    parentOverlayId: string
    lockScroll: boolean
    onRequestClose: (r: OverlayCloseReason) => void
    openedAt: number
  }> = {},
) {
  return {
    id,
    type,
    modal: extras.modal,
    dismissible: extras.dismissible,
    parentOverlayId: extras.parentOverlayId,
    lockScroll: extras.lockScroll,
    onRequestClose: extras.onRequestClose ?? vi.fn(),
  }
}

describe('Overlay Manager — priorities', () => {
  it('mappe les types vers les priorités', () => {
    expect(resolvePriority('tooltip')).toBe('passive')
    expect(resolvePriority('popover')).toBe('floating')
    expect(resolvePriority('drawer', { modal: false })).toBe('panel')
    expect(resolvePriority('drawer', { modal: true })).toBe('modal')
    expect(resolvePriority('dialog')).toBe('modal')
    expect(resolvePriority('confirm_dialog')).toBe('modal')
    expect(resolvePriority('critical_dialog')).toBe('critical')
  })

  it('dérive un z-index déterministe', () => {
    expect(computeOverlayZIndex('modal', 0)).toBeLessThan(computeOverlayZIndex('critical', 0))
    expect(computeOverlayZIndex('modal', 2)).toBe(computeOverlayZIndex('modal', 0) + 2)
  })
})

describe('Overlay Manager — stack', () => {
  let mgr: ReturnType<typeof createOverlayManager>
  let clock: number

  beforeEach(() => {
    clock = 1000
    mgr = createOverlayManager({ emitEvents: false, now: () => ++clock })
  })

  afterEach(() => {
    mgr.dispose()
  })

  it('register / unregister / IDs uniques', () => {
    mgr.registerOverlay(makeInput('a', 'dialog'))
    mgr.registerOverlay(makeInput('a', 'dialog'))
    expect(mgr.getStackDepth()).toBe(1)
    mgr.unregisterOverlay('a')
    expect(mgr.getStackDepth()).toBe(0)
  })

  it('ordonne par priorité puis date', () => {
    mgr.registerOverlay(makeInput('tip', 'tooltip'))
    mgr.registerOverlay(makeInput('dlg', 'dialog'))
    mgr.registerOverlay(makeInput('crit', 'critical_dialog'))
    const ids = mgr.getStack().map((d) => d.id)
    expect(ids).toEqual(['tip', 'dlg', 'crit'])
    expect(mgr.getTopOverlay()?.id).toBe('crit')
    expect(mgr.isTopOverlay('crit')).toBe(true)
    expect(mgr.isTopOverlay('dlg')).toBe(false)
  })

  it('à priorité égale, le plus récent est top', () => {
    mgr.registerOverlay(makeInput('d1', 'dialog'))
    mgr.registerOverlay(makeInput('d2', 'dialog'))
    expect(mgr.getTopOverlay()?.id).toBe('d2')
  })

  it('Popover enfant au-dessus du parent Dialog', () => {
    mgr.registerOverlay(makeInput('dlg', 'dialog'))
    mgr.registerOverlay(makeInput('pop', 'popover', { parentOverlayId: 'dlg', modal: false }))
    const ids = mgr.getStack().map((d) => d.id)
    expect(ids.indexOf('pop')).toBeGreaterThan(ids.indexOf('dlg'))
    expect(mgr.getTopOverlay()?.id).toBe('pop')
  })

  it('Tooltip reste sous Dialog', () => {
    mgr.registerOverlay(makeInput('tip', 'tooltip'))
    mgr.registerOverlay(makeInput('dlg', 'dialog'))
    expect(mgr.getTopOverlay()?.id).toBe('dlg')
  })

  it('closeTop / closeAll ordre inverse', () => {
    const closes: string[] = []
    mgr.registerOverlay(
      makeInput('a', 'dialog', {
        onRequestClose: () => closes.push('a'),
      }),
    )
    mgr.registerOverlay(
      makeInput('b', 'dialog', {
        onRequestClose: () => closes.push('b'),
      }),
    )
    mgr.closeTop('programmatic')
    expect(closes).toEqual(['b'])
    mgr.registerOverlay(
      makeInput('c', 'dialog', {
        onRequestClose: () => closes.push('c'),
      }),
    )
    mgr.closeAll('logout')
    expect(closes.at(-1)).toBe('a')
    expect(closes).toContain('c')
    expect(mgr.getStackDepth()).toBe(0)
  })

  it('non dismissible ignore Escape', () => {
    const onClose = vi.fn()
    mgr.registerOverlay(
      makeInput('x', 'critical_dialog', { dismissible: false, onRequestClose: onClose }),
    )
    expect(mgr.closeTop('escape')).toBe(false)
    expect(onClose).not.toHaveBeenCalled()
    expect(mgr.closeAll('logout')).toBeUndefined()
    expect(onClose).toHaveBeenCalled()
  })

  it('fermeture parent nettoie enfants — pas d’orphelin', () => {
    const closed: string[] = []
    mgr.registerOverlay(
      makeInput('dlg', 'dialog', { onRequestClose: () => closed.push('dlg') }),
    )
    mgr.registerOverlay(
      makeInput('pop', 'popover', {
        parentOverlayId: 'dlg',
        modal: false,
        onRequestClose: () => closed.push('pop'),
      }),
    )
    mgr.requestClose('dlg', 'action')
    expect(closed[0]).toBe('pop')
    expect(closed).toContain('dlg')
  })

  it('scroll lock count avec deux modales', () => {
    mgr.registerOverlay(makeInput('a', 'dialog', { lockScroll: true }))
    mgr.registerOverlay(makeInput('b', 'dialog', { lockScroll: true }))
    expect(mgr.getModalLockCount()).toBe(2)
    mgr.requestClose('b', 'action')
    mgr.unregisterOverlay('b')
    expect(mgr.getModalLockCount()).toBe(1)
    mgr.unregisterOverlay('a')
    expect(mgr.getModalLockCount()).toBe(0)
  })

  it('closeAll reasons logout / org / product / route', () => {
    const reasons: OverlayCloseReason[] = []
    mgr.registerOverlay(
      makeInput('a', 'dialog', {
        onRequestClose: (r) => reasons.push(r),
      }),
    )
    mgr.closeAll('organization_change')
    expect(reasons).toEqual(['organization_change'])
    mgr.registerOverlay(makeInput('b', 'dialog', { onRequestClose: (r) => reasons.push(r) }))
    mgr.closeAll('product_change')
    expect(reasons.at(-1)).toBe('product_change')
  })

  it('fonctionne sans document (SSR)', () => {
    const m = createOverlayManager({ emitEvents: false })
    m.registerOverlay(makeInput('ssr', 'dialog'))
    expect(m.getStackDepth()).toBe(1)
    m.closeAll('provider_unmount')
    m.dispose()
  })

  it('sortStack pur', () => {
    const stack = sortStack([
      {
        id: 't',
        type: 'tooltip',
        priority: 'passive',
        modal: false,
        dismissible: true,
        closeOnEscape: true,
        closeOnBackdrop: false,
        closeOnRouteChange: true,
        openedAt: 1,
        onRequestClose: () => undefined,
        restoreFocus: false,
        lockScroll: false,
        status: 'open',
      },
      {
        id: 'd',
        type: 'dialog',
        priority: 'modal',
        modal: true,
        dismissible: true,
        closeOnEscape: true,
        closeOnBackdrop: true,
        closeOnRouteChange: true,
        openedAt: 2,
        onRequestClose: () => undefined,
        restoreFocus: true,
        lockScroll: true,
        status: 'open',
      },
    ])
    expect(stack.map((s) => s.id)).toEqual(['t', 'd'])
  })
})

describe('Overlay Manager — event payload safety', () => {
  it('assertSafeEventDetail refuse les clés hors contrat', () => {
    expect(
      assertSafeEventDetail({
        overlayId: 'a',
        overlayType: 'dialog',
        priority: 'modal',
        stackDepth: 1,
      }),
    ).toBe(true)
    expect(
      assertSafeEventDetail({
        overlayId: 'a',
        overlayType: 'dialog',
        priority: 'modal',
        stackDepth: 1,
        title: 'secret',
      } as never),
    ).toBe(false)
  })
})

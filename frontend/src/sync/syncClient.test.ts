import { describe, expect, it, vi } from 'vitest'
import { SyncClient } from './syncClient'

describe('SyncClient', () => {
  it('émet vers les abonnés après refresh', async () => {
    const client = new SyncClient()
    const tick = vi.fn().mockResolvedValue(undefined)
    const listener = vi.fn()
    client.subscribe('notifications', listener)
    const channels = (
      client as unknown as {
        channels: Map<string, { tick: unknown; timer: number | null }>
      }
    ).channels
    const state = channels.get('notifications')
    if (state) {
      state.tick = tick
      state.timer = null
    }
    await client.refreshNow('notifications')
    expect(tick).toHaveBeenCalled()
    expect(listener).toHaveBeenCalledWith('notifications', undefined)
    client.dispose()
  })

  it('mode initial polling (pas de SSE backend)', () => {
    const client = new SyncClient()
    expect(client.getMode()).toBe('polling')
    client.dispose()
  })
})

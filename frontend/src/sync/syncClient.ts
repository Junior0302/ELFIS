/** Couche Sync Phase 1 — SSE si disponible, sinon polling intelligent. */

export type SyncChannel =
  | 'notifications'
  | 'migration'
  | 'documents'
  | 'proposals'
  | 'jobs'

export type SyncListener = (channel: SyncChannel, payload?: unknown) => void

type TickFn = () => Promise<void> | void

type ChannelState = {
  intervalMs: number
  minIntervalMs: number
  maxIntervalMs: number
  timer: number | null
  tick: TickFn | null
  lastOk: boolean
  listeners: Set<SyncListener>
}

function makeChannel(intervalMs: number): ChannelState {
  return {
    intervalMs,
    minIntervalMs: Math.max(5_000, Math.floor(intervalMs / 2)),
    maxIntervalMs: Math.min(120_000, intervalMs * 4),
    timer: null,
    tick: null,
    lastOk: true,
    listeners: new Set(),
  }
}

/**
 * Pas d’endpoint SSE backend aujourd’hui → polling adaptatif.
 * Si `VITE_SSE_URL` est défini, tente EventSource puis bascule en polling à l’erreur.
 */
export class SyncClient {
  private channels = new Map<SyncChannel, ChannelState>()
  private sse: EventSource | null = null
  private mode: 'sse' | 'polling' = 'polling'

  constructor() {
    this.channels.set('notifications', makeChannel(30_000))
    this.channels.set('migration', makeChannel(15_000))
    this.channels.set('documents', makeChannel(45_000))
    this.channels.set('proposals', makeChannel(45_000))
    this.channels.set('jobs', makeChannel(20_000))
  }

  getMode() {
    return this.mode
  }

  subscribe(channel: SyncChannel, listener: SyncListener): () => void {
    const state = this.channels.get(channel)
    if (!state) return () => undefined
    state.listeners.add(listener)
    return () => state.listeners.delete(listener)
  }

  register(channel: SyncChannel, tick: TickFn) {
    const state = this.channels.get(channel)
    if (!state) return
    state.tick = tick
    this.ensurePolling(channel)
    this.trySse()
  }

  unregister(channel: SyncChannel) {
    const state = this.channels.get(channel)
    if (!state) return
    state.tick = null
    if (state.timer != null) {
      window.clearTimeout(state.timer)
      state.timer = null
    }
  }

  emit(channel: SyncChannel, payload?: unknown) {
    const state = this.channels.get(channel)
    if (!state) return
    state.listeners.forEach((l) => l(channel, payload))
  }

  async refreshNow(channel: SyncChannel) {
    const state = this.channels.get(channel)
    if (!state?.tick) return
    try {
      await state.tick()
      state.lastOk = true
      state.intervalMs = Math.max(state.minIntervalMs, Math.floor(state.intervalMs * 0.9))
      this.emit(channel)
    } catch {
      state.lastOk = false
      state.intervalMs = Math.min(state.maxIntervalMs, Math.floor(state.intervalMs * 1.5))
    }
  }

  private ensurePolling(channel: SyncChannel) {
    const state = this.channels.get(channel)
    if (!state || state.timer != null) return
    if (typeof window === 'undefined') return
    const loop = async () => {
      if (state.tick) {
        try {
          await state.tick()
          state.lastOk = true
          state.intervalMs = Math.max(
            state.minIntervalMs,
            Math.floor(state.intervalMs * 0.95),
          )
          this.emit(channel)
        } catch {
          state.lastOk = false
          state.intervalMs = Math.min(
            state.maxIntervalMs,
            Math.floor(state.intervalMs * 1.4),
          )
        }
      }
      state.timer = window.setTimeout(() => void loop(), state.intervalMs)
    }
    state.timer = window.setTimeout(() => void loop(), state.intervalMs)
  }

  private trySse() {
    const url = (import.meta.env.VITE_SSE_URL as string | undefined)?.trim()
    if (!url || this.sse) return
    try {
      const es = new EventSource(url, { withCredentials: true })
      this.sse = es
      this.mode = 'sse'
      es.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data) as { channel?: SyncChannel; payload?: unknown }
          if (data.channel) {
            void this.refreshNow(data.channel)
            this.emit(data.channel, data.payload)
          }
        } catch {
          /* ignore malformed */
        }
      }
      es.onerror = () => {
        es.close()
        this.sse = null
        this.mode = 'polling'
      }
    } catch {
      this.mode = 'polling'
    }
  }

  dispose() {
    this.channels.forEach((state) => {
      if (state.timer != null && typeof window !== 'undefined') window.clearTimeout(state.timer)
      state.timer = null
      state.tick = null
      state.listeners.clear()
    })
    this.sse?.close()
    this.sse = null
  }
}

export const syncClient = new SyncClient()

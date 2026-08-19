import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { api } from '../api'
import { useAuth } from '../auth'
import { syncClient, type SyncChannel } from './syncClient'

type SyncSnapshot = {
  unreadNotifications: number
  mode: 'sse' | 'polling'
  lastTickAt: Record<string, string>
}

type SyncContextValue = SyncSnapshot & {
  refresh: (channel?: SyncChannel) => Promise<void>
  subscribe: (channel: SyncChannel, fn: () => void) => () => void
}

const SyncContext = createContext<SyncContextValue | null>(null)

export function SyncProvider({ children }: { children: ReactNode }) {
  const { token, orgId } = useAuth()
  const [unreadNotifications, setUnread] = useState(0)
  const [lastTickAt, setLastTickAt] = useState<Record<string, string>>({})
  const [mode, setMode] = useState<'sse' | 'polling'>(syncClient.getMode())

  const mark = useCallback((channel: SyncChannel) => {
    setLastTickAt((prev) => ({ ...prev, [channel]: new Date().toISOString() }))
    setMode(syncClient.getMode())
  }, [])

  useEffect(() => {
    if (!token || orgId == null) {
      syncClient.unregister('notifications')
      return
    }
    syncClient.register('notifications', async () => {
      const data = await api.notificationsUnreadCount(token, orgId)
      setUnread(data.count || 0)
      mark('notifications')
    })
    void syncClient.refreshNow('notifications')
    return () => syncClient.unregister('notifications')
  }, [token, orgId, mark])

  const refresh = useCallback(async (channel?: SyncChannel) => {
    if (channel) {
      await syncClient.refreshNow(channel)
      return
    }
    await syncClient.refreshNow('notifications')
  }, [])

  const subscribe = useCallback((channel: SyncChannel, fn: () => void) => {
    return syncClient.subscribe(channel, () => fn())
  }, [])

  const value = useMemo(
    () => ({ unreadNotifications, mode, lastTickAt, refresh, subscribe }),
    [unreadNotifications, mode, lastTickAt, refresh, subscribe],
  )

  return <SyncContext.Provider value={value}>{children}</SyncContext.Provider>
}

export function useSync() {
  const ctx = useContext(SyncContext)
  if (!ctx) {
    return {
      unreadNotifications: 0,
      mode: 'polling' as const,
      lastTickAt: {},
      refresh: async () => undefined,
      subscribe: () => () => undefined,
    }
  }
  return ctx
}

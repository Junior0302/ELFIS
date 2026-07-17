import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { api, type SubscriptionInfo } from './api'
import { useAuth } from './auth'

type SubscriptionContextValue = {
  subscription: SubscriptionInfo | null
  loading: boolean
  error: string
  refresh: (opts?: { syncSessionId?: string | null }) => Promise<SubscriptionInfo | null>
  setSubscription: (value: SubscriptionInfo | null) => void
  checkoutReturnPending: boolean
  setCheckoutReturnPending: (value: boolean) => void
}

const SubscriptionContext = createContext<SubscriptionContextValue | null>(null)

export function SubscriptionProvider({ children }: { children: ReactNode }) {
  const { token, orgId } = useAuth()
  const [subscription, setSubscription] = useState<SubscriptionInfo | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [checkoutReturnPending, setCheckoutReturnPending] = useState(false)

  const refresh = useCallback(
    async (opts?: { syncSessionId?: string | null }) => {
      if (!token || !orgId) {
        setSubscription(null)
        return null
      }
      setLoading(true)
      setError('')
      try {
        let current =
          opts?.syncSessionId !== undefined
            ? await api.syncSubscription(token, orgId, opts.syncSessionId)
            : await api.currentSubscription(token, orgId)
        setSubscription(current)
        return current
      } catch (reason) {
        const message =
          reason instanceof Error ? reason.message : 'Statut d’abonnement indisponible'
        setError(message)
        try {
          const fallback = await api.currentSubscription(token, orgId)
          setSubscription(fallback)
          return fallback
        } catch {
          setSubscription(null)
          return null
        }
      } finally {
        setLoading(false)
      }
    },
    [token, orgId],
  )

  useEffect(() => {
    void refresh()
  }, [refresh])

  useEffect(() => {
    const onFocus = () => {
      void refresh()
    }
    window.addEventListener('focus', onFocus)
    return () => window.removeEventListener('focus', onFocus)
  }, [refresh])

  const value = useMemo(
    () => ({
      subscription,
      loading,
      error,
      refresh,
      setSubscription,
      checkoutReturnPending,
      setCheckoutReturnPending,
    }),
    [subscription, loading, error, refresh, checkoutReturnPending],
  )

  return <SubscriptionContext.Provider value={value}>{children}</SubscriptionContext.Provider>
}

export function useSubscription() {
  const ctx = useContext(SubscriptionContext)
  if (!ctx) {
    throw new Error('useSubscription doit être utilisé dans SubscriptionProvider')
  }
  return ctx
}

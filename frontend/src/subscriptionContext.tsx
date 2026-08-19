import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
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
  // F1.3.2.3 — loading=true dès le 1er rendu si session org connue.
  // Sinon phase=no_entitlement flash → /welcome → /home (perte de route au F5).
  const [loading, setLoading] = useState(() => Boolean(token && orgId))
  const [error, setError] = useState('')
  const [checkoutReturnPending, setCheckoutReturnPending] = useState(false)
  const subscriptionRef = useRef(subscription)
  subscriptionRef.current = subscription

  const refresh = useCallback(
    async (opts?: { syncSessionId?: string | null }) => {
      if (!token || !orgId) {
        setSubscription(null)
        setLoading(false)
        return null
      }
      // Silent refresh when we already know the subscription — avoids ProductAccessLayout
      // phase=loading remount that closed invoice email composers / wiped local drafts.
      const gateLoading = subscriptionRef.current == null
      if (gateLoading) setLoading(true)
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
          setError('')
          return fallback
        } catch {
          setSubscription(null)
          return null
        }
      } finally {
        if (gateLoading) setLoading(false)
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

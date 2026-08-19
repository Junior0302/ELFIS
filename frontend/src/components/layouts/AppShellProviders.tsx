import type { ReactNode } from 'react'
import { SubscriptionProvider } from '../../subscriptionContext'
import { SyncProvider } from '../../sync/SyncProvider'
import { ToastProvider } from '../../ui/Toast'

/**
 * Providers communs aux shells authentifiés (workspace + public produit).
 * Sprint 2.1 — extraction sans changement de comportement.
 */
export default function AppShellProviders({ children }: { children: ReactNode }) {
  return (
    <SubscriptionProvider>
      <ToastProvider>
        <SyncProvider>{children}</SyncProvider>
      </ToastProvider>
    </SubscriptionProvider>
  )
}

import AppShellProviders from './layouts/AppShellProviders'
import ProductAccessLayout from './layouts/ProductAccessLayout'

/**
 * Point d’entrée des routes authentifiées produit.
 * Sprint 2.3 : providers + garde entitlement → PublicLayout | WorkspaceLayout.
 */
export default function Layout() {
  return (
    <AppShellProviders>
      <ProductAccessLayout />
    </AppShellProviders>
  )
}

export { default as PublicLayout } from './layouts/PublicLayout'
export { default as WorkspaceLayout } from './layouts/WorkspaceLayout'
export { default as AppShellProviders } from './layouts/AppShellProviders'
export { default as ProductAccessLayout } from './layouts/ProductAccessLayout'

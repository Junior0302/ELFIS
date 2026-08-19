import { Navigate } from 'react-router-dom'

/** Ancienne route /vault → Documents ELFIS Core (Vault unique). */
export default function VaultRedirect() {
  return <Navigate to="/platform/documents" replace />
}

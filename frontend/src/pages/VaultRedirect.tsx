import { Navigate } from 'react-router-dom'

/** Ancienne route /vault → Documents. */
export default function VaultRedirect() {
  return <Navigate to="/documents" replace />
}

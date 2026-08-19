/**
 * Compat legacy `/facturation/nouveau` → modal Documents `/documents/new`.
 */
import { Navigate, useSearchParams } from 'react-router-dom'

export default function FacturationNouveauRedirect() {
  const [params] = useSearchParams()
  const qs = params.toString()
  return (
    <Navigate
      to={`/facturation/documents/new${qs ? `?${qs}` : ''}`}
      replace
    />
  )
}

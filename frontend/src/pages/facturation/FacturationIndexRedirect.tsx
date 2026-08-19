/**
 * Compatibilité `/facturation?doc=` et `?customer_id=` après introduction des espaces.
 */
import { Navigate, useSearchParams } from 'react-router-dom'
import FacturationOverviewPage from './FacturationOverviewPage'

export default function FacturationIndexRedirect() {
  const [params] = useSearchParams()
  const doc = params.get('doc')
  const customerId = params.get('customer_id')
  const source = params.get('source')

  if (doc) {
    const qs = new URLSearchParams()
    qs.set('doc', doc)
    if (source) qs.set('source', source)
    return <Navigate to={`/facturation/documents?${qs.toString()}`} replace />
  }

  if (customerId) {
    const qs = new URLSearchParams()
    qs.set('customer_id', customerId)
    if (source) qs.set('source', source)
    return <Navigate to={`/facturation/documents/new?${qs.toString()}`} replace />
  }

  return <FacturationOverviewPage />
}

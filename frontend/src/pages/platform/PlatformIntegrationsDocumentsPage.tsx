import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../auth'
import {
  deliverComptaPilotPackage,
  listProductBridges,
} from '../../services/documentProcessingApi'
import { can } from '../../types/permissions'

type PackageRow = {
  id: string
  product_key: string
  document_id: string
  document_version_id: string
  business_validation_id: string
  status: string
  organization_id: number
  created_at?: string
}

type DeliveryRow = {
  id: string
  package_id: string
  product_key: string
  bridge_key: string
  status: string
  attempt_count: number
  external_reference?: string | null
  last_error_code?: string | null
  last_error_message_sanitized?: string | null
}

function apiRoot() {
  return (import.meta.env.VITE_API_URL as string) || '/api'
}

/**
 * Packages & livraisons documentaires — aucun mapping comptable.
 */
export default function PlatformIntegrationsDocumentsPage() {
  const { token, orgId, memberships } = useAuth()
  const membership = memberships.find((m) => m.organization_id === orgId)
  const permissions = membership?.permissions || []
  const canRead = can(permissions, 'product_integrations.packages.read') || can(permissions, '*')
  const canDeliver =
    can(permissions, 'product_integrations.deliveries.create') || can(permissions, '*')
  const canRetry =
    can(permissions, 'product_integrations.deliveries.retry') || can(permissions, '*')

  const [packages, setPackages] = useState<PackageRow[]>([])
  const [deliveries, setDeliveries] = useState<DeliveryRow[]>([])
  const [bridgeMode, setBridgeMode] = useState('disabled')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    if (!token || !canRead) return
    setLoading(true)
    setError(null)
    try {
      const headers: Record<string, string> = {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      }
      if (orgId) headers['X-Organization-Id'] = String(orgId)
      const [pkgRes, delRes, bridges] = await Promise.all([
        fetch(`${apiRoot()}/product-integrations/packages?limit=50`, { headers }),
        fetch(`${apiRoot()}/product-integrations/deliveries?limit=50`, { headers }),
        listProductBridges(token, orgId),
      ])
      if (!pkgRes.ok) throw new Error(`packages HTTP ${pkgRes.status}`)
      if (!delRes.ok) throw new Error(`deliveries HTTP ${delRes.status}`)
      const pkgJson = await pkgRes.json()
      const delJson = await delRes.json()
      setPackages(pkgJson.items || [])
      setDeliveries(delJson.items || [])
      const cp = bridges.items.find((b) => b.product_key === 'comptapilot')
      setBridgeMode(String(cp?.bridge_mode || 'disabled'))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erreur')
    } finally {
      setLoading(false)
    }
  }, [token, orgId, canRead])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const liveAllowed = bridgeMode === 'live'
  const dryRun = bridgeMode === 'dry_run'

  async function queueDeliver(packageId: string) {
    if (!token || !liveAllowed) return
    try {
      await deliverComptaPilotPackage(packageId, token, orgId)
      await refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Livraison')
    }
  }

  async function retryDelivery(id: string) {
    if (!token || !canRetry) return
    const headers: Record<string, string> = {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    }
    if (orgId) headers['X-Organization-Id'] = String(orgId)
    const res = await fetch(`${apiRoot()}/product-integrations/deliveries/${id}/retry`, {
      method: 'POST',
      headers,
    })
    if (!res.ok) {
      setError(`retry HTTP ${res.status}`)
      return
    }
    await refresh()
  }

  return (
    <div className="platform-page">
      <header className="platform-page__header">
        <h1>Intégrations documents</h1>
        <p className="muted">
          Packages ELFIS → produits. Mode bridge : <strong>{bridgeMode}</strong>
          {dryRun ? ' (simulation — aucun import métier)' : null}
          {!liveAllowed ? ' — publication live désactivée' : null}.
        </p>
        <p className="muted">
          Validation documentaire ELFIS ≠ validation comptable.{' '}
          <Link to="/elfadmin/processing">Processing</Link>
        </p>
      </header>

      {!canRead ? <p className="muted">Permission product_integrations.packages.read requise.</p> : null}
      {loading ? <p className="muted">Chargement…</p> : null}
      {error ? <p role="alert">{error}</p> : null}

      <section>
        <h2>Packages</h2>
        <ul>
          {packages.length === 0 ? <li className="muted">Aucun package</li> : null}
          {packages.map((p) => (
            <li key={p.id}>
              {p.product_key} · {p.status} · doc {p.document_id.slice(0, 8)} · v{' '}
              {p.document_version_id.slice(0, 8)} · validation {p.business_validation_id.slice(0, 8)}
              {canDeliver && liveAllowed && p.status === 'ready' ? (
                <button type="button" className="platform-action" onClick={() => void queueDeliver(p.id)}>
                  Mettre en file (live)
                </button>
              ) : null}
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h2>Livraisons</h2>
        <ul>
          {deliveries.length === 0 ? <li className="muted">Aucune livraison</li> : null}
          {deliveries.map((d) => (
            <li key={d.id}>
              {d.product_key}/{d.bridge_key} · {d.status} · tentatives {d.attempt_count}
              {d.external_reference ? ` · ref ${String(d.external_reference).slice(0, 12)}…` : ''}
              {d.last_error_code ? ` · err ${d.last_error_code}` : ''}
              {d.last_error_message_sanitized ? ` — ${d.last_error_message_sanitized}` : ''}
              {canRetry && (d.status === 'failed' || d.status === 'blocked') ? (
                <button type="button" className="platform-action" onClick={() => void retryDelivery(d.id)}>
                  Retry
                </button>
              ) : null}
              {d.status === 'unknown' || d.status === 'manual_review' ? (
                <span className="muted"> · reconciliation CLI requise</span>
              ) : null}
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}

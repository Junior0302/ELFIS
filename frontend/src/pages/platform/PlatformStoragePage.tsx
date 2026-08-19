import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../../auth'
import { can } from '../../types/permissions'

type ProviderInfo = {
  configured_provider: string
  active_provider: string
  capabilities: Record<string, boolean>
  download_mode: string
  supabase_bucket_configured: boolean
  supabase_url_configured: boolean
}

type MigrationRow = {
  id: string
  storage_object_id: string
  source_provider: string
  target_provider: string
  status: string
  checksum_verified: boolean
  error_code?: string | null
}

function apiRoot(): string {
  const raw = (import.meta.env.VITE_API_URL as string | undefined)?.trim()
  if (raw) return raw.replace(/\/$/, '')
  return '/api'
}

/**
 * Vue read-only provider / migrations — pas de bouton migration globale.
 */
export default function PlatformStoragePage() {
  const { token, memberships, orgId } = useAuth()
  const membership = memberships.find((m) => m.organization_id === orgId)
  const permissions = membership?.permissions || []
  const canRead =
    can(permissions, 'storage.providers.read') ||
    can(permissions, 'storage.objects.read') ||
    can(permissions, '*')

  const [info, setInfo] = useState<ProviderInfo | null>(null)
  const [migrations, setMigrations] = useState<MigrationRow[]>([])
  const [integrity, setIntegrity] = useState<{ scanned: number; ok: number; failed: number } | null>(
    null,
  )
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!token || !canRead) return
    setError(null)
    const headers = { Authorization: `Bearer ${token}` }
    try {
      const [p, m, i] = await Promise.all([
        fetch(`${apiRoot()}/admin/storage/provider`, { headers }),
        fetch(`${apiRoot()}/admin/storage/migrations?limit=20`, { headers }),
        fetch(`${apiRoot()}/admin/storage/integrity-summary?limit=50`, { headers }),
      ])
      if (p.ok) setInfo(await p.json())
      if (m.ok) {
        const body = await m.json()
        setMigrations(body.items || [])
      }
      if (i.ok) setIntegrity(await i.json())
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erreur')
    }
  }, [token, canRead])

  useEffect(() => {
    void load()
  }, [load])

  return (
    <div className="platform-page">
      <header className="platform-page__header">
        <h1>Storage</h1>
        <p className="muted">Provider actif, migrations et intégrité — lecture seule. Pas de secrets.</p>
      </header>
      {!canRead ? <p className="muted">Permission storage.providers.read requise.</p> : null}
      {error ? <p role="alert">{error}</p> : null}
      {info ? (
        <section>
          <p>
            Provider configuré : <strong>{info.configured_provider}</strong> · actif :{' '}
            <strong>{info.active_provider}</strong> · mode download : {info.download_mode}
          </p>
          <p className="muted">
            Supabase URL configurée : {info.supabase_url_configured ? 'oui' : 'non'} · bucket :{' '}
            {info.supabase_bucket_configured ? 'oui' : 'non'}
          </p>
        </section>
      ) : null}
      {integrity ? (
        <section>
          <h2>Intégrité (aperçu)</h2>
          <p className="muted">
            scannés {integrity.scanned} · ok {integrity.ok} · échecs {integrity.failed}
          </p>
        </section>
      ) : null}
      <section>
        <h2>Migrations récentes</h2>
        <ul className="platform-simple-list">
          {migrations.length === 0 ? <li className="muted">Aucune</li> : null}
          {migrations.map((row) => (
            <li key={row.id}>
              {row.source_provider} → {row.target_provider} · {row.status}
              {row.error_code ? ` · ${row.error_code}` : ''}
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}

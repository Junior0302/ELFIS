import { useCallback, useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  api,
  type SharedRelation,
  type SharedRelationDuplicate,
  type SharedRelationRole,
} from '../../api'
import { useAuth } from '../../auth'
import '../../platform-workspace/platform-workspace.css'

type TabId = 'all' | SharedRelationRole | 'duplicates'

const TABS: { id: TabId; label: string }[] = [
  { id: 'all', label: 'Toutes' },
  { id: 'customer', label: 'Clients' },
  { id: 'supplier', label: 'Fournisseurs' },
  { id: 'prospect', label: 'Prospects' },
  { id: 'commercial_account', label: 'Comptes commerciaux' },
  { id: 'partner', label: 'Partenaires' },
  { id: 'duplicates', label: 'Doublons possibles' },
]

const ROLE_LABEL: Record<string, string> = {
  customer: 'Client',
  supplier: 'Fournisseur',
  prospect: 'Prospect',
  partner: 'Partenaire',
  commercial_account: 'Compte commercial',
  employee: 'Employé',
  billing_contact: 'Contact facturation',
}

/**
 * ELFIS Relations — lecture unifiée via contrat SharedRelation (S1.2).
 * Aucune fusion de tables ; IDs opaques source:id.
 */
export default function PlatformRelationsPage() {
  const { token, orgId } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const tab = (searchParams.get('tab') as TabId) || 'all'
  const [q, setQ] = useState(searchParams.get('q') || '')
  const [qDraft, setQDraft] = useState(q)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [items, setItems] = useState<SharedRelation[]>([])
  const [total, setTotal] = useState(0)
  const [duplicates, setDuplicates] = useState<SharedRelationDuplicate[]>([])
  const [page, setPage] = useState(1)

  const load = useCallback(() => {
    if (!token) return
    setLoading(true)
    setError('')
    if (tab === 'duplicates') {
      api
        .listSharedRelationDuplicates(token, orgId)
        .then((res) => {
          setDuplicates(res.items || [])
          setItems([])
          setTotal(res.items?.length || 0)
        })
        .catch((e) => setError(e instanceof Error ? e.message : 'Chargement impossible'))
        .finally(() => setLoading(false))
      return
    }
    const role = tab === 'all' ? undefined : tab
    api
      .listSharedRelations(token, orgId, {
        q: q || undefined,
        role,
        page,
        page_size: 50,
      })
      .then((res) => {
        setItems(res.items || [])
        setTotal(res.total || 0)
        setDuplicates([])
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Chargement impossible'))
      .finally(() => setLoading(false))
  }, [token, orgId, tab, q, page])

  useEffect(() => {
    void load()
  }, [load])

  const setTab = (next: TabId) => {
    setPage(1)
    const sp = new URLSearchParams(searchParams)
    if (next === 'all') sp.delete('tab')
    else sp.set('tab', next)
    setSearchParams(sp)
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h2>Relations</h2>
          <p>
            Identités partagées ELFIS — projection lecture. Pas de fusion automatique des sources.
          </p>
        </div>
      </div>

      <div className="platform-surface-banner">
        <strong>ELFIS Core</strong>
        <p>
          Annuaire plateforme uniquement. Les vues métier Clients restent dans Finance et
          Commercial, via Espaces.
        </p>
      </div>

      <div className="billing-tabs" role="tablist" style={{ marginBottom: '1rem', flexWrap: 'wrap' }}>
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            className={`billing-tab ${tab === t.id ? 'active' : ''}`}
            aria-selected={tab === t.id}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab !== 'duplicates' ? (
        <form
          className="panel"
          style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}
          onSubmit={(e) => {
            e.preventDefault()
            setPage(1)
            setQ(qDraft.trim())
          }}
        >
          <input
            value={qDraft}
            onChange={(e) => setQDraft(e.target.value)}
            placeholder="Rechercher une relation…"
            aria-label="Rechercher une relation"
            style={{ flex: '1 1 220px' }}
          />
          <button type="submit" className="btn">
            Rechercher
          </button>
        </form>
      ) : (
        <p className="muted">
          Alertes non destructives — aucune fusion automatique. Décision manuelle hors scope S1.2.
        </p>
      )}

      {error ? (
        <div className="panel form-error" role="alert">
          {error}
        </div>
      ) : null}

      {loading ? (
        <div className="panel">Chargement…</div>
      ) : tab === 'duplicates' ? (
        <section className="panel">
          <h3>Doublons possibles ({duplicates.length})</h3>
          {duplicates.length === 0 ? (
            <p className="muted">Aucun signal de doublon pour cette organisation.</p>
          ) : (
            <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
              {duplicates.map((d) => (
                <li
                  key={`${d.left_id}-${d.right_id}`}
                  style={{ padding: '0.75rem 0', borderBottom: '1px solid rgba(0,0,0,0.06)' }}
                >
                  <span className="platform-role-chip">confiance {(d.confidence * 100).toFixed(0)}%</span>
                  <div>
                    <Link to={`/platform/relations/${encodeURIComponent(d.left_id)}`}>{d.left_id}</Link>
                    {' ↔ '}
                    <Link to={`/platform/relations/${encodeURIComponent(d.right_id)}`}>{d.right_id}</Link>
                  </div>
                  <p className="muted" style={{ margin: '0.25rem 0 0' }}>
                    Champs : {d.matching_fields.join(', ')}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </section>
      ) : (
        <section className="panel">
          <h3>
            Relations ({total})
            {q ? <span className="muted"> · « {q} »</span> : null}
          </h3>
          {items.length === 0 ? (
            <p className="muted">Aucune relation pour ce filtre.</p>
          ) : (
            <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
              {items.map((row) => (
                <li
                  key={row.id}
                  style={{ padding: '0.75rem 0', borderBottom: '1px solid rgba(0,0,0,0.06)' }}
                >
                  <Link to={`/platform/relations/${encodeURIComponent(row.id)}`}>
                    <strong>{row.display_name}</strong>
                  </Link>
                  <span className="muted"> · {row.party_type}</span>
                  <span className="muted"> · {row.source_system}:{row.source_entity_id}</span>
                  <div>
                    {row.roles.map((r) => (
                      <span key={r} className="platform-role-chip">
                        {ROLE_LABEL[r] || r}
                      </span>
                    ))}
                    <span className="platform-role-chip">{row.status}</span>
                  </div>
                  <p className="muted" style={{ margin: '0.25rem 0 0' }}>
                    {row.emails[0] || '—'}
                    {row.phones[0] ? ` · ${row.phones[0]}` : ''}
                  </p>
                </li>
              ))}
            </ul>
          )}
          {total > 50 ? (
            <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem' }}>
              <button type="button" className="btn secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                Précédent
              </button>
              <span className="muted">Page {page}</span>
              <button
                type="button"
                className="btn secondary"
                disabled={page * 50 >= total}
                onClick={() => setPage((p) => p + 1)}
              >
                Suivant
              </button>
            </div>
          ) : null}
        </section>
      )}
    </div>
  )
}

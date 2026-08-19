import { useEffect, useState, type FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api, formatEuro } from '../api'
import { useAuth } from '../auth'

type Item = {
  search_document_id: string
  resource_type: string
  resource_id: string
  title: string
  subtitle?: string | null
  snippet: string
  status?: string | null
  category?: string | null
  document_date?: string | null
  amount?: number | null
  currency?: string | null
  action_url?: string | null
  score: number
}

const TYPE_LABEL: Record<string, string> = {
  vault_document: 'Document',
  document_analysis: 'Analyse',
  document_text_extraction: 'Extraction',
  accounting_proposal: 'Écriture',
  accounting_entry: 'Journal',
  customer: 'Client',
  supplier: 'Fournisseur',
}

export default function SearchPage() {
  const { token, orgId } = useAuth()
  const [params, setParams] = useSearchParams()
  const [q, setQ] = useState(params.get('q') || '')
  const [resourceType, setResourceType] = useState(params.get('resource_type') || '')
  const [sort, setSort] = useState(params.get('sort') || '')
  const [page, setPage] = useState(Number(params.get('page') || 1))
  const [items, setItems] = useState<Item[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const load = (query = q, p = page) => {
    if (!token) return
    setLoading(true)
    setError('')
    api
      .searchElfis(
        {
          q: query || undefined,
          resource_type: resourceType || undefined,
          sort: sort || undefined,
          page: p,
          page_size: 20,
        },
        token,
        orgId,
      )
      .then((res) => {
        setItems(res.items as Item[])
        setTotal(res.total)
      })
      .catch((e) => setError(e.message || 'Erreur de recherche'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load(params.get('q') || '', Number(params.get('page') || 1))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, orgId])

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    const next = new URLSearchParams()
    if (q.trim()) next.set('q', q.trim())
    if (resourceType) next.set('resource_type', resourceType)
    if (sort) next.set('sort', sort)
    next.set('page', '1')
    setParams(next)
    setPage(1)
    load(q.trim(), 1)
  }

  const totalPages = Math.max(1, Math.ceil(total / 20))

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <h1>Recherche ELFIS</h1>
          <p className="muted">Documents, analyses, écritures et contacts de votre organisation</p>
        </div>
      </header>

      <form className="toolbar" onSubmit={onSubmit} style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Mots-clés, fournisseur, n° facture…"
          style={{ minWidth: '220px', flex: 1 }}
        />
        <select value={resourceType} onChange={(e) => setResourceType(e.target.value)}>
          <option value="">Tous les types</option>
          {Object.entries(TYPE_LABEL).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </select>
        <select value={sort} onChange={(e) => setSort(e.target.value)}>
          <option value="">Tri auto</option>
          <option value="relevance">Pertinence</option>
          <option value="newest">Plus récent</option>
          <option value="oldest">Plus ancien</option>
          <option value="amount_high">Montant ↓</option>
          <option value="amount_low">Montant ↑</option>
        </select>
        <button type="submit" className="btn">
          Rechercher
        </button>
      </form>

      {error ? <p className="error">{error}</p> : null}
      {loading ? <p className="muted">Recherche…</p> : null}

      {!loading && !error ? (
        <p className="muted">
          {total} résultat{total > 1 ? 's' : ''}
        </p>
      ) : null}

      {!loading && items.length === 0 && !error ? (
        <p>Aucun résultat pour cette recherche.</p>
      ) : null}

      <ul className="search-results" style={{ listStyle: 'none', padding: 0, margin: 0 }}>
        {items.map((item) => (
          <li
            key={item.search_document_id}
            style={{
              padding: '1rem 0',
              borderBottom: '1px solid var(--border, #ddd)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
              <div>
                <span className="muted">{TYPE_LABEL[item.resource_type] || item.resource_type}</span>
                <h3 style={{ margin: '0.25rem 0' }}>
                  {item.action_url ? <Link to={item.action_url}>{item.title}</Link> : item.title}
                </h3>
                {item.subtitle ? <p className="muted">{item.subtitle}</p> : null}
                {item.snippet ? (
                  <p
                    className="search-snippet"
                    dangerouslySetInnerHTML={{
                      __html: item.snippet.replace(/\[\[(.+?)\]\]/g, '<mark>$1</mark>'),
                    }}
                  />
                ) : null}
              </div>
              <div style={{ textAlign: 'right' }}>
                {item.amount != null ? <strong>{formatEuro(item.amount)}</strong> : null}
                {item.status ? <div className="muted">{item.status}</div> : null}
                {item.document_date ? (
                  <div className="muted">{new Date(item.document_date).toLocaleDateString('fr-FR')}</div>
                ) : null}
              </div>
            </div>
          </li>
        ))}
      </ul>

      {totalPages > 1 ? (
        <div className="toolbar" style={{ marginTop: '1rem', gap: '0.5rem' }}>
          <button
            type="button"
            className="btn ghost"
            disabled={page <= 1}
            onClick={() => {
              const p = page - 1
              setPage(p)
              load(q, p)
            }}
          >
            Précédent
          </button>
          <span className="muted">
            Page {page} / {totalPages}
          </span>
          <button
            type="button"
            className="btn ghost"
            disabled={page >= totalPages}
            onClick={() => {
              const p = page + 1
              setPage(p)
              load(q, p)
            }}
          >
            Suivant
          </button>
        </div>
      ) : null}
    </div>
  )
}

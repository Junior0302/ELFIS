import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import WorkQueueItemCard from '../components/WorkQueueItemCard'
import { markDecisionsStale } from '../decisionCenter'
import { Badge, EmptyState, PageHeader, Section } from '../design-system'
import {
  bucketLabel,
  consumeWorkQueueStale,
  emptyCopy,
  markWorkQueueStale,
  type WorkQueueBucket,
  type WorkQueueCounts,
  type WorkQueueItem,
} from '../workQueue'
import { ErrorState, Skeleton } from '../ui/UiStates'

const BUCKETS: WorkQueueBucket[] = ['todo', 'in_progress', 'waiting', 'completed']

export default function WorkQueuePage() {
  const { token, orgId } = useAuth()
  const [params, setParams] = useSearchParams()
  const bucket = (params.get('bucket') as WorkQueueBucket) || 'todo'
  const severity = params.get('severity') || ''
  const decisionType = params.get('decision_type') || ''
  const sourceType = params.get('source_type') || ''
  const sort = params.get('sort') || 'priority'
  const search = params.get('search') || ''
  const page = Math.max(1, Number(params.get('page') || '1') || 1)

  const [items, setItems] = useState<WorkQueueItem[]>([])
  const [counts, setCounts] = useState<WorkQueueCounts>({
    todo: 0,
    in_progress: 0,
    waiting: 0,
    completed: 0,
  })
  const [totalPages, setTotalPages] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [statusMessage, setStatusMessage] = useState('')
  const [busyId, setBusyId] = useState<string | null>(null)
  const [searchDraft, setSearchDraft] = useState(search)

  const hasFilters = Boolean(severity || decisionType || sourceType || search)

  const patchParams = useCallback(
    (patch: Record<string, string | null>) => {
      const next = new URLSearchParams(params)
      Object.entries(patch).forEach(([key, value]) => {
        if (!value) next.delete(key)
        else next.set(key, value)
      })
      if (!patch.page) next.delete('page')
      setParams(next, { replace: true })
    },
    [params, setParams],
  )

  const load = useCallback(() => {
    if (!token || orgId == null) return
    setLoading(true)
    setError('')
    void api
      .getWorkQueue(token, orgId, {
        bucket,
        severity: severity || undefined,
        decision_type: decisionType || undefined,
        source_type: sourceType || undefined,
        search: search || undefined,
        sort,
        page,
        page_size: 20,
        sync: page === 1 && bucket === 'todo',
      })
      .then((res) => {
        setItems(res.items)
        setCounts(res.counts)
        setTotalPages(res.pagination.total_pages)
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Impossible de charger la boîte de travail'))
      .finally(() => setLoading(false))
  }, [token, orgId, bucket, severity, decisionType, sourceType, search, sort, page])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    const onFocus = () => {
      if (consumeWorkQueueStale()) load()
    }
    window.addEventListener('focus', onFocus)
    return () => window.removeEventListener('focus', onFocus)
  }, [load])

  useEffect(() => {
    setSearchDraft(search)
  }, [search])

  const onSearchSubmit = (e: FormEvent) => {
    e.preventDefault()
    patchParams({ search: searchDraft.trim() || null, page: null })
  }

  const resetFilters = () => {
    setParams(new URLSearchParams({ bucket }), { replace: true })
    setSearchDraft('')
  }

  const afterMutation = (message: string) => {
    setStatusMessage(message)
    markDecisionsStale()
    markWorkQueueStale()
    load()
  }

  const onStart = async (id: string) => {
    if (!token || orgId == null) return
    setBusyId(id)
    try {
      await api.startDecision(id, token, orgId)
      afterMutation('Décision commencée.')
      patchParams({ bucket: 'in_progress', page: null })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Impossible de commencer')
    } finally {
      setBusyId(null)
    }
  }

  const onDismiss = async (id: string) => {
    if (!token || orgId == null) return
    setBusyId(id)
    try {
      await api.dismissDecision(id, token, orgId)
      afterMutation('Décision ignorée.')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Impossible d’ignorer')
    } finally {
      setBusyId(null)
    }
  }

  const empty = useMemo(() => emptyCopy(bucket, hasFilters), [bucket, hasFilters])

  return (
    <>
      <PageHeader
        title="Boîte de travail"
        description="Retrouvez les éléments qui nécessitent votre attention et poursuivez leur traitement."
      >
        <p className="muted first-experience-back">
          <Link to="/dashboard">Retour au Dashboard</Link>
        </p>
      </PageHeader>

      <Section
        title="Volumes"
        description="Répartition par file"
        variant="bordered"
        spacing="compact"
        actions={<Badge tone="accent">À traiter</Badge>}
        className="panel work-queue-summary"
      >
        <ul className="work-queue-counts">
          {BUCKETS.map((b) => (
            <li key={b}>
              <button
                type="button"
                className={bucket === b ? 'is-active' : ''}
                onClick={() => patchParams({ bucket: b, page: null })}
              >
                <strong>{counts[b]}</strong>
                <span>{bucketLabel(b)}</span>
              </button>
            </li>
          ))}
        </ul>
      </Section>

      <div className="billing-tabs" role="tablist" aria-label="Files de travail">
        {BUCKETS.map((b) => (
          <button
            key={b}
            type="button"
            role="tab"
            id={`wq-tab-${b}`}
            aria-selected={bucket === b}
            aria-controls={`wq-panel-${b}`}
            className={`billing-tab${bucket === b ? ' active' : ''}`}
            onClick={() => patchParams({ bucket: b, page: null })}
          >
            {bucketLabel(b)} ({counts[b]})
          </button>
        ))}
      </div>

      <form className="work-queue-toolbar panel" onSubmit={onSearchSubmit} aria-label="Filtres">
        <label>
          Rechercher
          <input
            value={searchDraft}
            onChange={(e) => setSearchDraft(e.target.value)}
            placeholder="Titre, résumé, référence…"
            maxLength={80}
          />
        </label>
        <label>
          Sévérité
          <select value={severity} onChange={(e) => patchParams({ severity: e.target.value || null, page: null })}>
            <option value="">Toutes</option>
            <option value="critical">Critique</option>
            <option value="high">Élevée</option>
            <option value="medium">Moyenne</option>
            <option value="low">Faible</option>
            <option value="info">Info</option>
          </select>
        </label>
        <label>
          Source
          <select
            value={sourceType}
            onChange={(e) => patchParams({ source_type: e.target.value || null, page: null })}
          >
            <option value="">Toutes</option>
            <option value="accounting_proposal">Comptabilité</option>
            <option value="document_analysis">Documents</option>
          </select>
        </label>
        <label>
          Tri
          <select value={sort} onChange={(e) => patchParams({ sort: e.target.value, page: null })}>
            <option value="priority">Priorité</option>
            <option value="newest">Plus récentes</option>
            <option value="oldest">Plus anciennes</option>
            <option value="updated">Mises à jour</option>
          </select>
        </label>
        <div className="actions">
          <button type="submit" className="btn">
            Appliquer
          </button>
          {hasFilters ? (
            <button type="button" className="btn secondary" onClick={resetFilters}>
              Réinitialiser les filtres
            </button>
          ) : null}
        </div>
      </form>

      {statusMessage ? (
        <p className="panel form-ok" role="status" aria-live="polite">
          {statusMessage}
        </p>
      ) : null}

      <div
        role="tabpanel"
        id={`wq-panel-${bucket}`}
        aria-labelledby={`wq-tab-${bucket}`}
        className="work-queue-panel"
      >
        {loading && items.length === 0 ? (
          <div aria-busy="true" aria-live="polite">
            <Skeleton rows={5} />
          </div>
        ) : null}
        {error && items.length === 0 ? <ErrorState message={error} onRetry={load} /> : null}
        {!loading && !error && items.length === 0 ? (
          <EmptyState
            title={empty.title}
            description={empty.description}
            action={
              hasFilters ? (
                <button type="button" className="btn secondary" onClick={resetFilters}>
                  Réinitialiser les filtres
                </button>
              ) : undefined
            }
          />
        ) : null}
        {items.length > 0 ? (
          <div className="decision-list" role="list">
            {error ? (
              <p className="form-error" role="alert">
                {error}
              </p>
            ) : null}
            {items.map((item) => (
              <div key={item.decision_id} role="listitem">
                <WorkQueueItemCard
                  item={item}
                  busy={busyId === item.decision_id}
                  onStart={bucket === 'todo' ? onStart : undefined}
                  onDismiss={bucket !== 'completed' ? onDismiss : undefined}
                />
              </div>
            ))}
          </div>
        ) : null}

        {totalPages > 1 ? (
          <nav className="work-queue-pagination" aria-label="Pagination">
            <button
              type="button"
              className="btn secondary"
              disabled={page <= 1}
              onClick={() => patchParams({ page: String(page - 1) })}
            >
              Précédent
            </button>
            <span>
              Page {page} / {totalPages}
            </span>
            <button
              type="button"
              className="btn secondary"
              disabled={page >= totalPages}
              onClick={() => patchParams({ page: String(page + 1) })}
            >
              Suivant
            </button>
          </nav>
        ) : null}
      </div>
    </>
  )
}

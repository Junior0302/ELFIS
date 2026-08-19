/**
 * Liste CRM générique SalesPilot — tri/pagination/filtre/quick create/bulk (S1.8).
 */
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import {
  Badge,
  Button,
  Container,
  EmptyState,
  Input,
  PageHeader,
  Section,
} from '../design-system'
import { ConfirmDialog } from '../design-system/overlays'
import { QuickCreateDrawer } from './QuickCreateDrawer'
import { SavedViewsBar } from './SavedViewsBar'
import type { QuickCreateKind } from './salesOps'

type Column<T> = {
  key: string
  label: string
  render: (row: T) => ReactNode
}

type Props<T extends { id: number }> = {
  title: string
  description: string
  createKind: QuickCreateKind
  columns: Column<T>[]
  load: (
    token: string,
    orgId: number,
    page: number,
    q: string,
  ) => Promise<{ items: T[]; pagination: { page: number; total: number; page_size: number } }>
  onDelete?: (token: string, orgId: number, id: number) => Promise<void>
  bulkResource?: string
  rowHref?: (row: T) => string
  emptyTitle: string
  emptyDescription: string
}

export function CrmResourceListPage<T extends { id: number }>({
  title,
  description,
  createKind,
  columns,
  load,
  onDelete,
  bulkResource,
  rowHref,
  emptyTitle,
  emptyDescription,
}: Props<T>) {
  const { token, orgId } = useAuth()
  const [items, setItems] = useState<T[]>([])
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [q, setQ] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [createOpen, setCreateOpen] = useState(false)
  const [selected, setSelected] = useState<number[]>([])
  const [deleteId, setDeleteId] = useState<number | null>(null)
  const [bulkOpen, setBulkOpen] = useState(false)
  const [bulkMarkDoneOpen, setBulkMarkDoneOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [savedFilters, setSavedFilters] = useState<Record<string, unknown>>({})

  const refresh = useCallback(() => {
    if (!token || orgId == null) return
    setLoading(true)
    setError('')
    const searchQ =
      typeof savedFilters.q === 'string' && savedFilters.q.trim()
        ? String(savedFilters.q)
        : q
    void load(token, orgId, page, searchQ)
      .then((res) => {
        setItems(res.items)
        setTotal(res.pagination.total)
      })
      .catch((err: unknown) => {
        setError(
          err && typeof err === 'object' && 'message' in err
            ? String((err as { message: unknown }).message)
            : 'Chargement impossible',
        )
        setItems([])
      })
      .finally(() => setLoading(false))
  }, [token, orgId, page, q, load, savedFilters])

  useEffect(() => {
    refresh()
  }, [refresh])

  const pageCount = useMemo(
    () => Math.max(1, Math.ceil(total / 20)),
    [total],
  )

  const toggle = (id: number) => {
    setSelected((cur) => (cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]))
  }

  const runDelete = async () => {
    if (!token || orgId == null || deleteId == null || !onDelete) return
    setBusy(true)
    try {
      await onDelete(token, orgId, deleteId)
      setDeleteId(null)
      refresh()
    } finally {
      setBusy(false)
    }
  }

  const runBulkDelete = async () => {
    if (!token || orgId == null || !bulkResource || selected.length === 0) return
    setBusy(true)
    try {
      await api.bulkSalesAction(token, orgId, {
        resource: bulkResource,
        action: 'soft_delete',
        ids: selected,
        confirm: true,
      })
      setSelected([])
      setBulkOpen(false)
      refresh()
    } finally {
      setBusy(false)
    }
  }

  const runBulkMarkDone = async () => {
    if (!token || orgId == null || bulkResource !== 'tasks' || selected.length === 0) return
    setBusy(true)
    try {
      await api.bulkSalesAction(token, orgId, {
        resource: 'tasks',
        action: 'mark_done',
        ids: selected,
        confirm: true,
      })
      setSelected([])
      setBulkMarkDoneOpen(false)
      refresh()
    } finally {
      setBusy(false)
    }
  }

  return (
    <Container className="sales-workspace">
      <PageHeader
        eyebrow="SalesPilot"
        title={title}
        description={description}
        actions={
          <div className="sales-deal__header-actions">
            <Button type="button" variant="primary" onClick={() => setCreateOpen(true)}>
              Créer
            </Button>
          </div>
        }
      />

      <Section title="Filtres" spacing="compact">
        <div className="sales-deal__header-actions">
          <Input
            aria-label="Recherche"
            placeholder="Rechercher…"
            value={q}
            onChange={(e) => {
              setPage(1)
              setQ(e.target.value)
            }}
          />
          <Button type="button" variant="secondary" onClick={refresh}>
            Actualiser
          </Button>
          {selected.length > 0 && bulkResource ? (
            <>
              <Button type="button" variant="danger" onClick={() => setBulkOpen(true)}>
                Archiver ({selected.length})
              </Button>
              {bulkResource === 'tasks' ? (
                <Button type="button" variant="secondary" onClick={() => setBulkMarkDoneOpen(true)}>
                  Marquer terminé ({selected.length})
                </Button>
              ) : null}
            </>
          ) : null}
        </div>
        {bulkResource ? (
          <SavedViewsBar
            resource={bulkResource}
            currentFilters={{ q, ...savedFilters }}
            onApply={(filters) => {
              setPage(1)
              if (typeof filters.q === 'string') setQ(filters.q)
              setSavedFilters(filters)
            }}
          />
        ) : null}
      </Section>

      {loading ? (
        <p className="muted">Chargement…</p>
      ) : error ? (
        <EmptyState title="Erreur" description={error} action={<Button onClick={refresh}>Réessayer</Button>} />
      ) : items.length === 0 ? (
        <EmptyState
          title={emptyTitle}
          description={emptyDescription}
          action={
            <Button type="button" variant="primary" onClick={() => setCreateOpen(true)}>
              Créer le premier
            </Button>
          }
        />
      ) : (
        <Section title={`${total} résultat(s)`} spacing="compact">
          <ul className="sales-workspace__list">
            {items.map((row) => (
              <li key={row.id} className="sales-workspace__list-item">
                <header>
                  <label className="sales-workspace__meta-row">
                    <input
                      type="checkbox"
                      checked={selected.includes(row.id)}
                      onChange={() => toggle(row.id)}
                      aria-label={`Sélectionner ${row.id}`}
                    />
                    {rowHref ? (
                      <Link to={rowHref(row)}>
                        <strong>{columns[0]?.render(row)}</strong>
                      </Link>
                    ) : (
                      <strong>{columns[0]?.render(row)}</strong>
                    )}
                  </label>
                  <div className="sales-deal__header-actions">
                    {onDelete ? (
                      <Button type="button" size="sm" variant="danger" onClick={() => setDeleteId(row.id)}>
                        Supprimer
                      </Button>
                    ) : null}
                  </div>
                </header>
                <p className="muted">
                  {columns.slice(1).map((c) => (
                    <span key={c.key} style={{ marginRight: 12 }}>
                      {c.label}: {c.render(row)}
                    </span>
                  ))}
                </p>
              </li>
            ))}
          </ul>
          <div className="sales-deal__header-actions">
            <Button
              type="button"
              variant="secondary"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              Précédent
            </Button>
            <Badge tone="neutral">
              Page {page} / {pageCount}
            </Badge>
            <Button
              type="button"
              variant="secondary"
              disabled={page >= pageCount}
              onClick={() => setPage((p) => p + 1)}
            >
              Suivant
            </Button>
          </div>
        </Section>
      )}

      <QuickCreateDrawer
        open={createOpen}
        kind={createKind}
        onOpenChange={setCreateOpen}
        onCreated={() => refresh()}
      />

      <ConfirmDialog
        open={deleteId != null}
        onOpenChange={(o) => !o && setDeleteId(null)}
        title="Supprimer"
        description="Suppression logique — la fiche disparaît des listes actives."
        confirmLabel="Supprimer"
        tone="danger"
        loading={busy}
        onConfirm={runDelete}
      />

      <ConfirmDialog
        open={bulkOpen}
        onOpenChange={setBulkOpen}
        title="Suppression groupée"
        description={`${selected.length} élément(s) seront archivés (soft delete).`}
        confirmLabel="Confirmer"
        tone="danger"
        loading={busy}
        onConfirm={runBulkDelete}
      />

      <ConfirmDialog
        open={bulkMarkDoneOpen}
        onOpenChange={setBulkMarkDoneOpen}
        title="Marquer terminé"
        description={`${selected.length} tâche(s) seront marquées comme terminées.`}
        confirmLabel="Confirmer"
        loading={busy}
        onConfirm={runBulkMarkDone}
      />
    </Container>
  )
}

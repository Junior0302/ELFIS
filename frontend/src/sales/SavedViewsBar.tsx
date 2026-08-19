/**
 * Saved Views — créer / appliquer / défaut / supprimer (S1.8).
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../auth'
import { Badge, Button, Input } from '../design-system'

export type SavedViewRow = {
  id: number
  name: string
  resource: string
  filters: Record<string, unknown>
  sort?: string | null
  is_default: boolean
  is_shared: boolean
}

type Props = {
  resource: string
  currentFilters: Record<string, unknown>
  onApply: (filters: Record<string, unknown>) => void
}

export function SavedViewsBar({ resource, currentFilters, onApply }: Props) {
  const { token, orgId } = useAuth()
  const [views, setViews] = useState<SavedViewRow[]>([])
  const [name, setName] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const appliedDefault = useRef(false)
  const onApplyRef = useRef(onApply)
  onApplyRef.current = onApply

  const refresh = useCallback(() => {
    if (!token || orgId == null) return
    void api
      .listSalesSavedViews(token, orgId, resource)
      .then((rows) => {
        const list = rows as SavedViewRow[]
        setViews(list)
        if (!appliedDefault.current) {
          const def = list.find((v) => v.is_default)
          if (def) {
            appliedDefault.current = true
            onApplyRef.current(def.filters || {})
          }
        }
      })
      .catch(() => setViews([]))
  }, [token, orgId, resource])

  useEffect(() => {
    appliedDefault.current = false
    refresh()
  }, [refresh])

  const save = async () => {
    if (!token || orgId == null || !name.trim() || busy) return
    setBusy(true)
    setError('')
    try {
      await api.createSalesSavedView(token, orgId, {
        resource,
        name: name.trim(),
        filters: currentFilters,
        is_default: views.length === 0,
      })
      setName('')
      refresh()
    } catch (err: unknown) {
      setError(
        err && typeof err === 'object' && 'message' in err
          ? String((err as { message: unknown }).message)
          : 'Enregistrement impossible',
      )
    } finally {
      setBusy(false)
    }
  }

  const setDefault = async (id: number) => {
    if (!token || orgId == null) return
    await api.updateSalesSavedView(token, orgId, id, { is_default: true })
    refresh()
  }

  const duplicate = async (view: SavedViewRow) => {
    if (!token || orgId == null) return
    await api.createSalesSavedView(token, orgId, {
      resource,
      name: `${view.name} (copie)`,
      filters: view.filters,
      sort: view.sort ?? undefined,
    })
    refresh()
  }

  const remove = async (id: number) => {
    if (!token || orgId == null) return
    await api.deleteSalesSavedView(token, orgId, id)
    refresh()
  }

  return (
    <div className="sales-deal__header-actions" style={{ flexWrap: 'wrap', gap: 8 }}>
      <span className="muted">Vues :</span>
      {views.map((v) => (
        <span key={v.id} className="sales-deal__header-actions" style={{ gap: 4 }}>
          <Button type="button" size="sm" variant="secondary" onClick={() => onApply(v.filters || {})}>
            {v.name}
          </Button>
          {v.is_default ? <Badge tone="accent">Défaut</Badge> : null}
          <Button type="button" size="sm" variant="secondary" onClick={() => void setDefault(v.id)}>
            Défaut
          </Button>
          <Button type="button" size="sm" variant="secondary" onClick={() => void duplicate(v)}>
            Dupliquer
          </Button>
          <Button type="button" size="sm" variant="secondary" onClick={() => void remove(v.id)}>
            Suppr.
          </Button>
        </span>
      ))}
      <Input
        aria-label="Nom de la vue"
        placeholder="Nom vue…"
        value={name}
        onChange={(e) => setName(e.target.value)}
        style={{ maxWidth: 160 }}
      />
      <Button type="button" size="sm" variant="primary" disabled={busy || !name.trim()} onClick={() => void save()}>
        Enregistrer la vue
      </Button>
      {error ? (
        <span className="muted" role="alert">
          {error}
        </span>
      ) : null}
    </div>
  )
}

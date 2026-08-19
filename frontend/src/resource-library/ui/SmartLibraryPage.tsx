import { useMemo, useState } from 'react'
import { can } from '../../types/permissions'
import { useAuth } from '../../auth'
import { getResourceActions } from '../actions'
import { duplicateLocalResource } from '../sources/localLibrarySource'
import { useResourceLibrary } from '../hooks/useResourceLibrary'
import type { Resource, ResourceActionId, ResourceCreateInput } from '../types'
import { ImportPlaceholder } from './ImportPlaceholder'
import { LibraryEmptyState } from './LibraryEmptyState'
import { ResourceCard } from './ResourceCard'
import { ResourceCreateForm } from './ResourceCreateForm'
import { SmartFilters } from './SmartFilters'
import { SmartLibraryNav } from './SmartLibraryNav'
import './smart-library.css'

export default function SmartLibraryPage() {
  const { token, orgId, memberships } = useAuth()
  const {
    source,
    filters,
    updateFilters,
    items,
    result,
    page,
    setPage,
    loading,
    error,
    metaDisabledReason,
    availableVatRates,
    reload,
    capabilities,
  } = useResourceLibrary()

  const [view, setView] = useState<'cards' | 'list'>('cards')
  const [showCreate, setShowCreate] = useState(false)
  const [editing, setEditing] = useState<Resource | null>(null)
  const [showImport, setShowImport] = useState(false)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [detail, setDetail] = useState<Resource | null>(null)

  const perms = useMemo(() => {
    const m = memberships.find((x) => x.organization_id === orgId)
    return m?.permissions ?? []
  }, [memberships, orgId])

  const canWrite = can(perms, 'invoice.create') || can(perms, '*')

  const onCreate = async (input: ResourceCreateInput) => {
    if (!token || !source.create) return
    setBusy(true)
    setMessage('')
    try {
      await source.create(input, token, orgId)
      setShowCreate(false)
      setMessage('Ressource créée.')
      reload()
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'Création impossible')
    } finally {
      setBusy(false)
    }
  }

  const onUpdate = async (input: ResourceCreateInput) => {
    if (!token || !editing || !source.update) return
    setBusy(true)
    setMessage('')
    try {
      await source.update(
        editing.id,
        { ...input, active: input.active },
        token,
        orgId,
      )
      setEditing(null)
      setMessage('Ressource mise à jour.')
      reload()
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'Mise à jour impossible')
    } finally {
      setBusy(false)
    }
  }

  const onAction = async (action: ResourceActionId, resource: Resource) => {
    setMessage('')
    if (action === 'view') {
      setDetail(resource)
      return
    }
    if (action === 'edit') {
      if (!canWrite) {
        setMessage('Permission invoice.create requise pour modifier.')
        return
      }
      setEditing(resource)
      setShowCreate(false)
      return
    }
    if (action === 'duplicate') {
      if (!token || !canWrite) {
        setMessage('Permission invoice.create requise pour dupliquer.')
        return
      }
      setBusy(true)
      try {
        await duplicateLocalResource(resource, token, orgId)
        setMessage('Ressource dupliquée.')
        reload()
      } catch (e) {
        setMessage(e instanceof Error ? e.message : 'Duplication impossible')
      } finally {
        setBusy(false)
      }
      return
    }
    if (action === 'add') {
      setMessage(`« ${resource.name} » — utilisez le ProductPicker dans un document pour ajouter une ligne.`)
      return
    }
    if (action === 'history') {
      const hist = getResourceActions(source, resource).find((a) => a.id === 'history')
      setMessage(hist?.disabledReason ?? 'Historique indisponible')
    }
  }

  const showEmpty =
    !loading &&
    items.length === 0 &&
    !metaDisabledReason &&
    filters.section !== 'packs'

  const sectionEmptyTitle =
    filters.section === 'packs'
      ? 'Packs indisponibles'
      : metaDisabledReason
        ? 'Section non disponible'
        : 'Bibliothèque vide'

  const sectionEmptyDesc =
    filters.section === 'packs'
      ? 'Les packs ne sont pas supportés par la bibliothèque locale V1.'
      : metaDisabledReason
        ? metaDisabledReason
        : 'Créez votre première ressource ou préparez un import (CSV / InventoryPilot).'

  return (
    <div className="sl-root" data-smart-library="f12">
      <header className="sl-hero">
        <div>
          <h2>Smart Library</h2>
          <p>
            Bibliothèque de ressources ComptaPilot — source officielle produits / services.
            InventoryPilot prêt à brancher sans changement d’UX.
          </p>
        </div>
        <div className="sl-hero__actions">
          <button
            type="button"
            className="btn"
            disabled={!canWrite || !capabilities.create}
            onClick={() => {
              setEditing(null)
              setShowCreate(true)
              setShowImport(false)
            }}
          >
            Créer
          </button>
          <button
            type="button"
            className="btn secondary"
            onClick={() => {
              setShowImport(true)
              setShowCreate(false)
              setEditing(null)
            }}
          >
            Importer
          </button>
        </div>
      </header>

      {error ? <div className="panel form-error">{error}</div> : null}
      {message ? <p className="sl-status" role="status">{message}</p> : null}

      {showCreate ? (
        <ResourceCreateForm
          busy={busy}
          onCancel={() => setShowCreate(false)}
          onSubmit={onCreate}
        />
      ) : null}
      {editing ? (
        <ResourceCreateForm
          initial={editing}
          busy={busy}
          onCancel={() => setEditing(null)}
          onSubmit={onUpdate}
        />
      ) : null}
      {showImport ? <ImportPlaceholder onClose={() => setShowImport(false)} /> : null}

      {detail ? (
        <div className="sl-form" role="dialog" aria-label="Détail ressource">
          <h3 style={{ margin: 0 }}>{detail.name}</h3>
          <p className="sl-status" style={{ margin: 0 }}>
            {detail.kind} · {detail.unitPriceHt.toFixed(2)} € HT · TVA {detail.vatRate}% ·{' '}
            {detail.status === 'active' ? 'Actif' : 'Inactif'}
          </p>
          <button type="button" className="btn secondary" onClick={() => setDetail(null)}>
            Fermer
          </button>
        </div>
      ) : null}

      <div className="sl-layout">
        <SmartLibraryNav
          section={filters.section}
          onChange={(section) => updateFilters({ section })}
          source={source}
        />
        <div className="sl-main">
          <SmartFilters
            filters={filters}
            onChange={updateFilters}
            view={view}
            onViewChange={setView}
            vatOptions={availableVatRates}
          />

          {loading ? <p className="sl-status">Chargement…</p> : null}

          {metaDisabledReason || filters.section === 'packs' ? (
            <LibraryEmptyState
              title={sectionEmptyTitle}
              description={sectionEmptyDesc}
              onCreate={
                canWrite
                  ? () => {
                      setShowCreate(true)
                    }
                  : undefined
              }
              createDisabled={!canWrite}
            />
          ) : null}

          {showEmpty ? (
            <LibraryEmptyState
              title="Aucune ressource"
              description="La bibliothèque locale est vide. Créez un produit ou un service, ou préparez un import."
              onCreate={
                canWrite
                  ? () => {
                      setShowCreate(true)
                    }
                  : undefined
              }
              onImport={() => setShowImport(true)}
              createDisabled={!canWrite}
            />
          ) : null}

          {!metaDisabledReason && filters.section !== 'packs' && items.length > 0 ? (
            <>
              <div className={view === 'list' ? 'sl-grid sl-grid--list' : 'sl-grid'}>
                {items.map((resource) => (
                  <ResourceCard
                    key={resource.id}
                    resource={resource}
                    source={source}
                    view={view}
                    onAction={(a, r) => void onAction(a, r)}
                  />
                ))}
              </div>
              <div className="sl-pager">
                <span>
                  {result.total} ressource{result.total > 1 ? 's' : ''} · page {result.page}
                </span>
                <div className="sl-hero__actions">
                  <button
                    type="button"
                    className="btn secondary"
                    disabled={page <= 1}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                  >
                    Précédent
                  </button>
                  <button
                    type="button"
                    className="btn secondary"
                    disabled={!result.hasMore}
                    onClick={() => setPage((p) => p + 1)}
                  >
                    Suivant
                  </button>
                </div>
              </div>
            </>
          ) : null}
        </div>
      </div>
    </div>
  )
}

/**
 * LibraryCatalogModal — sous-modale catalogue centrée au-dessus du Composer (F1.3.2.2).
 * Portal hors stacking context Composer ; z-index tokens FP_OVERLAY_Z.
 */

import { useCallback, useId, useMemo, useRef, useState, type RefObject } from 'react'
import { Portal } from '../../design-system/overlays/Portal'
import { useOverlayBehaviour } from '../../design-system/overlays/hooks/useOverlayBehaviour'
import { useOverlayContextOptional } from '../../design-system/overlays/OverlayProvider'
import { OverlayParentIdContext } from '../../design-system/overlays/OverlayContext'
import { formatEuro } from '../../api'
import { useResourceLibrary } from '../../resource-library/hooks/useResourceLibrary'
import { resourceToSearchResult } from '../../resource-library/adapters/resourceToSearchResult'
import type { LibraryNavSection, Resource } from '../../resource-library/types'
import type { SearchResult } from '../../platform-search/types'
import { FP_OVERLAY_Z } from './overlayLayers'
import { ProductCreationDialog } from './ProductCreationDialog'
import './library-catalog-modal.css'

export type LibraryCatalogModalProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  onAddResource: (item: SearchResult) => void
  returnFocusRef?: RefObject<HTMLElement | null>
  /** TVA par défaut pour création produit */
  defaultVatRate?: number
}

const FILTER_TABS: { id: LibraryNavSection; label: string }[] = [
  { id: 'all', label: 'Tous' },
  { id: 'products', label: 'Produits' },
  { id: 'services', label: 'Services' },
  { id: 'packs', label: 'Packs' },
]

function kindLabel(kind: Resource['kind']): string {
  if (kind === 'service') return 'Service'
  if (kind === 'pack') return 'Pack'
  return 'Produit'
}

export function LibraryCatalogModal({
  open,
  onOpenChange,
  onAddResource,
  returnFocusRef,
  defaultVatRate = 20,
}: LibraryCatalogModalProps) {
  const searchId = useId()
  const titleId = useId()
  const descId = useId()
  const searchRef = useRef<HTMLInputElement>(null)
  const panelRef = useRef<HTMLDivElement>(null)
  const [toast, setToast] = useState('')
  const [createOpen, setCreateOpen] = useState(false)
  const lib = useResourceLibrary({ activeOnly: true, sort: 'name_asc' })
  const mgr = useOverlayContextOptional()

  const packsSupported = Boolean(lib.capabilities.packs)
  const tabs = useMemo(
    () => FILTER_TABS.filter((t) => t.id !== 'packs' || packsSupported),
    [packsSupported],
  )

  const onClose = useCallback(() => {
    setCreateOpen(false)
    onOpenChange(false)
  }, [onOpenChange])

  const { overlayId } = useOverlayBehaviour({
    open,
    type: 'dialog',
    modal: true,
    dismissible: !createOpen,
    closeOnEscape: !createOpen,
    closeOnBackdrop: !createOpen,
    onClose,
    panelRef,
    initialFocusRef: searchRef,
    returnFocusRef,
    lockScroll: true,
  })

  const handleAdd = useCallback(
    (resource: Resource) => {
      onAddResource(resourceToSearchResult(resource))
      setToast(`Ajouté : ${resource.name}`)
      window.setTimeout(() => setToast(''), 2200)
    },
    [onAddResource],
  )

  if (!open) return null

  return (
    <Portal>
      <div
        className="fp-catalog-modal-backdrop"
        role="presentation"
        data-fp-catalog-layer="backdrop"
        style={{ zIndex: FP_OVERLAY_Z.submodalBackdrop }}
        onClick={() => {
          if (createOpen) return
          mgr?.requestClose(overlayId, 'backdrop') ?? onClose()
        }}
      >
        <div
          ref={panelRef}
          className="fp-catalog-modal"
          role="dialog"
          aria-modal="true"
          aria-labelledby={titleId}
          aria-describedby={descId}
          tabIndex={-1}
          data-fp-catalog-layer="modal"
          data-fp-library-catalog-modal="true"
          style={{ zIndex: FP_OVERLAY_Z.catalogModal }}
          onClick={(e) => e.stopPropagation()}
        >
          <OverlayParentIdContext.Provider value={overlayId}>
            <header className="fp-catalog-modal__header">
              <div>
                <h2 id={titleId} className="fp-catalog-modal__title">
                  Catalogue
                </h2>
                <p id={descId} className="fp-catalog-modal__desc">
                  Smart Library — ajoutez des produits ou services au document.
                </p>
              </div>
              <button
                type="button"
                className="fp-catalog-modal__close"
                aria-label="Fermer"
                onClick={onClose}
              >
                ×
              </button>
            </header>

            <div className="fp-catalog-modal__body">
              <div className="fp-catalog-modal__toolbar">
                <label className="fp-catalog-modal__search" htmlFor={searchId}>
                  <span className="visually-hidden">Rechercher dans le catalogue</span>
                  <input
                    ref={searchRef}
                    id={searchId}
                    type="search"
                    placeholder="Rechercher…"
                    value={lib.filters.q}
                    onChange={(e) => lib.updateFilters({ q: e.target.value })}
                    aria-label="Rechercher dans le catalogue"
                  />
                </label>
                <div
                  className="fp-catalog-modal__tabs"
                  role="tablist"
                  aria-label="Filtres catalogue"
                >
                  {tabs.map((tab) => {
                    const selected = lib.filters.section === tab.id
                    return (
                      <button
                        key={tab.id}
                        type="button"
                        role="tab"
                        aria-selected={selected}
                        className={
                          selected
                            ? 'fp-catalog-modal__tab is-selected'
                            : 'fp-catalog-modal__tab'
                        }
                        onClick={() => lib.updateFilters({ section: tab.id })}
                      >
                        {tab.label}
                      </button>
                    )
                  })}
                </div>
              </div>

              {toast ? (
                <p className="fp-catalog-modal__toast" role="status" aria-live="polite">
                  {toast}
                </p>
              ) : null}

              {lib.metaDisabledReason ? (
                <p className="muted" role="status">
                  {lib.metaDisabledReason}
                </p>
              ) : null}

              {lib.error ? (
                <div className="panel form-error" role="alert">
                  {lib.error}{' '}
                  <button type="button" className="btn secondary" onClick={() => lib.reload()}>
                    Réessayer
                  </button>
                </div>
              ) : null}

              {lib.loading ? (
                <p className="muted" aria-busy="true">
                  Chargement du catalogue…
                </p>
              ) : null}

              {!lib.loading && !lib.error && lib.items.length === 0 ? (
                <p className="muted" role="status">
                  Aucun élément dans le catalogue.
                </p>
              ) : null}

              <ul className="fp-catalog-modal__list" aria-label="Résultats catalogue">
                {lib.items.map((resource) => (
                  <li key={resource.id} className="fp-catalog-modal__item">
                    <div className="fp-catalog-modal__item-body">
                      <strong>{resource.name}</strong>
                      <span className="fp-catalog-modal__meta">
                        {kindLabel(resource.kind)} · {formatEuro(resource.unitPriceHt)} HT · TVA{' '}
                        {resource.vatRate} %
                      </span>
                      {resource.description ? (
                        <span className="fp-catalog-modal__desc-item">{resource.description}</span>
                      ) : null}
                    </div>
                    <button
                      type="button"
                      className="btn"
                      onClick={() => handleAdd(resource)}
                      aria-label={`Ajouter ${resource.name}`}
                    >
                      Ajouter
                    </button>
                  </li>
                ))}
              </ul>
            </div>

            <footer className="fp-catalog-modal__footer">
              <button
                type="button"
                className="btn secondary"
                onClick={() => setCreateOpen(true)}
              >
                Nouveau produit
              </button>
              <button type="button" className="btn" onClick={onClose}>
                Fermer
              </button>
            </footer>

            <ProductCreationDialog
              open={createOpen}
              onOpenChange={setCreateOpen}
              defaultVatRate={defaultVatRate}
              onCreated={(resource) => {
                handleAdd(resource)
                lib.reload()
                setCreateOpen(false)
              }}
            />
          </OverlayParentIdContext.Provider>
        </div>
      </div>
    </Portal>
  )
}

/** @deprecated F1.3.2.2 — utiliser LibraryCatalogModal */
export { LibraryCatalogModal as LibraryCatalogDrawer }

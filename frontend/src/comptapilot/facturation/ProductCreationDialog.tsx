/**
 * ProductCreationDialog — création produit au-dessus du LibraryCatalogModal (F1.3.2.2).
 */

import { useId, useRef, useState, type FormEvent } from 'react'
import { Portal } from '../../design-system/overlays/Portal'
import { useOverlayBehaviour } from '../../design-system/overlays/hooks/useOverlayBehaviour'
import { api } from '../../api'
import { useAuth } from '../../auth'
import { catalogItemToResource } from '../../resource-library/adapters/catalogToResource'
import type { Resource } from '../../resource-library/types'
import { FP_OVERLAY_Z } from './overlayLayers'
import './library-catalog-modal.css'

export type ProductCreationDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  defaultVatRate?: number
  onCreated: (resource: Resource) => void
}

export function ProductCreationDialog({
  open,
  onOpenChange,
  defaultVatRate = 20,
  onCreated,
}: ProductCreationDialogProps) {
  const { token, orgId } = useAuth()
  const titleId = useId()
  const nameRef = useRef<HTMLInputElement>(null)
  const panelRef = useRef<HTMLDivElement>(null)
  const [name, setName] = useState('')
  const [price, setPrice] = useState('0')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const onClose = () => {
    if (busy) return
    setError('')
    onOpenChange(false)
  }

  useOverlayBehaviour({
    open,
    type: 'dialog',
    modal: true,
    dismissible: !busy,
    closeOnEscape: !busy,
    closeOnBackdrop: !busy,
    onClose,
    panelRef,
    initialFocusRef: nameRef,
    lockScroll: true,
  })

  const submit = async (e?: FormEvent) => {
    e?.preventDefault()
    if (!token || !name.trim()) return
    setBusy(true)
    setError('')
    try {
      const created = await api.createCatalogItem(
        {
          name: name.trim(),
          unit_price_ht: Number(price) || 0,
          vat_rate: defaultVatRate,
          active: true,
        },
        token,
        orgId,
      )
      onCreated(catalogItemToResource(created))
      setName('')
      setPrice('0')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Création impossible')
    } finally {
      setBusy(false)
    }
  }

  if (!open) return null

  return (
    <Portal>
      <div
        className="fp-product-create-backdrop"
        role="presentation"
        data-fp-catalog-layer="create-backdrop"
        style={{ zIndex: FP_OVERLAY_Z.nestedCreate }}
        onClick={() => {
          if (busy) return
          onClose()
        }}
      >
        <div
          ref={panelRef}
          className="fp-product-create-dialog"
          role="dialog"
          aria-modal="true"
          aria-labelledby={titleId}
          tabIndex={-1}
          data-fp-product-creation-dialog="true"
          onClick={(ev) => ev.stopPropagation()}
        >
          <header className="fp-product-create-dialog__header">
            <h2 id={titleId}>Nouveau produit</h2>
            <button
              type="button"
              className="fp-catalog-modal__close"
              aria-label="Fermer"
              disabled={busy}
              onClick={onClose}
            >
              ×
            </button>
          </header>
          <form className="fp-product-create-dialog__form" onSubmit={(e) => void submit(e)}>
            <label>
              <span>Nom</span>
              <input
                ref={nameRef}
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                aria-label="Nom du nouveau produit"
                required
              />
            </label>
            <label>
              <span>Prix HT</span>
              <input
                type="number"
                min={0}
                step={0.01}
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                aria-label="Prix HT du nouveau produit"
              />
            </label>
            {error ? (
              <p className="error" role="alert">
                {error}
              </p>
            ) : null}
            <div className="fp-product-create-dialog__actions">
              <button type="button" className="btn secondary" disabled={busy} onClick={onClose}>
                Annuler
              </button>
              <button type="submit" className="btn" disabled={busy || !name.trim()}>
                {busy ? 'Création…' : 'Créer et ajouter'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Portal>
  )
}

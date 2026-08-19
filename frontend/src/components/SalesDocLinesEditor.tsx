import { useEffect, useState } from 'react'
import { api, formatEuro, type CatalogItem } from '../api'
import {
  emptySalesLine,
  lineAmountHt,
  linesTotalHt,
  type SalesLineDraft,
} from '../salesDocLines'

type Props = {
  lines: SalesLineDraft[]
  onChange: (lines: SalesLineDraft[]) => void
  token: string | null | undefined
  orgId: number | null | undefined
  disabled?: boolean
}

export default function SalesDocLinesEditor({
  lines,
  onChange,
  token,
  orgId,
  disabled,
}: Props) {
  const [catalog, setCatalog] = useState<CatalogItem[]>([])
  const [catalogError, setCatalogError] = useState('')

  useEffect(() => {
    if (!token) return
    let cancelled = false
    api
      .listCatalog(token, orgId, true)
      .then((res) => {
        if (!cancelled) setCatalog(res.items.filter((i) => i.active))
      })
      .catch((e) => {
        if (!cancelled) setCatalogError(e instanceof Error ? e.message : 'Catalogue indisponible')
      })
    return () => {
      cancelled = true
    }
  }, [token, orgId])

  const updateLine = (index: number, patch: Partial<SalesLineDraft>) => {
    onChange(lines.map((line, i) => (i === index ? { ...line, ...patch } : line)))
  }

  const addLine = () => onChange([...lines, emptySalesLine()])

  const removeLine = (index: number) => {
    if (lines.length <= 1) {
      onChange([emptySalesLine()])
      return
    }
    onChange(lines.filter((_, i) => i !== index))
  }

  const applyCatalog = (index: number, itemId: string) => {
    if (!itemId) {
      updateLine(index, { catalog_item_id: null })
      return
    }
    const item = catalog.find((c) => String(c.id) === itemId)
    if (!item) return
    updateLine(index, {
      catalog_item_id: item.id,
      label: item.name,
      unit_price: item.unit_price_ht,
    })
  }

  const total = linesTotalHt(lines)

  return (
    <div className="field full sales-lines-editor">
      <label>Lignes</label>
      {catalogError ? <p className="muted">{catalogError}</p> : null}
      <div className="list" style={{ gap: '0.75rem' }}>
        {lines.map((line, index) => (
          <div
            key={index}
            className="form-grid"
            style={{
              border: '1px solid var(--border, rgba(148,163,184,0.35))',
              borderRadius: 8,
              padding: '0.75rem',
            }}
          >
            {catalog.length > 0 ? (
              <div className="field full">
                <label htmlFor={`line-catalog-${index}`}>Depuis le catalogue</label>
                <select
                  id={`line-catalog-${index}`}
                  value={line.catalog_item_id != null ? String(line.catalog_item_id) : ''}
                  disabled={disabled}
                  onChange={(e) => applyCatalog(index, e.target.value)}
                >
                  <option value="">Saisie libre…</option>
                  {catalog.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name} — {formatEuro(item.unit_price_ht)} HT
                    </option>
                  ))}
                </select>
              </div>
            ) : null}
            <div className="field full">
              <label htmlFor={`line-label-${index}`}>Désignation</label>
              <input
                id={`line-label-${index}`}
                value={line.label}
                disabled={disabled}
                required
                onChange={(e) => updateLine(index, { label: e.target.value, catalog_item_id: null })}
                placeholder="Prestation ou produit"
              />
            </div>
            <div className="field">
              <label htmlFor={`line-qty-${index}`}>Quantité</label>
              <input
                id={`line-qty-${index}`}
                type="number"
                step="0.01"
                min="0"
                value={line.quantity}
                disabled={disabled}
                required
                onChange={(e) => updateLine(index, { quantity: Number(e.target.value) })}
              />
            </div>
            <div className="field">
              <label htmlFor={`line-price-${index}`}>Prix unitaire HT</label>
              <input
                id={`line-price-${index}`}
                type="number"
                step="0.01"
                min="0"
                value={line.unit_price}
                disabled={disabled}
                required
                onChange={(e) =>
                  updateLine(index, { unit_price: Number(e.target.value), catalog_item_id: null })
                }
              />
            </div>
            <div className="field">
              <label>Total ligne</label>
              <strong>{formatEuro(lineAmountHt(line))}</strong>
            </div>
            <div className="actions" style={{ marginTop: 0 }}>
              <button
                className="btn secondary"
                type="button"
                disabled={disabled}
                onClick={() => removeLine(index)}
              >
                Retirer
              </button>
            </div>
          </div>
        ))}
      </div>
      <div className="actions" style={{ marginTop: '0.75rem', alignItems: 'center' }}>
        <button className="btn secondary" type="button" disabled={disabled} onClick={addLine}>
          Ajouter une ligne
        </button>
        <strong>Total HT : {formatEuro(total)}</strong>
        {catalog.length === 0 && !catalogError ? (
          <span className="muted">Catalogue vide — saisie libre des lignes.</span>
        ) : null}
      </div>
    </div>
  )
}

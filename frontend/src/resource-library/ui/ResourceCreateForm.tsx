import { useState, type FormEvent } from 'react'
import type { Resource, ResourceCreateInput, ResourceKind } from '../types'

const empty: ResourceCreateInput = {
  name: '',
  kind: 'product',
  unit: 'unité',
  unitPriceHt: 0,
  vatRate: 20,
  active: true,
}

export type ResourceCreateFormProps = {
  initial?: Resource | null
  busy?: boolean
  onSubmit: (input: ResourceCreateInput) => Promise<void> | void
  onCancel: () => void
}

export function ResourceCreateForm({
  initial,
  busy,
  onSubmit,
  onCancel,
}: ResourceCreateFormProps) {
  const [form, setForm] = useState<ResourceCreateInput>(() =>
    initial
      ? {
          name: initial.name,
          kind: initial.kind === 'pack' ? 'product' : initial.kind,
          unit: initial.unit,
          unitPriceHt: initial.unitPriceHt,
          vatRate: initial.vatRate,
          active: initial.status === 'active',
          description: initial.description,
        }
      : empty,
  )

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!form.name.trim()) return
    await onSubmit({
      ...form,
      name: form.name.trim(),
      kind: form.kind === 'pack' ? 'product' : form.kind,
    })
  }

  return (
    <form className="sl-form" onSubmit={(e) => void handleSubmit(e)} aria-label="Formulaire ressource">
      <h3 style={{ margin: 0 }}>{initial ? 'Modifier la ressource' : 'Nouvelle ressource'}</h3>
      <p className="sl-status" style={{ margin: 0 }}>
        Même formulaire quelle que soit la source (Local Library aujourd’hui — InventoryPilot demain).
      </p>
      <div className="sl-form__grid">
        <label>
          Nom
          <input
            required
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
        </label>
        <label>
          Type
          <select
            value={form.kind}
            onChange={(e) => setForm({ ...form, kind: e.target.value as ResourceKind })}
          >
            <option value="product">Produit</option>
            <option value="service">Service</option>
          </select>
        </label>
        <label>
          Unité
          <input
            value={form.unit ?? 'unité'}
            onChange={(e) => setForm({ ...form, unit: e.target.value })}
          />
        </label>
        <label>
          Prix HT
          <input
            type="number"
            step="0.01"
            min={0}
            value={form.unitPriceHt}
            onChange={(e) => setForm({ ...form, unitPriceHt: Number(e.target.value) })}
          />
        </label>
        <label>
          TVA %
          <input
            type="number"
            step="0.1"
            min={0}
            value={form.vatRate}
            onChange={(e) => setForm({ ...form, vatRate: Number(e.target.value) })}
          />
        </label>
        <label className="checkbox-inline" style={{ alignSelf: 'end' }}>
          <input
            type="checkbox"
            checked={form.active ?? true}
            onChange={(e) => setForm({ ...form, active: e.target.checked })}
          />
          Actif
        </label>
      </div>
      <div className="sl-form__actions">
        <button className="btn" type="submit" disabled={busy || !form.name.trim()}>
          {initial ? 'Enregistrer' : 'Créer'}
        </button>
        <button className="btn secondary" type="button" onClick={onCancel} disabled={busy}>
          Annuler
        </button>
      </div>
    </form>
  )
}

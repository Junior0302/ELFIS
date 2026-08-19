/**
 * CustomerPicker — spécialisation RelationPicker + fallback billing.
 * Intègre Document Composer : ID opaque SharedRelation, fallback customerId.
 */

import { useMemo, useState, type ReactNode } from 'react'
import { api } from '../../api'
import { useAuth } from '../../auth'
import type { SearchResult } from '../types'
import { RelationPicker } from './RelationPicker'

export type CustomerPickerSelection = {
  customerId: number | null
  relationId: string | null
  displayName: string
  email: string
  phone?: string
  address?: string
  source: 'billing_customer' | 'shared_relation'
  raw: SearchResult
}

export type CustomerPickerProps = {
  onSelect: (selection: CustomerPickerSelection) => void
  selectedSlot?: ReactNode
  /** Affiche le formulaire de création billing (workflow existant). */
  allowCreate?: boolean
  className?: string
}

export function searchResultToCustomerSelection(item: SearchResult): CustomerPickerSelection {
  const meta = item.metadata ?? {}
  if (item.source === 'billing_customers' || meta.billing_fallback) {
    return {
      customerId: Number(meta.customerId) || null,
      relationId: null,
      displayName: item.title,
      email: String(meta.email ?? item.subtitle ?? ''),
      phone: meta.phone ? String(meta.phone) : undefined,
      address: meta.address ? String(meta.address) : undefined,
      source: 'billing_customer',
      raw: item,
    }
  }

  const sourceEntityId = meta.source_entity_id
  const sourceSystem = meta.source_system
  const customerId =
    sourceSystem === 'customer' && typeof sourceEntityId === 'number' ? sourceEntityId : null

  return {
    customerId,
    relationId: String(meta.relationId ?? item.id),
    displayName: item.title,
    email: String(meta.email ?? ''),
    phone: meta.phone ? String(meta.phone) : undefined,
    address: meta.address ? String(meta.address) : undefined,
    source: 'shared_relation',
    raw: item,
  }
}

export function CustomerPicker({
  onSelect,
  selectedSlot,
  allowCreate = true,
  className,
}: CustomerPickerProps) {
  const { token, orgId } = useAuth()
  const [createOpen, setCreateOpen] = useState(false)
  const [newName, setNewName] = useState('')
  const [newEmail, setNewEmail] = useState('')
  const [createError, setCreateError] = useState('')
  const [creating, setCreating] = useState(false)

  const createAction = useMemo(() => {
    if (!allowCreate) return undefined
    return {
      label: createOpen ? 'Fermer' : '+ Ajouter un client',
      onClick: () => setCreateOpen((v) => !v),
    }
  }, [allowCreate, createOpen])

  const createClient = async () => {
    if (!token || !newName.trim()) return
    setCreating(true)
    setCreateError('')
    try {
      const created = await api.createCustomer(
        { name: newName.trim(), email: newEmail.trim() || undefined },
        token,
        orgId,
      )
      const raw: SearchResult = {
        type: 'customer',
        id: `billing_customer:${created.id}`,
        title: created.name,
        subtitle: created.email || undefined,
        source: 'billing_customers',
        metadata: {
          customerId: created.id,
          email: created.email || '',
          phone: created.phone,
          address: created.address,
          billing_fallback: true,
        },
      }
      onSelect(searchResultToCustomerSelection(raw))
      setCreateOpen(false)
      setNewName('')
      setNewEmail('')
    } catch (e) {
      setCreateError(e instanceof Error ? e.message : 'Création impossible')
    } finally {
      setCreating(false)
    }
  }

  return (
    <RelationPicker
      role="customer"
      className={className}
      label="Client"
      placeholder="Rechercher un client…"
      createAction={createAction}
      selectedSlot={selectedSlot}
      onSelect={(item) => onSelect(searchResultToCustomerSelection(item))}
      footer={
        createOpen ? (
          <div className="ps-picker__actions" style={{ marginTop: '0.75rem', flexDirection: 'column' }}>
            <div className="ps-search__input-wrap">
              <input
                className="ps-search__input"
                type="text"
                placeholder="Nom du client"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                aria-label="Nom du nouveau client"
              />
              <input
                className="ps-search__input"
                type="email"
                placeholder="E-mail (optionnel)"
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
                aria-label="E-mail du nouveau client"
              />
              <button
                type="button"
                className="btn"
                disabled={creating || !newName.trim()}
                onClick={() => void createClient()}
              >
                Enregistrer
              </button>
            </div>
            {createError ? <p className="error">{createError}</p> : null}
          </div>
        ) : null
      }
    />
  )
}

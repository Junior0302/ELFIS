/** Libellés et formatage ELFIS Vault (frontend). */

import { formatEuro, type VaultDocumentType } from './api'

export const VAULT_DOCUMENT_TYPE_LABELS: Record<VaultDocumentType, string> = {
  customer_invoice: 'Facture client',
  supplier_invoice: 'Facture fournisseur',
  quote: 'Devis',
  credit_note: 'Avoir',
  expense_report: 'Note de frais',
  bank_statement: 'Relevé bancaire',
  contract: 'Contrat',
  other: 'Autre',
}

export function vaultDocumentTypeLabel(type: string): string {
  return VAULT_DOCUMENT_TYPE_LABELS[type as VaultDocumentType] || type
}

export function vaultArchiveStatusLabel(status: string): string {
  switch (status) {
    case 'archived':
      return 'Archivé'
    case 'pending':
      return 'En attente'
    case 'deleted':
      return 'Supprimé'
    default:
      return status
  }
}

export function vaultAccountingStatusLabel(status: string): string {
  switch (status) {
    case 'not_processed':
      return 'Non traité'
    case 'processed':
      return 'Traité'
    case 'exported':
      return 'Exporté'
    default:
      return status
  }
}

export function formatVaultAmount(value: number | string | null | undefined, currency = 'EUR'): string {
  if (value == null || value === '') return '—'
  const n = typeof value === 'number' ? value : Number(value)
  if (Number.isNaN(n)) return '—'
  if (currency === 'EUR') return formatEuro(n)
  return `${n.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${currency}`
}

export function formatVaultFileSize(bytes: number): string {
  if (!bytes || bytes < 0) return '—'
  if (bytes < 1024) return `${bytes} o`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} Ko`
  return `${(bytes / (1024 * 1024)).toLocaleString('fr-FR', { maximumFractionDigits: 1 })} Mo`
}

export function formatVaultDate(value: string | null | undefined): string {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) {
    // date-only YYYY-MM-DD
    const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(value)
    if (m) return `${m[3]}/${m[2]}/${m[1]}`
    return value
  }
  return d.toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}

export function formatVaultDateTime(value: string | null | undefined): string {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleString('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

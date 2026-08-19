/**
 * Navigation config — sections / items déclaratifs (pas de JSX ad hoc par Pilot).
 */

import type { ReactNode } from 'react'
import type { ProductId } from '../../design-system'

export type ElfisNavIconId = string

export type ElfisNavigationItem = {
  id: string
  label: string
  href: string
  icon?: ElfisNavIconId
  /** Exact match path (sinon startsWith). */
  exact?: boolean
  /** Permission / gate — laissé au render (pas inventé ici). */
  permission?: string
  locked?: boolean
  badge?: ReactNode
  /** Switch produit / lien externe plateforme. */
  kind?: 'item' | 'switch' | 'external'
  /** Sous-items — même profondeur visuelle Compta / Sales. */
  children?: ElfisNavigationItem[]
}

export type ElfisNavigationSection = {
  id: string
  label?: string
  items: ElfisNavigationItem[]
}

export type ElfisDomainNavConfig = {
  pilotId: ProductId
  domainId: string
  sections: ElfisNavigationSection[]
}

export type ElfisGlobalNavLink = {
  id: string
  label: string
  href: string
  icon?: ElfisNavIconId
}

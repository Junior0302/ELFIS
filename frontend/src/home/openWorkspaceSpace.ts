/**
 * Navigation vers un espace métier — même règles que le launcher Espaces.
 * Pas de seconde logique d’ouverture.
 */

import type { NavigateFunction } from 'react-router-dom'
import type { ProductId } from '../design-system/types'
import { setLastProductId } from './lastProduct'

const RESUME_PRODUCT_IDS = new Set<string>(['comptapilot', 'salespilot'])

export function openWorkspaceSpace(
  navigate: NavigateFunction,
  opts: {
    route: string
    engineProductId?: string | null
  },
): void {
  const pid = opts.engineProductId
  if (pid && RESUME_PRODUCT_IDS.has(pid)) {
    setLastProductId(pid as ProductId)
  }
  navigate(opts.route)
}

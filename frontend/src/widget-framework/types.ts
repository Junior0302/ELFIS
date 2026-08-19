/**
 * ELFIS Widget Framework V1 — contrats génériques (produit-agnostiques).
 */
import type { ReactNode } from 'react'

export type WidgetStatus = 'idle' | 'loading' | 'ready' | 'refreshing' | 'empty' | 'error'

export type WidgetCategory = 'observe' | 'alert' | 'forecast' | 'action' | 'explain'

export type WidgetSize = 'sm' | 'md' | 'lg' | 'full'

/** Présentation visuelle — n’altère pas le contrat de données. */
export type WidgetVariant = 'compact' | 'standard' | 'chart' | 'list' | 'hero' | 'score'

export type WidgetActionDef = {
  id: string
  label: string
  href?: string
  onClick?: () => void
  tone?: 'primary' | 'secondary' | 'danger'
}

export type WidgetDefinition = {
  id: string
  title: string
  description?: string
  category: WidgetCategory
  size?: WidgetSize
  variant?: WidgetVariant
  refreshable?: boolean
  status: WidgetStatus
  lastUpdatedAt?: string | null
  actions?: WidgetActionDef[]
  permissions?: string[]
  source?: string
  confidence?: 'high' | 'medium' | 'low' | 'unknown'
  emptyTitle?: string
  emptyDescription?: string
  errorMessage?: string
}

export type WidgetContainerProps = {
  definition: WidgetDefinition
  onRefresh?: () => void
  onRetry?: () => void
  children?: ReactNode
  className?: string
  footer?: ReactNode
  toolbarExtra?: ReactNode
}

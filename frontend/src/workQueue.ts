/** Types Work Queue C1.17. */

import type { DecisionAction } from './decisionCenter'

export type WorkQueueBucket = 'todo' | 'in_progress' | 'waiting' | 'completed'

export type WaitingReason = {
  code: string
  label: string
  description?: string | null
  retry_after?: string | null
}

export type WorkQueuePrimaryAction = {
  action_type: string
  label: string
  method: 'NAVIGATE' | 'POST'
  action_path?: string | null
  endpoint?: string | null
  enabled: boolean
}

export type WorkQueueItem = {
  decision_id: string
  decision_type: string
  bucket: WorkQueueBucket
  status: string
  execution_status: string
  severity: string
  title: string
  summary: string
  source_type: string
  source_id: string
  created_at: string
  updated_at: string
  age_label?: string | null
  primary_action?: WorkQueuePrimaryAction | null
  available_actions: DecisionAction[]
  is_blocking: boolean
  waiting_reason?: WaitingReason | null
  last_activity?: string | null
  progress_label?: string | null
  required_permission?: string | null
  evidence_summary?: string | null
  started_at?: string | null
}

export type WorkQueueCounts = {
  todo: number
  in_progress: number
  waiting: number
  completed: number
}

export type WorkQueueResponse = {
  items: WorkQueueItem[]
  pagination: {
    page: number
    page_size: number
    total_items: number
    total_pages: number
  }
  counts: WorkQueueCounts
  filters: {
    bucket?: string | null
    severity?: string | null
    decision_type?: string | null
    source_type?: string | null
    search?: string | null
    sort: string
  }
  generated_at: string
}

export const WORK_QUEUE_REFRESH_KEY = 'elfis.work_queue.refresh'

export function markWorkQueueStale(): void {
  try {
    sessionStorage.setItem(WORK_QUEUE_REFRESH_KEY, String(Date.now()))
  } catch {
    /* ignore */
  }
}

export function consumeWorkQueueStale(): boolean {
  try {
    const value = sessionStorage.getItem(WORK_QUEUE_REFRESH_KEY)
    if (!value) return false
    sessionStorage.removeItem(WORK_QUEUE_REFRESH_KEY)
    return true
  } catch {
    return false
  }
}

export function bucketLabel(bucket: WorkQueueBucket): string {
  switch (bucket) {
    case 'todo':
      return 'À traiter'
    case 'in_progress':
      return 'En cours'
    case 'waiting':
      return 'En attente'
    case 'completed':
      return 'Terminées'
    default:
      return bucket
  }
}

export function emptyCopy(bucket: WorkQueueBucket, hasFilters: boolean): { title: string; description: string } {
  if (hasFilters) {
    return {
      title: 'Aucun résultat',
      description: 'Aucun résultat ne correspond à vos filtres.',
    }
  }
  switch (bucket) {
    case 'todo':
      return {
        title: 'Rien à traiter',
        description: 'Aucun élément ne nécessite votre attention actuellement.',
      }
    case 'in_progress':
      return {
        title: 'Aucun traitement en cours',
        description: 'Vous n’avez aucun traitement en cours.',
      }
    case 'waiting':
      return {
        title: 'Rien en attente',
        description: 'Aucun élément n’attend de traitement externe ou système.',
      }
    default:
      return {
        title: 'Aucune décision terminée',
        description: 'Aucune décision terminée pour cette période.',
      }
  }
}

/**
 * Signaux Home — uniquement sources plateforme réelles.
 * Aucune invention de KPI métier (factures, prospects, etc.).
 * Espaces : WORKSPACE_REGISTRY (même SoT que le launcher).
 */

import { WORKSPACE_REGISTRY } from '../workspaces'
import { getLastProductAt, getLastProductId } from './lastProduct'

export type HomeSignal = {
  id: string
  label: string
  tone: 'info' | 'attention' | 'calm'
  href?: string
}

export type HomeHealthLamp = {
  id: string
  label: string
  /** green | orange | red — uniquement si état connu. */
  tone: 'green' | 'orange' | 'red'
  detail: string
}

export type DayDomainCard = {
  id: 'finance' | 'commercial' | 'documents' | 'organisation'
  title: string
  summary: string
  actionLabel: string
  actionTo: string | null
  status: string
  statusTone: 'ok' | 'idle' | 'warn' | 'soon'
  lastActivity: string
}

export type HomeSpaceSummary = {
  id: string
  title: string
  summary: string
  available: boolean
  to: string | null
  poweredBy?: string | null
  statusLabel: string
  accent: string
  productId?: string | null
  resumeHint?: string | null
}

export type HomeWatchItem = {
  id: string
  title: string
  context: string
  href?: string
  tone: 'attention' | 'info'
}

function formatLastSeen(iso: string | null): string {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleString('fr-FR', {
      dateStyle: 'medium',
      timeStyle: 'short',
    })
  } catch {
    return ''
  }
}

export function relativeCheckLabel(iso?: string): string {
  if (!iso) return 'à l’instant'
  try {
    const ms = Date.now() - new Date(iso).getTime()
    if (Number.isNaN(ms) || ms < 0) return 'à l’instant'
    const mins = Math.round(ms / 60000)
    if (mins < 1) return 'à l’instant'
    if (mins === 1) return 'il y a 1 min'
    if (mins < 60) return `il y a ${mins} min`
    const hours = Math.round(mins / 60)
    return hours === 1 ? 'il y a 1 h' : `il y a ${hours} h`
  } catch {
    return 'à l’instant'
  }
}

/** Badge header — uniquement états observés (connexion / org / sync). */
export function platformStatusLabel(allObservedOk: boolean): string {
  return allObservedOk ? 'Plateforme opérationnelle' : 'Attention requise'
}

export function buildDetectionSignals(input: {
  connected: boolean
  orgName: string
  orgOk: boolean
  unreadNotifications: number
  syncOk: boolean
  lastProductId: string | null
}): HomeSignal[] {
  const signals: HomeSignal[] = []

  if (!input.connected) {
    signals.push({
      id: 'auth',
      label: 'Session non authentifiée',
      tone: 'attention',
      href: '/login',
    })
  }

  if (input.connected && !input.orgOk) {
    signals.push({
      id: 'org',
      label: 'Aucune organisation active',
      tone: 'attention',
      href: '/platform/organization',
    })
  }

  if (input.connected && input.orgOk && !input.syncOk) {
    signals.push({
      id: 'sync',
      label: 'Synchronisation en attente',
      tone: 'attention',
    })
  }

  if (input.unreadNotifications > 0) {
    signals.push({
      id: 'notifs',
      label:
        input.unreadNotifications === 1
          ? '1 notification non lue'
          : `${input.unreadNotifications} notifications non lues`,
      tone: 'attention',
      href: '/notifications',
    })
  }

  if (input.connected && input.orgOk && !input.lastProductId) {
    signals.push({
      id: 'resume',
      label: 'Aucune session récente à reprendre',
      tone: 'info',
      href: '#home-continue',
    })
  }

  return signals
}

/** Éléments actionnables pour « À surveiller » (max 6). */
export function buildWatchItems(signals: HomeSignal[]): HomeWatchItem[] {
  return signals
    .filter((s) => s.tone === 'attention')
    .slice(0, 6)
    .map((s) => ({
      id: s.id,
      title: s.label,
      context: s.href ? 'Action requise' : 'État plateforme',
      href: s.href,
      tone: 'attention' as const,
    }))
}

export function buildDayDomainCards(input: {
  orgName: string
  orgRole?: string
  lastProductId: string | null
  lastProductAt: string | null
  unreadNotifications: number
}): DayDomainCard[] {
  const lastAt = formatLastSeen(input.lastProductAt)
  const lastFinance = input.lastProductId === 'comptapilot'
  const lastSales = input.lastProductId === 'salespilot'

  return [
    {
      id: 'finance',
      title: 'Finance',
      summary: lastFinance
        ? 'Dernière session dans l’espace finance.'
        : 'Aucun signal finance aujourd’hui.',
      actionLabel: lastFinance ? 'Reprendre' : 'Ouvrir',
      actionTo: '/dashboard',
      status: lastFinance ? 'Session récente' : 'Calme',
      statusTone: lastFinance ? 'ok' : 'idle',
      lastActivity: lastFinance && lastAt ? lastAt : '—',
    },
    {
      id: 'commercial',
      title: 'Commercial',
      summary: lastSales
        ? 'Dernière session dans l’espace commercial.'
        : 'Aucun signal commercial aujourd’hui.',
      actionLabel: lastSales ? 'Reprendre' : 'Ouvrir',
      actionTo: '/sales',
      status: lastSales ? 'Session récente' : 'Calme',
      statusTone: lastSales ? 'ok' : 'idle',
      lastActivity: lastSales && lastAt ? lastAt : '—',
    },
    {
      id: 'documents',
      title: 'Documents',
      summary: 'Aucun agrégat documents branché sur Home.',
      actionLabel: 'Ouvrir',
      actionTo: '/platform/documents',
      status: 'Non agrégé',
      statusTone: 'idle',
      lastActivity: '—',
    },
    {
      id: 'organisation',
      title: 'Organisation',
      summary:
        input.orgName && input.orgName !== '—'
          ? `Contexte actif : ${input.orgName}${input.orgRole ? ` · ${input.orgRole}` : ''}.`
          : 'Sélectionnez une organisation pour piloter.',
      actionLabel: 'Gérer',
      actionTo: '/platform/organization',
      status:
        input.orgName && input.orgName !== '—'
          ? input.unreadNotifications > 0
            ? 'Attention'
            : 'Active'
          : 'À configurer',
      statusTone:
        input.orgName && input.orgName !== '—'
          ? input.unreadNotifications > 0
            ? 'warn'
            : 'ok'
          : 'warn',
      lastActivity: lastAt || '—',
    },
  ]
}

export function buildHealthLamps(input: {
  connected: boolean
  orgOk: boolean
  syncOk: boolean
  syncMode?: string
  unreadKnown: boolean
}): HomeHealthLamp[] {
  const lamps: HomeHealthLamp[] = [
    {
      id: 'connection',
      label: 'Connexion',
      tone: input.connected ? 'green' : 'red',
      detail: input.connected ? 'Session active' : 'Hors ligne',
    },
    {
      id: 'org',
      label: 'Organisation',
      tone: input.orgOk ? 'green' : 'orange',
      detail: input.orgOk ? 'Contexte OK' : 'Non sélectionnée',
    },
    {
      id: 'sync',
      label: 'Synchronisation',
      tone: input.syncOk ? 'green' : 'orange',
      detail: input.syncOk
        ? input.syncMode
          ? `Active (${input.syncMode})`
          : 'Active'
        : 'En attente',
    },
  ]

  if (input.unreadKnown) {
    lamps.push({
      id: 'notifications',
      label: 'Notifications',
      tone: 'green',
      detail: 'Flux branché',
    })
  }

  return lamps
}

/**
 * Cartes « Vos espaces » — dérivées du WORKSPACE_REGISTRY.
 * Même source que le launcher Espaces.
 */
export function resolveSpaceSummaries(
  lastProductId: string | null,
  lastAt: string | null,
): HomeSpaceSummary[] {
  const stamp = formatLastSeen(lastAt)

  return WORKSPACE_REGISTRY.map((workspace) => {
    const available = workspace.availability === 'available' && Boolean(workspace.rootPath)
    const isResume =
      Boolean(lastProductId) &&
      workspace.engineProductId === lastProductId &&
      Boolean(stamp)

    return {
      id: workspace.id,
      title: workspace.label,
      summary: workspace.description,
      available,
      to: workspace.rootPath,
      poweredBy: workspace.engineLabel,
      statusLabel:
        workspace.availability === 'available'
          ? 'Disponible'
          : workspace.availability === 'locked'
            ? 'Verrouillé'
            : 'Bientôt',
      accent: workspace.accent.primary,
      productId: workspace.engineProductId,
      resumeHint: isResume ? `Reprise possible · ${stamp}` : null,
    }
  })
}

/** Relecture locale des derniers produits (sans inventer d’entités métier). */
export function readResumeContext() {
  return {
    lastId: getLastProductId(),
    lastAt: getLastProductAt(),
  }
}

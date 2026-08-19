/**
 * Command Center view-model — pure helpers, no React.
 * Routes only map to real SPA destinations.
 */

import { getProductEntryRoute } from '../app-launcher/productEntryRoutes'
import type {
  CommandModeState,
  CommandResultGroup,
  CommandResultGroupId,
  CommandResultItem,
  SearchEngineHit,
} from './commandTypes'

export const GROUP_LABELS: Readonly<Record<CommandResultGroupId, string>> = {
  applications: 'Applications',
  navigation: 'Navigation',
  clients: 'Clients',
  documents: 'Documents',
  factures: 'Factures',
  prospects: 'Prospects',
  opportunites: 'Opportunités',
  quick_actions: 'Commandes rapides',
  commands: 'Commandes',
}

const GROUP_ORDER: readonly CommandResultGroupId[] = [
  'commands',
  'quick_actions',
  'applications',
  'navigation',
  'clients',
  'documents',
  'factures',
  'prospects',
  'opportunites',
]

/** Static applications with real entry routes only. */
export function getApplicationItems(): CommandResultItem[] {
  const items: CommandResultItem[] = []
  const compta = getProductEntryRoute('comptapilot')
  if (compta) {
    items.push({
      id: 'app:comptapilot',
      kind: 'application',
      group: 'applications',
      title: 'ComptaPilot',
      subtitle: 'Ouvrir ComptaPilot',
      href: compta,
      keywords: ['compta', 'comptapilot', 'finance', 'comptable'],
    })
  }
  const sales = getProductEntryRoute('salespilot')
  if (sales) {
    items.push({
      id: 'app:salespilot',
      kind: 'application',
      group: 'applications',
      title: 'SalesPilot',
      subtitle: 'Ouvrir SalesPilot',
      href: sales,
      keywords: ['sales', 'salespilot', 'crm', 'commercial'],
    })
  }
  return items
}

export function getNavigationItems(): CommandResultItem[] {
  return [
    {
      id: 'nav:home',
      kind: 'navigation',
      group: 'navigation',
      title: 'Accueil',
      subtitle: '/home',
      href: '/home',
      keywords: ['accueil', 'home', 'elfis'],
    },
    {
      id: 'nav:settings',
      kind: 'navigation',
      group: 'navigation',
      title: 'Paramètres Core',
      subtitle: '/platform/settings',
      href: '/platform/settings',
      keywords: ['paramètres', 'settings', 'configuration', 'core'],
    },
    {
      id: 'nav:org',
      kind: 'navigation',
      group: 'navigation',
      title: 'Organisation',
      subtitle: '/platform/organization',
      href: '/platform/organization',
      keywords: ['organisation', 'org', 'entreprise'],
    },
    {
      id: 'nav:members',
      kind: 'navigation',
      group: 'navigation',
      title: 'Équipe & membres',
      subtitle: '/platform/members',
      href: '/platform/members',
      keywords: ['équipe', 'membres', 'team', 'users'],
    },
    {
      id: 'nav:documents',
      kind: 'navigation',
      group: 'navigation',
      title: 'Documents ELFIS',
      subtitle: '/platform/documents',
      href: '/platform/documents',
      keywords: ['documents', 'vault', 'pdf'],
    },
    {
      id: 'nav:communications',
      kind: 'navigation',
      group: 'navigation',
      title: 'Communications',
      subtitle: '/platform/communications',
      href: '/platform/communications',
      keywords: ['communications', 'email', 'e-mail', 'brevo', 'smtp'],
    },
    {
      id: 'nav:aura',
      kind: 'navigation',
      group: 'navigation',
      title: 'Aura',
      subtitle: '/platform/aura',
      href: '/platform/aura',
      keywords: ['aura', 'assistant', 'ia', 'ai'],
    },
    {
      id: 'nav:relations',
      kind: 'navigation',
      group: 'navigation',
      title: 'Relations ELFIS',
      subtitle: '/platform/relations',
      href: '/platform/relations',
      keywords: ['relations', 'clients', 'fournisseurs', 'contacts', 'rechercher relation'],
    },
    {
      id: 'nav:relations-customers',
      kind: 'navigation',
      group: 'navigation',
      title: 'Clients ELFIS',
      subtitle: '/platform/relations?tab=customer',
      href: '/platform/relations?tab=customer',
      keywords: ['clients elfis', 'relations clients'],
    },
    {
      id: 'nav:relations-suppliers',
      kind: 'navigation',
      group: 'navigation',
      title: 'Fournisseurs ELFIS',
      subtitle: '/platform/relations?tab=supplier',
      href: '/platform/relations?tab=supplier',
      keywords: ['fournisseurs elfis', 'relations fournisseurs'],
    },
    {
      id: 'nav:clients-compta',
      kind: 'navigation',
      group: 'navigation',
      title: 'Clients ComptaPilot',
      subtitle: '/clients',
      href: '/clients',
      keywords: ['clients', 'compta', 'customer'],
    },
    {
      id: 'nav:clients-sales',
      kind: 'navigation',
      group: 'navigation',
      title: 'Entreprises SalesPilot',
      subtitle: '/sales/companies',
      href: '/sales/companies',
      keywords: ['entreprises', 'sales', 'accounts'],
    },
  ]
}

/** Keyword → local quick actions (existing routes only). */
export const QUICK_ACTION_CATALOG: readonly CommandResultItem[] = [
  {
    id: 'qa:nouvelle-facture',
    kind: 'quick_action',
    group: 'quick_actions',
    title: 'Nouvelle facture',
    subtitle: 'Facturation',
    href: '/facturation/nouveau?type=facture',
    keywords: ['facture', 'facturation', 'invoice', 'nouvelle'],
  },
  {
    id: 'qa:factures',
    kind: 'quick_action',
    group: 'quick_actions',
    title: 'Factures',
    subtitle: 'Liste facturation',
    href: '/facturation/documents',
    keywords: ['facture', 'factures', 'facturation'],
  },
  {
    id: 'qa:importer-facture',
    kind: 'quick_action',
    group: 'quick_actions',
    title: 'Importer une facture',
    subtitle: 'Dépôt document',
    href: '/deposit',
    keywords: ['facture', 'importer', 'import', 'dépôt', 'deposit'],
  },
  {
    id: 'qa:nouveau-client',
    kind: 'quick_action',
    group: 'quick_actions',
    title: 'Nouveau client',
    subtitle: 'Clients',
    href: '/clients',
    keywords: ['client', 'clients', 'nouveau', 'customer'],
  },
  {
    id: 'qa:tous-clients',
    kind: 'quick_action',
    group: 'quick_actions',
    title: 'Tous les clients',
    subtitle: 'Clients',
    href: '/clients',
    keywords: ['client', 'clients', 'tous', 'customer'],
  },
  {
    id: 'qa:ouvrir-sales',
    kind: 'quick_action',
    group: 'quick_actions',
    title: 'Ouvrir SalesPilot',
    subtitle: '/sales',
    href: '/sales',
    keywords: ['sales', 'salespilot', 'crm', 'commercial'],
  },
]

/** Command mode (`>`) — navigate only. */
export const COMMAND_CATALOG: readonly CommandResultItem[] = [
  {
    id: 'cmd:nouvelle-facture',
    kind: 'command',
    group: 'commands',
    title: 'Nouvelle facture',
    subtitle: '> nouvelle facture',
    href: '/facturation/nouveau?type=facture',
    keywords: ['nouvelle facture', 'facture', 'new invoice'],
  },
  {
    id: 'cmd:ouvrir-sales',
    kind: 'command',
    group: 'commands',
    title: 'Ouvrir SalesPilot',
    subtitle: '> ouvrir salespilot',
    href: '/sales',
    keywords: ['ouvrir salespilot', 'salespilot', 'sales', 'ouvrir sales'],
  },
  {
    id: 'cmd:ouvrir-compta',
    kind: 'command',
    group: 'commands',
    title: 'Ouvrir ComptaPilot',
    subtitle: '> ouvrir comptapilot',
    href: '/dashboard',
    keywords: ['ouvrir comptapilot', 'comptapilot', 'compta', 'ouvrir compta'],
  },
  {
    id: 'cmd:importer-document',
    kind: 'command',
    group: 'commands',
    title: 'Importer un document',
    subtitle: '> importer document',
    href: '/deposit',
    keywords: ['importer document', 'importer', 'import', 'dépôt', 'deposit'],
  },
]

export function parseCommandMode(raw: string): CommandModeState {
  const trimmed = raw.trimStart()
  if (!trimmed.startsWith('>')) {
    return { active: false, commandText: '' }
  }
  return { active: true, commandText: trimmed.slice(1).trimStart() }
}

function matchesQuery(item: CommandResultItem, q: string): boolean {
  if (!q) return true
  const hay = [item.title, item.subtitle ?? '', ...(item.keywords ?? [])].join(' ').toLowerCase()
  const tokens = q.toLowerCase().split(/\s+/).filter(Boolean)
  return tokens.every((t) => hay.includes(t))
}

export function filterQuickActions(query: string): CommandResultItem[] {
  const q = query.trim().toLowerCase()
  if (!q) return []
  /* Keyword trigger: show actions whose keywords overlap the query tokens or title */
  const tokens = q.split(/\s+/).filter(Boolean)
  return QUICK_ACTION_CATALOG.filter((item) => {
    const keys = (item.keywords ?? []).map((k) => k.toLowerCase())
    return tokens.some((t) => keys.some((k) => k.includes(t) || t.includes(k))) || matchesQuery(item, q)
  })
}

export function filterCommands(commandText: string): CommandResultItem[] {
  const q = commandText.trim().toLowerCase()
  if (!q) return [...COMMAND_CATALOG]
  return COMMAND_CATALOG.filter((item) => matchesQuery(item, q))
}

export function filterLocalItems(items: CommandResultItem[], query: string): CommandResultItem[] {
  const q = query.trim()
  if (!q) return items
  return items.filter((item) => matchesQuery(item, q))
}

/** Map Search Engine V1 resource_type → Command Center group. */
export function groupIdForResourceType(resourceType: string): CommandResultGroupId | null {
  switch (resourceType) {
    case 'customer':
    case 'supplier':
      return 'clients'
    case 'vault_document':
    case 'document_analysis':
    case 'document_text_extraction':
      return 'documents'
    case 'accounting_proposal':
    case 'accounting_entry':
      return 'factures'
    default:
      return 'documents'
  }
}

const TYPE_LABEL: Record<string, string> = {
  vault_document: 'Document',
  document_analysis: 'Analyse',
  document_text_extraction: 'Extraction',
  accounting_proposal: 'Écriture',
  accounting_entry: 'Journal',
  customer: 'Client',
  supplier: 'Fournisseur',
}

export function searchHitToItem(hit: SearchEngineHit): CommandResultItem | null {
  const group = groupIdForResourceType(hit.resource_type)
  if (!group) return null
  const href =
    (hit.action_url && hit.action_url.startsWith('/') ? hit.action_url : null) ||
    `/search?q=${encodeURIComponent(hit.title)}`
  const typeLabel = TYPE_LABEL[hit.resource_type] || hit.resource_type
  return {
    id: `search:${hit.search_document_id}`,
    kind: 'search',
    group,
    title: hit.title,
    subtitle: hit.subtitle || hit.snippet || typeLabel,
    href,
    resourceType: hit.resource_type,
  }
}

export function buildResultGroups(params: {
  query: string
  commandMode: CommandModeState
  searchHits: SearchEngineHit[]
}): CommandResultGroup[] {
  const { query, commandMode, searchHits } = params

  if (commandMode.active) {
    const commands = filterCommands(commandMode.commandText)
    if (commands.length === 0) return []
    return [{ id: 'commands', label: GROUP_LABELS.commands, items: commands }]
  }

  const q = query.trim()
  const apps = filterLocalItems(getApplicationItems(), q)
  const nav = filterLocalItems(getNavigationItems(), q)
  const quick = q ? filterQuickActions(q) : []

  const searchItems = searchHits
    .map(searchHitToItem)
    .filter((x): x is CommandResultItem => Boolean(x))

  const byGroup = new Map<CommandResultGroupId, CommandResultItem[]>()
  const push = (item: CommandResultItem) => {
    const list = byGroup.get(item.group) ?? []
    list.push(item)
    byGroup.set(item.group, list)
  }

  apps.forEach(push)
  nav.forEach(push)
  quick.forEach(push)
  searchItems.forEach(push)

  /* Idle: show apps + nav as starting points */
  if (!q) {
    const idle: CommandResultGroup[] = []
    for (const id of ['applications', 'navigation'] as const) {
      const items = byGroup.get(id) ?? []
      if (items.length) idle.push({ id, label: GROUP_LABELS[id], items })
    }
    return idle
  }

  const out: CommandResultGroup[] = []
  for (const id of GROUP_ORDER) {
    const items = byGroup.get(id) ?? []
    if (items.length) out.push({ id, label: GROUP_LABELS[id], items })
  }
  return out
}

export function flattenGroups(groups: CommandResultGroup[]): CommandResultItem[] {
  return groups.flatMap((g) => g.items)
}

export function searchPageHref(query: string): string {
  const q = query.trim()
  return q ? `/search?q=${encodeURIComponent(q)}` : '/search'
}

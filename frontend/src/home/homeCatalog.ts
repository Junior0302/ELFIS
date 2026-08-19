export type HomeAppCard = {
  id: string
  productId?: 'comptapilot' | 'salespilot' | 'docpilot' | 'hrpilot' | 'supportpilot'
  name: string
  description: string
  capabilities: readonly [string, string, string]
  to: string | null
  available: boolean
  accent: string
  statusLabel: string
}

/** Cartes Home — curated, pas de logique métier. */
export const HOME_APP_CARDS: HomeAppCard[] = [
  {
    id: 'comptapilot',
    productId: 'comptapilot',
    name: 'ComptaPilot',
    description: 'Finance, facturation et pilotage comptable.',
    capabilities: ['Facturation', 'Banque', 'Clôture'],
    to: '/dashboard',
    available: true,
    accent: '#0B3D2E',
    statusLabel: 'Disponible',
  },
  {
    id: 'salespilot',
    productId: 'salespilot',
    name: 'SalesPilot',
    description: 'Pipeline, CRM et opportunités commerciales.',
    capabilities: ['Pipeline', 'CRM', 'Propositions'],
    to: '/sales',
    available: true,
    accent: '#1D4ED8',
    statusLabel: 'Disponible',
  },
  {
    id: 'docpilot',
    productId: 'docpilot',
    name: 'DocPilot',
    description: 'Documents et flux documentaires.',
    capabilities: ['Coffre', 'OCR', 'Recherche'],
    to: null,
    available: false,
    accent: '#C2410C',
    statusLabel: 'Bientôt disponible',
  },
  {
    id: 'hrpilot',
    productId: 'hrpilot',
    name: 'HRPilot',
    description: 'Équipes, congés et processus RH.',
    capabilities: ['Équipes', 'Congés', 'Onboarding'],
    to: null,
    available: false,
    accent: '#6D28D9',
    statusLabel: 'Bientôt disponible',
  },
  {
    id: 'analyticspilot',
    name: 'AnalyticsPilot',
    description: 'Tableaux de bord et insights transverses.',
    capabilities: ['KPI', 'Rapports', 'Alertes'],
    to: null,
    available: false,
    accent: '#0E7490',
    statusLabel: 'Bientôt disponible',
  },
  {
    id: 'supportpilot',
    productId: 'supportpilot',
    name: 'SupportPilot',
    description: 'Tickets et relation client.',
    capabilities: ['Tickets', 'SLA', 'Base de savoir'],
    to: null,
    available: false,
    accent: '#3730A3',
    statusLabel: 'Bientôt disponible',
  },
]

export type HomeTimelineItem = {
  id: string
  title: string
  detail: string
  at: string
  day: 'today' | 'yesterday'
}

export const HOME_TIMELINE_MOCK: HomeTimelineItem[] = [
  { id: 'a1', title: 'Paiement reçu', detail: 'Règlement F-2026-0138 · ComptaPilot', at: 'Il y a 8 min', day: 'today' },
  { id: 'a2', title: 'Facture créée', detail: 'F-2026-0142 · ComptaPilot', at: 'Il y a 12 min', day: 'today' },
  { id: 'a3', title: 'Prospect gagné', detail: 'Opportunité Q3 · SalesPilot', at: 'Il y a 1 h', day: 'today' },
  { id: 'a4', title: 'Document importé', detail: 'contrat.pdf · DocPilot', at: 'Hier, 18:20', day: 'yesterday' },
  { id: 'a5', title: 'Client ajouté', detail: 'Acme SAS · SalesPilot', at: 'Hier, 14:05', day: 'yesterday' },
]

export type HomeNotifMock = {
  id: string
  title: string
  body: string
  at: string
  product: string
  type: 'info' | 'success' | 'system' | 'security'
}

export const HOME_NOTIF_MOCK: HomeNotifMock[] = [
  {
    id: 'n1',
    title: 'Bienvenue sur ELFIS Home',
    body: 'Choisissez une application pour commencer.',
    at: 'Maintenant',
    product: 'ELFIS Core',
    type: 'info',
  },
  {
    id: 'n2',
    title: 'Organisation synchronisée',
    body: 'Vos workspaces sont à jour.',
    at: 'Il y a 5 min',
    product: 'ELFIS Core',
    type: 'success',
  },
  {
    id: 'n3',
    title: 'SalesPilot disponible',
    body: 'Reprenez votre pipeline quand vous voulez.',
    at: 'Il y a 2 h',
    product: 'SalesPilot',
    type: 'info',
  },
  {
    id: 'n4',
    title: 'Rappel abonnement',
    body: 'Votre essai se poursuit normalement.',
    at: 'Hier',
    product: 'ELFIS Core',
    type: 'system',
  },
  {
    id: 'n5',
    title: 'Sécurité',
    body: 'Connexion réussie depuis un nouvel appareil (aperçu).',
    at: 'Hier',
    product: 'ELFIS Core',
    type: 'security',
  },
]

/** @deprecated use HOME_TIMELINE_MOCK */
export const HOME_ACTIVITY_MOCK = HOME_TIMELINE_MOCK.map((item) => ({
  id: item.id,
  title: item.title,
  detail: item.detail,
  at: item.at,
}))

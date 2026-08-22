/**
 * Espaces roadmap (launcher « À venir ») — maquette Lucide.
 */

import { WORKSPACE_ACCENTS } from './accents'
import type { WorkspaceConfig } from './types'

function soon(
  partial: Omit<WorkspaceConfig, 'availability' | 'rootPath' | 'shortcuts' | 'navigationGroups'>,
): WorkspaceConfig {
  return {
    ...partial,
    rootPath: null,
    availability: 'coming_soon',
    shortcuts: [],
    navigationGroups: [],
  }
}

export const achatsWorkspaceConfig = soon({
  id: 'achats',
  label: 'Achats',
  description: 'Gestion des achats et fournisseurs.',
  engineLabel: null,
  engineProductId: null,
  icon: 'shopping-cart',
  accent: WORKSPACE_ACCENTS.achats,
  searchAliases: ['achat', 'achats', 'fournisseur', 'fournisseurs', 'commande', 'approvisionnement'],
  capabilities: ['Commandes', 'Fournisseurs', 'Réceptions'],
})

export const stockWorkspaceConfig = soon({
  id: 'stock',
  label: 'Stock & Inventaire',
  description: 'Suivi des stocks et inventaires.',
  engineLabel: null,
  engineProductId: null,
  icon: 'box',
  accent: WORKSPACE_ACCENTS.stock,
  searchAliases: ['stock', 'inventaire', 'entrepôt', 'article', 'articles', 'référence'],
  capabilities: ['Stocks', 'Inventaires', 'Mouvements'],
})

export const logistiqueWorkspaceConfig = soon({
  id: 'logistique',
  label: 'Logistique',
  description: 'Expéditions et livraisons.',
  engineLabel: null,
  engineProductId: null,
  icon: 'truck',
  accent: WORKSPACE_ACCENTS.logistique,
  searchAliases: ['logistique', 'livraison', 'livraisons', 'expédition', 'transport', 'colis'],
  capabilities: ['Expéditions', 'Livraisons', 'Suivi'],
})

export const rhWorkspaceConfig = soon({
  id: 'rh',
  label: 'Ressources Humaines',
  description: 'Gestion des équipes et talents.',
  engineLabel: null,
  engineProductId: 'hrpilot',
  icon: 'user-circle',
  accent: WORKSPACE_ACCENTS.rh,
  searchAliases: ['rh', 'hr', 'équipe', 'équipes', 'congés', 'onboarding', 'collaborateur', 'talents'],
  capabilities: ['Équipes', 'Congés', 'Onboarding'],
})

export const planningWorkspaceConfig = soon({
  id: 'planning',
  label: 'Planning',
  description: 'Planification et organisation.',
  engineLabel: null,
  engineProductId: null,
  icon: 'calendar',
  accent: WORKSPACE_ACCENTS.planning,
  searchAliases: ['planning', 'agenda', 'calendrier', 'organisation', 'créneau', 'ressource'],
  capabilities: ['Agenda', 'Créneaux', 'Organisation'],
})

export const projetsWorkspaceConfig = soon({
  id: 'projets',
  label: 'Projets',
  description: 'Suivi des projets et tâches.',
  engineLabel: null,
  engineProductId: null,
  icon: 'pie-chart',
  accent: WORKSPACE_ACCENTS.projets,
  searchAliases: ['projet', 'projets', 'tâche', 'tâches', 'jalon', 'jalons', 'gantt'],
  capabilities: ['Projets', 'Tâches', 'Jalons'],
})

export const banqueWorkspaceConfig = soon({
  id: 'banque',
  label: 'Banque',
  description: 'Relevés et synchronisation.',
  engineLabel: null,
  engineProductId: null,
  icon: 'landmark',
  accent: WORKSPACE_ACCENTS.banque,
  searchAliases: ['banque', 'relevé', 'relevés', 'synchronisation', 'compte', 'virement'],
  capabilities: ['Relevés', 'Synchronisation', 'Comptes'],
})

export const comptabiliteWorkspaceConfig = soon({
  id: 'comptabilite',
  label: 'Comptabilité',
  description: 'Écritures et clôtures.',
  engineLabel: null,
  engineProductId: null,
  icon: 'calculator',
  accent: WORKSPACE_ACCENTS.comptabilite,
  searchAliases: ['comptabilité', 'écriture', 'écritures', 'clôture', 'bilan', 'journal'],
  capabilities: ['Écritures', 'Clôtures', 'Bilan'],
})

export const facturationWorkspaceConfig = soon({
  id: 'facturation',
  label: 'Facturation',
  description: 'Devis, factures et paiements.',
  engineLabel: null,
  engineProductId: null,
  icon: 'receipt',
  accent: WORKSPACE_ACCENTS.facturation,
  searchAliases: ['facture', 'facturation', 'devis', 'paiement', 'paiements', 'avoir'],
  capabilities: ['Devis', 'Factures', 'Paiements'],
})

export const conformiteWorkspaceConfig = soon({
  id: 'conformite',
  label: 'Conformité',
  description: 'RGPD, sécurité et audit.',
  engineLabel: null,
  engineProductId: null,
  icon: 'shield',
  accent: WORKSPACE_ACCENTS.conformite,
  searchAliases: ['conformité', 'rgpd', 'audit', 'sécurité', 'contrôle', 'compliance'],
  capabilities: ['RGPD', 'Audit', 'Sécurité'],
})

export const rseWorkspaceConfig = soon({
  id: 'rse',
  label: 'RSE',
  description: 'Responsabilité sociétale et environnementale.',
  engineLabel: null,
  engineProductId: null,
  icon: 'leaf',
  accent: WORKSPACE_ACCENTS.rse,
  searchAliases: ['rse', 'environnement', 'carbone', 'durable', 'esg', 'impact'],
  capabilities: ['Impact', 'ESG', 'Reporting'],
})

export const parametresWorkspaceConfig = soon({
  id: 'parametres',
  label: 'Paramètres',
  description: 'Configuration et préférences.',
  engineLabel: null,
  engineProductId: null,
  icon: 'settings',
  accent: WORKSPACE_ACCENTS.parametres,
  searchAliases: ['paramètre', 'paramètres', 'configuration', 'préférences', 'réglages'],
  capabilities: ['Configuration', 'Préférences', 'Profil'],
})

/** Miroir frontend de backend/app/services/plan_features.py — source de vérité = API /auth/plan-catalog */

export const PLAN_FEATURES: Record<string, string[]> = {
  starter: ['document_analysis', 'basic_exports', 'basic_invoicing'],
  pro: [
    'document_analysis',
    'advanced_analysis',
    'team_members',
    'advanced_exports',
    'supplier_intelligence',
    'basic_invoicing',
    'basic_exports',
    'intelligence_dashboard',
    'elfis_chat',
  ],
  business: [
    'document_analysis',
    'advanced_analysis',
    'team_members',
    'multi_user_permissions',
    'advanced_exports',
    'supplier_intelligence',
    'basic_invoicing',
    'basic_exports',
    'intelligence_dashboard',
    'elfis_chat',
  ],
}

export const PLAN_SEAT_LIMITS: Record<string, number> = {
  starter: 1,
  pro: 5,
  business: 25,
}

export const FEATURE_LABELS_FR: Record<string, string> = {
  document_analysis: 'Analyse de documents',
  basic_exports: 'Exports de base',
  basic_invoicing: 'Facturation de base',
  advanced_analysis: 'Analyse avancée',
  team_members: 'Équipe multi-utilisateurs',
  advanced_exports: 'Exports avancés',
  supplier_intelligence: 'Intelligence fournisseurs',
  multi_user_permissions: 'Permissions avancées',
  intelligence_dashboard: 'Tableau Intelligence',
  elfis_chat: 'Chat ELFIS',
}

/** Libellés rôles — alias vers rôles globaux ELFIS (BRAND.ELFIS.2). */
export { GLOBAL_ROLE_LABELS_FR as ROLE_LABELS_FR } from './platform-roles/globalRoles'

export function planIncludesFeature(plan: string | undefined, feature: string) {
  const key = (plan || 'starter').toLowerCase()
  return (PLAN_FEATURES[key] || PLAN_FEATURES.starter).includes(feature)
}

/** Concept 6 — « Prêt. Compris. Un clic. » — première impression. */

export const TRIAL_LOCK_MESSAGE = 'Disponible après activation de votre essai.'

export const TRIAL_ONBOARDING_ALLOWED_PATHS = [
  '/dashboard',
  '/welcome',
  '/abonnement',
  '/compte',
  '/modules',
] as const

export function isPathAllowedDuringTrialOnboarding(pathname: string): boolean {
  return TRIAL_ONBOARDING_ALLOWED_PATHS.some(
    (p) => pathname === p || pathname.startsWith(`${p}/`),
  )
}

/** 3 bénéfices dirigeants — plus grands, plus respirants (landing). */
export const TRIAL_ONBOARDING_BENEFITS = [
  {
    id: 'pilotage',
    icon: '📈',
    title: 'Sachez combien vous gagnez réellement',
    text: 'Des chiffres clairs pour décider sans tableur — trésorerie, CA et alertes en un regard.',
  },
  {
    id: 'copilote',
    icon: '🤖',
    title: 'Votre Copilote IA',
    text: 'Posez vos questions en langage simple. Obtenez des réponses appuyées sur vos données.',
  },
  {
    id: 'automatisation',
    icon: '⚡',
    title: 'Banque et documents, sans ressaisie',
    text: 'Opérations bancaires synchronisées et factures préparées — vous gardez le contrôle.',
  },
] as const

export const TRIAL_ONBOARDING_STEPS = [
  { id: 1, label: 'Activer mon essai', key: 'trial' },
  { id: 2, label: 'Compléter mon entreprise', key: 'company' },
  { id: 3, label: 'Importer une facture', key: 'invoice' },
  { id: 4, label: 'Connecter ma banque', key: 'bank' },
  { id: 5, label: 'Découvrir mon tableau de bord', key: 'dashboard' },
] as const

export const TRIAL_TRUST_ITEMS = [
  { id: 'eu', icon: '🇪🇺', label: 'Hébergement sécurisé en Europe' },
  { id: 'rgpd', icon: '🛡️', label: 'Conforme RGPD' },
  { id: 'expert', icon: '🎓', label: 'Compatible expert-comptable' },
  { id: 'ai', icon: '✦', label: 'IA explicable' },
  { id: 'backup', icon: '💾', label: 'Sauvegarde automatique' },
] as const

export const TRIAL_DISCOVERY_SLIDES = [
  {
    title: 'Comprendre vos chiffres',
    text: 'Trésorerie, revenus et alertes — expliqués simplement.',
  },
  {
    title: 'Un Copilote à vos côtés',
    text: 'Posez une question : la réponse s’appuie sur vos données.',
  },
  {
    title: 'Gagner du temps dès le premier jour',
    text: 'Factures et banque se synchronisent. Vous gardez le contrôle.',
  },
] as const

/** Aperçu illustratif — pas un vrai dashboard. */
export const TRIAL_PREVIEW_SAMPLE = {
  healthScore: 82,
  healthGrade: 'A',
  treasury: '24 800 €',
  revenue: '12 450 €',
  unpaid: '1 200 €',
  alert: '2 factures à relancer cette semaine',
  copilote: 'Pourquoi ma trésorerie a baissé ce mois-ci ?',
} as const

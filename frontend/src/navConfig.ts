export type NavItem = {
  to: string
  label: string
  /** Sous-titre court dans la barre latérale */
  hint: string
  /** Salutation vocale courte (style Jarvis/Siri) pour l'onglet */
  spokenIntro: string
  /** Guide détaillé (4 phrases) affiché en tête de page */
  guide: [string, string, string, string]
  /** Guide alternatif quand l’utilisateur n’a pas d’accès produit (ex. sans abonnement) */
  guideLocked?: [string, string, string, string]
  spokenIntroLocked?: string
  permission?: string
}

export type NavSection = { title: string; items: NavItem[] }

/** Navigation Phase 1 — toutes les pages intégrées accessibles. */
export const navSections: NavSection[] = [
  {
    title: 'Principal',
    items: [
      {
        to: '/dashboard',
        label: 'Accueil',
        hint: 'Tableau de bord',
        spokenIntro: 'Bienvenue. Voici votre tableau de bord.',
        spokenIntroLocked:
          'Bienvenue. Activez d’abord votre essai gratuit pour ouvrir le tableau de bord.',
        permission: 'invoice.read',
        guide: [
          'Vue d’accueil synthétique : KPIs, Health Score, alertes et sync bancaire.',
          'Les chiffres viennent du Financial Engine (/api/financial/overview).',
          'Accès rapides vers Finance, Banque, Copilote, Facturation et Dépôt.',
          'L’analyse détaillée reste sur /finance — ici, synthèse et priorités.',
        ],
        guideLocked: [
          'Commencez par démarrer votre essai gratuit de 14 jours.',
          'Ensuite, connectez votre banque et créez votre première facture.',
          'Le Copilote IA et le tableau financier s’ouvrent après activation.',
          'Ouvrez Abonnement pour lancer l’essai en quelques clics.',
        ],
      },
      {
        to: '/work-queue',
        label: 'À traiter',
        hint: 'Boîte de travail',
        spokenIntro: 'Boîte de travail. Voici ce qui demande votre attention.',
        permission: 'invoice.read',
        guide: [
          'Organisez les décisions à traiter, en cours, en attente et terminées.',
          'Les volumes et priorités viennent du Work Queue backend.',
          'Ouvrez un élément pour comprendre la cause et agir via le Decision Center.',
          'Le détail reste sur /decisions/{id} pour l’exécution sensible.',
        ],
      },
      {
        to: '/finance',
        label: 'Finance',
        hint: 'Dashboard financier',
        spokenIntro: 'Tableau de bord financier. KPIs, alertes et santé.',
        permission: 'invoice.read',
        guide: [
          'KPIs, tendances, graphiques, alertes et Health Score en temps réel.',
          'Tous les calculs viennent du Financial Engine — le frontend n’en fait aucun.',
          'Exemple : suivez trésorerie, CA, dépenses et TVA estimée.',
          'Actualisation automatique : les indicateurs restent à jour.',
        ],
      },
      {
        to: '/documents',
        label: 'Documents',
        hint: 'Centre documentaire',
        spokenIntro: 'Centre Documents. Liste, filtres et aperçu Vault.',
        permission: 'documents.read',
        guide: [
          'Listez, filtrez et consultez vos PDF archivés.',
          'Accédez ensuite à l’analyse, la validation et la comptabilité.',
          'Exemple : ouvrez un PDF, vérifiez le statut, lancez une proposition.',
          'Toutes les actions appellent les API Vault / documents existantes.',
        ],
      },
      {
        to: '/migration',
        label: 'Centre d’import',
        hint: 'Wizard & imports',
        spokenIntro: 'Centre d’import. Sessions, progression et rapports.',
        permission: 'migration_center.read',
        guide: [
          'Créez ou reprenez une session de migration.',
          'Wizard, batchs et rapports : 100 % API, aucune logique locale.',
          'Exemple : migration Excel initiale reprise le lendemain.',
          'Surveillez la progression et l’ETA depuis le tableau de bord migration.',
        ],
      },
      {
        to: '/accounting',
        label: 'Comptabilité',
        hint: 'Propositions & historique',
        spokenIntro: 'Section Comptabilité. Propositions, moteur et historique.',
        permission: 'ai.analysis',
        guide: [
          'Hub vers propositions V1, moteur V2 et documents traités.',
          'Aucune écriture définitive sans validation humaine.',
          'Exemple : ouvrez une proposition, contrôlez, validez.',
          'Les données viennent des endpoints accounting existants.',
        ],
      },
      {
        to: '/accounting/intelligence',
        label: 'Intelligence comptable',
        hint: 'Recommandations',
        spokenIntro: 'Intelligence comptable. Recommandations et feedback.',
        permission: 'accounting_intelligence.read',
        guide: [
          'Recommandations expliquées, score de confiance, apprentissage.',
          'Le feedback utilisateur alimente la mémoire — jamais un refus.',
          'Exemple : acceptez une reco pour mémoriser le compte.',
          'API /accounting/intelligence uniquement.',
        ],
      },
      {
        to: '/platform/banking',
        label: 'Synchronisation bancaire',
        hint: 'Connexions & synchronisation ELFIS',
        spokenIntro: 'Synchronisation bancaire ELFIS. Connexions, comptes et transactions.',
        permission: 'bank.read',
        guide: [
          'Connectez vos banques via un fournisseur interchangeable.',
          'Le Banking Engine backend reste la source de vérité.',
          'Exemple : connectez la banque démo puis synchronisez.',
          'Suivez la santé des connexions et le journal des syncs.',
        ],
      },
      {
        to: '/search',
        label: 'Recherche',
        hint: 'Recherche globale',
        spokenIntro: 'Recherche globale sur documents, clients et propositions.',
        permission: 'invoice.read',
        guide: [
          'Recherchez documents, clients, fournisseurs, propositions, rapports.',
          'Le moteur Search Engine backend reste la source de vérité.',
          'Exemple : tapez un n° de facture ou un fournisseur.',
          'Accessible aussi depuis la barre du haut.',
        ],
      },
      {
        to: '/notifications',
        label: 'Notifications',
        hint: 'Centre d’alertes',
        spokenIntro: 'Centre de notifications. Succès, erreurs, jobs et imports.',
        permission: 'invoice.read',
        guide: [
          'Succès, erreurs, imports, migrations, jobs et événements.',
          'Marquez comme lu ou archivez sans quitter l’écran.',
          'Exemple : un échec d’envoi Vault apparaît ici.',
          'Synchronisation via polling intelligent (pas de SSE backend).',
        ],
      },
      {
        to: '/reports',
        label: 'Rapports',
        hint: 'Exports & bilans',
        spokenIntro: 'Rapports. Accès aux bilans migration et exports.',
        permission: 'invoice.read',
        guide: [
          'Point d’entrée vers rapports migration, exports et pilotage.',
          'Aucun calcul local : liens vers les écrans déjà branchés API.',
          'Exemple : ouvrir le rapport d’une session de migration.',
          'Complété par l’historique comptable et le cockpit.',
        ],
      },
      {
        to: '/admin/equipe',
        label: 'Administration',
        hint: 'Équipe & droits',
        spokenIntro: 'Administration. Invitez et gérez les droits.',
        permission: 'users.manage',
        guide: [
          'Invitez des collaborateurs et définissez les permissions.',
          'Les rôles IAM backend restent la source de vérité.',
          'Exemple : un assistant crée des devis, le dirigeant gère l’abo.',
          'Abonnement et organisation restent accessibles dans Paramètres.',
        ],
      },
      {
        to: '/cockpit',
        label: 'Centre opérationnel',
        hint: 'Ops & jobs',
        spokenIntro: 'Centre opérationnel. Jobs, notifs et activité.',
        permission: 'invoice.read',
        guide: [
          'Vue ops : notifications, migrations, propositions comptables.',
          'Indicateurs financiers = Financial Engine (même source qu’Accueil / Finance).',
          'Exemple : voir les sessions actives et les alertes non lues.',
          'Les admins plateforme gardent aussi l’accès ELF Admin.',
        ],
      },
      {
        to: '/settings',
        label: 'Paramètres',
        hint: 'Comptabilité & OCR',
        spokenIntro: 'Préférences comptables. OCR, comptes et modèles d’e-mail.',
        guide: [
          'Comptes comptables, OCR, seuils de confiance.',
          'L’identité entreprise se gère dans Paramètres ELFIS / Organisation.',
          'Exemple : mettre à jour le taux de TVA par défaut.',
          'Accessible dès l’inscription.',
        ],
      },
    ],
  },
  {
    title: 'Commercial',
    items: [
      {
        to: '/deposit',
        label: 'Déposer',
        hint: 'Scan de factures',
        spokenIntro: 'Déposer une facture pour analyse.',
        permission: 'invoice.create',
        guide: [
          'Déposez une photo ou un PDF pour lancer le traitement.',
          'Flux existant inchangé — API documents / AI.',
          'Exemple : photo de fournitures puis validation.',
          'Réservé à l’abonnement ou essai actif.',
        ],
      },
      {
        to: '/facturation',
        label: 'Facturation',
        hint: 'Factures & devis',
        spokenIntro: 'Facturation commerciale.',
        permission: 'invoice.read',
        guide: [
          'Factures, devis et encaissements.',
          'Envoi via votre messagerie avec PDF joint.',
          'Exemple : créer un devis puis le convertir.',
          'Inclus dans l’essai ComptaPilot IA.',
        ],
      },
      {
        to: '/clients',
        label: 'Clients',
        hint: 'Fiches & contacts',
        spokenIntro: 'Vos clients.',
        permission: 'invoice.read',
        guide: [
          'Centralisez les fiches clients.',
          'Évite les doublons au prochain devis.',
          'Exemple : enregistrer Dupont SARL une fois.',
          'Disponible avec l’offre ComptaPilot.',
        ],
      },
      {
        to: '/catalogue',
        label: 'Catalogue',
        hint: 'Produits & services',
        spokenIntro: 'Catalogue produits.',
        permission: 'invoice.read',
        guide: [
          'Produits et services avec prix et TVA.',
          'Insertion rapide dans devis et factures.',
          'Exemple : audit mensuel 190 € HT.',
          'Inclus dans l’abonnement / essai.',
        ],
      },
      {
        to: '/activites',
        label: 'Activités',
        hint: 'Agenda commercial',
        spokenIntro: 'Agenda commercial.',
        permission: 'invoice.read',
        guide: [
          'Rendez-vous et suivis clients.',
          'Ne rien oublier au quotidien.',
          'Exemple : RDV mardi, rappel vendredi.',
          'Débloqué avec essai ou abonnement.',
        ],
      },
      {
        to: '/copilote',
        label: 'Copilote IA',
        hint: 'Assistant financier',
        spokenIntro: 'Copilote IA. Posez vos questions financières.',
        permission: 'ai.analysis',
        guide: [
          'Conversation structurée : faits, estimations, recommandations, manques.',
          'Le Decision Engine orchestre les moteurs — le LLM n’invente jamais de données.',
          'Chaque recommandation expose pourquoi, quelles données et le niveau de confiance.',
          'Donnez votre feedback (utile / inutile / incorrect) pour améliorer l’assistant.',
        ],
      },
      {
        to: '/intelligence',
        label: 'Signaux',
        hint: 'Alertes ELFIS',
        spokenIntro: 'Signaux et alertes métier.',
        permission: 'ai.analysis',
        guide: [
          'Alertes et anomalies à surveiller.',
          'Anticiper avant que ça coûte cher.',
          'Exemple : montant inhabituel.',
          'Actif avec abonnement ou essai.',
        ],
      },
      {
        to: '/abonnement',
        label: 'Abonnement',
        hint: 'Essai & facturation',
        spokenIntro: 'Gérez votre abonnement.',
        permission: 'subscription.manage',
        guide: [
          'Billing V2 : abonnement, quotas, historique, plans et paiements.',
          'L’Entitlement Engine est la source de vérité ; Stripe synchronise.',
          'Exemple : activer l’essai, suivre la consommation, changer de plan.',
          'Sans abo, le premium reste verrouillé selon les entitlements.',
        ],
      },
      {
        to: '/organisation',
        label: 'Entreprise',
        hint: 'Identité',
        spokenIntro: 'Identité de l’entreprise.',
        guide: [
          'Raison sociale, TVA, e-mails.',
          'Accessible dès l’inscription.',
          'Exemple : logo et objet de devis.',
          'Complète les Paramètres.',
        ],
      },
      {
        to: '/modules',
        label: 'Modules',
        hint: 'Catalogue produit',
        spokenIntro: 'Catalogue des modules.',
        permission: 'invoice.read',
        guide: [
          'Vue des modules produit disponibles.',
          'Navigation vers les espaces intégrés.',
          'Exemple : ouvrir Migration ou Documents.',
          'Page désormais accessible depuis la nav.',
        ],
      },
    ],
  },
]

export function findNavItem(pathname: string): NavItem | undefined {
  const normalized = pathname.replace(/\/+$/, '') || '/'
  let best: NavItem | undefined
  let bestLen = -1
  for (const section of navSections) {
    for (const item of section.items) {
      if (item.to === normalized) return item
      if (item.to !== '/dashboard' && normalized.startsWith(item.to + '/')) {
        if (item.to.length > bestLen) {
          best = item
          bestLen = item.to.length
        }
      }
    }
  }
  return best
}

export function spokenPageScript(item: NavItem): string {
  return `${item.spokenIntro} ${item.guide[0]} ${item.guide[1]}`
}

/** Routes produit attendues Phase 1 (tests). */
export const PHASE1_INTEGRATED_PATHS = [
  '/dashboard',
  '/documents',
  '/migration',
  '/accounting',
  '/accounting/proposals',
  '/accounting/engine',
  '/accounting/intelligence',
  '/search',
  '/notifications',
  '/reports',
  '/admin/equipe',
  '/cockpit',
  '/settings',
  '/history',
  '/deposit',
  '/facturation',
  '/modules',
] as const

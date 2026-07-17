export type NavItem = {
  to: string
  label: string
  /** Sous-titre court dans la barre latérale */
  hint: string
  /** Salutation vocale courte (style Jarvis/Siri) pour l'onglet */
  spokenIntro: string
  /** Guide détaillé (4 phrases) affiché en tête de page */
  guide: [string, string, string, string]
  permission?: string
}

export type NavSection = { title: string; items: NavItem[] }

export const navSections: NavSection[] = [
  {
    title: 'Pilotage',
    items: [
      {
        to: '/dashboard',
        label: 'Tableau de bord',
        hint: 'Vue d’ensemble',
        spokenIntro:
          'Bienvenue sur votre tableau de bord. Ici, vous voyez l’état de l’activité en un coup d’œil.',
        permission: 'invoice.read',
        guide: [
          'C’est votre écran d’accueil une fois connecté : vous voyez en un coup d’œil l’état de l’activité.',
          'Utile pour savoir où vous en êtes sans ouvrir chaque module (documents récents, rappels, accès rapides).',
          'Exemple : vous arrivez le matin et voyez qu’une facture attend validation, ou qu’un devis a été envoyé hier.',
          'Sans abonnement actif, cette vue vous oriente déjà vers l’essai pour débloquer l’analyse et la facturation.',
        ],
      },
      {
        to: '/intelligence',
        label: 'Intelligence',
        hint: 'Alertes & ELFIS',
        spokenIntro:
          'Voici la page Intelligence. J’y centralise les alertes et signaux qui méritent votre attention.',
        permission: 'ai.analysis',
        guide: [
          'Ici, ComptaPilot regroupe les alertes et signaux utiles pour le dirigeant (écarts, anomalies, priorités).',
          'Ça sert à anticiper un problème avant qu’il coûte cher : oubli, incohérence, document à traiter.',
          'Exemple : une facture fournisseur au montant inhabituel, ou un document en attente trop longtemps.',
          'Avec l’abonnement (ou l’essai), ces analyses deviennent actives ; sans lui, le module reste verrouillé.',
        ],
      },
      {
        to: '/copilote',
        label: 'Copilote IA',
        hint: 'Voix & conseils',
        spokenIntro:
          'Vous êtes sur le Copilote IA. Parlez-moi ou écrivez pour piloter vos chiffres.',
        permission: 'ai.analysis',
        guide: [
          'Posez une question en français — à l’écrit ou à la voix (mode Jarvis).',
          'Le copilote aide à décider rapidement sans remplacer votre expert-comptable.',
          'Exemple : appuyez sur l’orbe et dites « Quels clients sont en retard ? ».',
          'Réservé à l’offre ComptaPilot IA : démarrez l’essai depuis Abonnement pour l’utiliser.',
        ],
      },
    ],
  },
  {
    title: 'Activité',
    items: [
      {
        to: '/deposit',
        label: 'Déposer',
        hint: 'Scan de factures',
        spokenIntro:
          'Vous êtes sur Déposer. Envoyez une photo ou un PDF, je m’occupe du reste.',
        permission: 'invoice.create',
        guide: [
          'Déposez une photo ou un PDF de facture / justificatif pour lancer le traitement automatique.',
          'Ça évite de retaper les montants, dates et fournisseurs à la main.',
          'Exemple : vous photographiez une facture de fournitures et validez les infos extraites en quelques clics.',
          'Fonctionnalité premium : l’essai ou l’abonnement ouvre ce flux de dépôt.',
        ],
      },
      {
        to: '/history',
        label: 'Comptabilité',
        hint: 'Documents & exports',
        spokenIntro:
          'Bienvenue en Comptabilité. Retrouvez ici tous vos documents et exports.',
        permission: 'documents.read',
        guide: [
          'Retrouvez tous les documents déjà traités, leur statut et l’historique de travail.',
          'Utile pour retrouver une pièce, préparer un export ou suivre ce qui reste à valider.',
          'Exemple : votre comptable demande les factures de mars — vous filtrez et exportez la période.',
          'Accessible avec un abonnement actif ; sinon les données premium restent en lecture limitée.',
        ],
      },
      {
        to: '/facturation',
        label: 'Facturation',
        hint: 'Devis & clients',
        spokenIntro:
          'Vous consultez la Facturation. Devis, encaissements et suivi client sont à portée de main.',
        permission: 'invoice.read',
        guide: [
          'Point d’entrée commercial : factures émises, suivi des encaissements et liens vers devis / clients.',
          'Ça sert à encaisser plus vite et à garder une vision claire de ce qui est dû.',
          'Exemple : vous créez une facture pour un client, l’envoyez, puis suivez le paiement.',
          'Avec l’essai ComptaPilot IA, toute la chaîne devis → facture devient disponible.',
        ],
      },
      {
        to: '/devis',
        label: 'Devis',
        hint: 'Liste & envoi',
        spokenIntro:
          'Vous êtes dans les Devis. Créez, listez et envoyez vos propositions en quelques clics.',
        permission: 'invoice.read',
        guide: [
          'Créez, listez et envoyez vos devis professionnels depuis un seul endroit.',
          'Utile pour professionnaliser vos propositions et convertir plus de prospects.',
          'Exemple : devis de prestation à 1 200 € HT envoyé au client, puis transformé en facture une fois accepté.',
          'Module lié à l’abonnement : sans offre active, la création / l’envoi peuvent être bloqués.',
        ],
      },
      {
        to: '/clients',
        label: 'Clients',
        hint: 'Fiches & contacts',
        spokenIntro:
          'Voici vos Clients. Centralisez contacts et fiches pour gagner du temps au quotidien.',
        permission: 'invoice.read',
        guide: [
          'Centralisez les fiches clients : nom, email, téléphone, adresse, n° TVA.',
          'Évite les doublons et accélère la création de devis / factures.',
          'Exemple : vous enregistrez « Dupont SARL » une fois, puis le retrouvez automatiquement au prochain devis.',
          'Disponible avec l’offre ComptaPilot ; idéal dès le démarrage de l’essai.',
        ],
      },
      {
        to: '/catalogue',
        label: 'Catalogue',
        hint: 'Produits & services',
        spokenIntro:
          'Bienvenue dans le Catalogue. Vos produits et services sont prêts à insérer dans chaque document.',
        permission: 'invoice.read',
        guide: [
          'Listez vos produits et services avec prix HT, unité et taux de TVA.',
          'Vous gagnez du temps : plus besoin de retaper les mêmes lignes à chaque devis.',
          'Exemple : « Audit mensuel — 190 € HT — 20 % TVA » prêt à insérer en un clic.',
          'Catalogue commercial inclus dans l’abonnement / essai ComptaPilot IA.',
        ],
      },
      {
        to: '/activites',
        label: 'Activités',
        hint: 'Agenda commercial',
        spokenIntro:
          'Vous êtes sur Activités. Planifiez rendez-vous et suivis commerciaux sans rien oublier.',
        permission: 'invoice.read',
        guide: [
          'Planifiez rendez-vous, suivis, ventes et interventions liés à vos clients.',
          'Ça sert à ne rien oublier dans le suivi commercial du quotidien.',
          'Exemple : RDV client mardi 10 h, puis rappel « devis à relancer » vendredi.',
          'Agenda commercial débloqué avec l’essai ou l’abonnement actif.',
        ],
      },
    ],
  },
  {
    title: 'Administration',
    items: [
      {
        to: '/abonnement',
        label: 'Abonnement',
        hint: 'Essai, carte & factures',
        spokenIntro:
          'Voici Abonnement. Gérez votre essai, votre carte et le renouvellement en toute simplicité.',
        permission: 'subscription.manage',
        guide: [
          'Gérez l’essai gratuit, le renouvellement, la carte et les factures de l’organisation.',
          'C’est ici que vous démarrez les 14 jours d’essai puis le forfait à 19 € / mois.',
          'Exemple : vous activez l’essai, recevez un rappel avant prélèvement, ou mettez à jour votre carte.',
          'Sans abonnement finalisé, les modules premium restent verrouillés jusqu’à activation réussie.',
        ],
      },
      {
        to: '/organisation',
        label: 'Organisation',
        hint: 'Entreprise & coordonnées',
        spokenIntro:
          'Vous êtes sur Organisation. Renseignez l’identité de votre entreprise une seule fois.',
        guide: [
          'Renseignez l’identité de l’entreprise (nom, adresse, informations légales utiles).',
          'Ces infos alimentent vos documents et la cohérence de votre espace multi-utilisateurs.',
          'Exemple : changer la raison sociale affichée sur les devis et factures.',
          'Accessible même avant abonnement : préparez votre fiche entreprise dès l’inscription.',
        ],
      },
      {
        to: '/admin/equipe',
        label: 'Admin équipe',
        hint: 'Comptes & droits',
        spokenIntro:
          'Bienvenue dans Admin équipe. Invitez vos collaborateurs et ajustez leurs droits.',
        permission: 'users.manage',
        guide: [
          'Invitez des collaborateurs et définissez qui peut voir ou modifier quoi.',
          'Utile pour travailler à plusieurs sans partager le même mot de passe.',
          'Exemple : un assistant crée les devis, le dirigeant seul gère l’abonnement.',
          'La gestion d’équipe reste disponible ; certaines actions métier dépendent de l’abonnement.',
        ],
      },
      {
        to: '/settings',
        label: 'Paramètres',
        hint: 'Entreprise & TVA',
        spokenIntro:
          'Vous consultez les Paramètres. Réglez TVA et préférences pour des documents conformes.',
        permission: 'settings.manage',
        guide: [
          'Réglez les paramètres métier (TVA, préférences d’entreprise liées à la facturation).',
          'Ça garantit des documents corrects et conformes à votre régime.',
          'Exemple : taux de TVA par défaut à 20 %, ou coordonnées reprises sur les PDF.',
          'À configurer tôt, même pendant l’essai, pour que vos premiers documents soient justes.',
        ],
      },
      {
        to: '/compte',
        label: 'Mon compte',
        hint: 'Profil & sécurité',
        spokenIntro:
          'Voici Mon compte. Mettez à jour votre profil et sécurisez votre accès personnel.',
        guide: [
          'Modifiez votre profil personnel : nom, téléphone, photo et mot de passe.',
          'C’est votre sécurité individuelle, indépendante de l’abonnement de l’entreprise.',
          'Exemple : changer le mot de passe après un partage accidentel d’écran.',
          'Toujours accessible, avec ou sans abonnement ComptaPilot IA.',
        ],
      },
    ],
  },
]

export function findNavItem(pathname: string): NavItem | undefined {
  const normalized = pathname.replace(/\/+$/, '') || '/'
  for (const section of navSections) {
    for (const item of section.items) {
      if (item.to === normalized) return item
      if (item.to !== '/dashboard' && normalized.startsWith(item.to + '/')) return item
    }
  }
  return undefined
}

export function spokenPageScript(item: NavItem): string {
  return `${item.spokenIntro} ${item.guide[0]} ${item.guide[1]}`
}

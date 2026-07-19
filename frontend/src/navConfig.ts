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
          'C’est votre écran d’accueil : chiffre d’affaires, impayés, documents et priorités.',
          'Le bouton « Écouter le récap » lit un résumé vocal court (~10 s) — seul endroit où la voix est activée.',
          'Exemple : vous arrivez le matin, écoutez le récap, puis ouvrez le copilote en chat si besoin.',
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
        hint: 'Chat & conseils',
        spokenIntro:
          'Vous êtes sur le Copilote IA. Posez vos questions en chat pour piloter vos chiffres.',
        permission: 'ai.analysis',
        guide: [
          'Posez une question en français dans le chat — réponses basées sur vos données.',
          'Le copilote aide à décider rapidement sans remplacer votre expert-comptable.',
          'Exemple : « Quels clients sont en retard ? » ou « Résume mon activité ».',
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
        hint: 'Factures, devis, encaissements',
        spokenIntro:
          'Vous consultez la Facturation. Devis, factures et encaissements sont à portée de main.',
        permission: 'invoice.read',
        guide: [
          'Point d’entrée commercial : factures, devis, encaissements et suivi client.',
          'Pour envoyer : ouvrez le document, vérifiez le destinataire, cliquez Envoyer maintenant.',
          'Le PDF part automatiquement en pièce jointe — rien à joindre à la main.',
          'Avec l’essai ComptaPilot IA, toute la chaîne devis → facture devient disponible.',
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
    title: 'Espace',
    items: [
      {
        to: '/organisation',
        label: 'Entreprise',
        hint: 'Identité, TVA, e-mails',
        spokenIntro:
          'Vous êtes sur Entreprise. Identité, TVA et modèles d’e-mail au même endroit.',
        guide: [
          'Renseignez l’identité, la TVA, et les modèles d’objet/message pour devis et factures.',
          'L’envoi part depuis ComptaPilot avec le PDF joint automatiquement.',
          'Exemple : raison sociale, logo, objet par défaut « Devis {{quote_number}} ».',
          'Accessible dès l’inscription ; affinez pendant l’essai.',
        ],
      },
      {
        to: '/admin/equipe',
        label: 'Équipe',
        hint: 'Invitations & droits',
        spokenIntro:
          'Bienvenue dans Équipe. Invitez vos collaborateurs et ajustez leurs droits.',
        permission: 'users.manage',
        guide: [
          'Invitez des collaborateurs et définissez qui peut voir ou modifier quoi.',
          'Utile pour travailler à plusieurs sans partager le même mot de passe.',
          'Exemple : un assistant crée les devis, le dirigeant seul gère l’abonnement.',
          'La gestion d’équipe reste disponible ; certaines actions métier dépendent de l’abonnement.',
        ],
      },
      {
        to: '/abonnement',
        label: 'Abonnement',
        hint: 'Essai & facturation',
        spokenIntro:
          'Voici Abonnement. Gérez votre essai, votre carte et le renouvellement.',
        permission: 'subscription.manage',
        guide: [
          'Gérez l’essai gratuit, le renouvellement, la carte et les factures de l’organisation.',
          'C’est ici que vous démarrez les 14 jours d’essai puis le forfait à 19 € / mois.',
          'Exemple : activez l’essai ou mettez à jour votre carte.',
          'Sans abonnement finalisé, les modules premium restent verrouillés.',
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

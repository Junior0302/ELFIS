export const LANDING_NAV = {
  links: [
    { href: '#produit', label: 'Produit' },
    { href: '#espaces', label: 'Espaces' },
    { href: '#solutions', label: 'Solutions' },
    { href: '#securite', label: 'Sécurité' },
  ],
  login: 'Se connecter',
  start: 'Commencer',
  openWorkspace: 'Ouvrir mon espace',
  loginTo: '/login',
  startTo: '/register',
  homeTo: '/home',
} as const

export const LANDING_HERO = {
  eyebrow: 'ELFIS CORE',
  title: 'Le système de gestion qui relie votre entreprise.',
  lead:
    'ELFIS Core réunit progressivement les fonctions essentielles de votre activité dans un environnement unique. Finance, ventes, documents, organisation et futurs métiers de l’entreprise peuvent ainsi fonctionner autour d’une même identité, des mêmes données et d’une logique commune.',
  leadSecondary:
    'Que vous soyez indépendant, dirigeant d’une petite structure ou membre d’une organisation en croissance, ELFIS vous aide à réduire la dispersion des outils, mieux structurer votre activité et créer un environnement capable d’évoluer avec votre entreprise.',
  tagline: 'Une plateforme. Une organisation. Plusieurs expertises.',
  discover: 'Découvrir ELFIS',
  discoverHref: '#produit',
  login: 'Se connecter',
  loginTo: '/login',
  start: 'Commencer',
  startTo: '/register',
  openWorkspace: 'Ouvrir mon espace',
  openWorkspaceTo: '/home',
} as const

export const LANDING_VISUAL = {
  ariaLabel: 'ELFIS Core relie les espaces Finance, Commercial et Documents',
  chrome: 'ELFIS Core',
  chromeMeta: 'Organisation',
  coreKicker: 'Environnement central',
  coreTitle: 'Une identité. Une organisation. Plusieurs expertises.',
  coreTraits: ['Accès unique', 'Rôles', 'Données liées'] as const,
} as const

export const LANDING_PROBLEM = {
  eyebrow: 'Le problème',
  title: 'Votre entreprise ne devrait pas fonctionner comme une collection d’outils isolés.',
  paragraphs: [
    'À mesure qu’une activité grandit, les outils se multiplient. Un logiciel pour les prospects, un autre pour les factures, des documents répartis entre plusieurs espaces, des informations clients saisies plusieurs fois et des collaborateurs qui doivent constamment passer d’une application à une autre.',
    'Cette fragmentation ralentit le travail, augmente les risques d’erreur et rend plus difficile l’obtention d’une vision claire de l’entreprise.',
    'ELFIS Core a été conçu pour répondre à ce problème.',
    'Plutôt que d’ajouter un logiciel supplémentaire, ELFIS construit un environnement commun capable de relier progressivement les différents métiers de l’entreprise.',
  ],
} as const

export const LANDING_PLATFORM = {
  eyebrow: 'La plateforme',
  title: 'Une plateforme commune pour toute votre organisation.',
  lead:
    'ELFIS Core constitue le socle de votre environnement de travail. Votre organisation, vos utilisateurs, vos accès et vos différents Espaces métiers peuvent fonctionner à partir d’une architecture commune.',
  body:
    'Chaque métier conserve ses propres outils et ses propres processus, tout en restant connecté au reste de l’entreprise. L’objectif est simple : permettre à vos équipes de travailler dans des environnements spécialisés sans recréer une nouvelle organisation à chaque changement d’outil.',
  principles: [
    'Une seule identité.',
    'Une seule organisation.',
    'Des Espaces spécialisés.',
    'Des informations qui peuvent circuler lorsque cela est nécessaire.',
  ],
} as const

export const LANDING_IDENTITY = {
  title: 'Une seule connexion pour retrouver votre environnement.',
  paragraphs: [
    'Avec ELFIS, un utilisateur n’a pas vocation à gérer une multitude de comptes pour accéder aux différents métiers de son entreprise.',
    'Une identité ELFIS permet de retrouver les Espaces auxquels l’organisation autorise l’accès et de passer d’un environnement à un autre sans perdre le contexte de travail.',
    'Moins de friction pour les utilisateurs, davantage de cohérence pour l’entreprise.',
  ],
} as const

export const LANDING_PERMISSIONS = {
  title: 'Chaque collaborateur accède à ce dont il a réellement besoin.',
  paragraphs: [
    'Toutes les personnes d’une organisation n’ont pas les mêmes responsabilités.',
    'ELFIS permet de structurer les accès autour des utilisateurs, des rôles et des permissions afin que chacun puisse travailler avec les outils correspondant à sa fonction.',
    'L’objectif est d’offrir un environnement simple pour l’utilisateur tout en conservant une maîtrise claire des responsabilités au niveau de l’entreprise.',
  ],
} as const

export const LANDING_SPACES = {
  eyebrow: 'Espaces métiers',
  title: 'Chaque métier possède son espace. Votre entreprise conserve sa cohérence.',
  lead:
    'ELFIS repose sur des Espaces métiers spécialisés. Chaque Espace rassemble les fonctionnalités, informations et workflows nécessaires à un domaine précis de l’entreprise, tout en restant connecté à ELFIS Core.',
  close:
    'Vous disposez ainsi d’outils adaptés à chaque métier sans transformer la plateforme en une interface gigantesque et difficile à utiliser.',
} as const

export const LANDING_SPACE_STORIES = {
  finance: {
    title: 'Gardez une vision claire de la situation financière de votre activité.',
    paragraphs: [
      'L’Espace Finance rassemble les outils nécessaires au suivi financier et administratif de l’entreprise.',
      'Facturation, comptabilité, trésorerie et opérations financières peuvent progressivement être réunies dans un environnement cohérent afin de limiter les ressaisies, mieux suivre l’activité et rendre les informations financières plus facilement exploitables.',
      'L’objectif n’est pas seulement de produire des documents financiers, mais de donner à l’entreprise une meilleure compréhension de ce qui se passe réellement dans son activité.',
    ],
  },
  commercial: {
    title: 'Transformez votre activité commerciale en processus structuré.',
    paragraphs: [
      'L’Espace Commercial accompagne le suivi de la relation client depuis les premières interactions jusqu’à la transformation d’une opportunité.',
      'Centralisez vos prospects, clients, opportunités et activités commerciales afin que les informations importantes ne restent plus dispersées entre des notes, des e-mails ou plusieurs outils différents.',
      'L’équipe dispose ainsi d’une vision plus claire de son pipeline et peut mieux suivre chaque étape de la relation commerciale.',
    ],
  },
  documents: {
    title: 'Vos documents ne devraient pas être de simples fichiers stockés quelque part.',
    paragraphs: [
      'L’Espace Documents centralise les informations documentaires de l’entreprise et prépare leur exploitation par les autres Espaces ELFIS.',
      'Contrats, factures, justificatifs, pièces administratives et autres documents peuvent être regroupés, recherchés et progressivement analysés afin de transformer une bibliothèque de fichiers en véritable ressource pour l’organisation.',
      'L’objectif est de retrouver plus rapidement l’information et d’éviter qu’un document important disparaisse dans un dossier, une boîte mail ou le poste d’un collaborateur.',
    ],
  },
} as const

export const LANDING_WORKFLOW = {
  eyebrow: 'Workflow connecté',
  title: 'De l’opportunité au paiement, l’information conserve son contexte.',
  paragraphs: [
    'Une relation commerciale peut commencer par un prospect dans l’Espace Commercial.',
    'Cette opportunité évolue, des documents sont générés ou reçus, puis l’opération donne lieu à une facturation et à un suivi financier.',
    'Dans une organisation fragmentée, une grande partie de ces informations doit être copiée d’un outil à l’autre.',
    'ELFIS vise au contraire à créer une continuité entre les étapes.',
  ],
  axis: 'Commercial → Documents → Finance',
  close: 'L’information accompagne progressivement le processus au lieu d’être reconstruite à chaque changement de métier.',
  steps: [
    { label: 'Prospect', space: 'Commercial' },
    { label: 'Opportunité', space: 'Commercial' },
    { label: 'Documents', space: 'Documents' },
    { label: 'Facturation', space: 'Finance' },
    { label: 'Suivi financier', space: 'Finance' },
  ],
} as const

export const LANDING_DATA = {
  title: 'Une donnée saisie ne devrait pas être recréée cinq fois.',
  paragraphs: [
    'Un client possède une identité, une adresse, des documents, des échanges commerciaux et des opérations financières.',
    'Dans beaucoup d’entreprises, ces informations sont pourtant enregistrées séparément dans plusieurs logiciels.',
    'ELFIS poursuit une logique différente : lorsqu’une information existe déjà et que les droits de l’organisation le permettent, elle doit pouvoir être réutilisée par les autres fonctions qui en ont besoin.',
  ],
  outcomes: ['Moins de ressaisie.', 'Moins d’incohérences.', 'Davantage de continuité.'],
  lineage: ['Client', 'Devis', 'Facture', 'Document', 'Comptabilité'],
} as const

export const LANDING_INDEPENDENTS = {
  eyebrow: 'Indépendants',
  title: 'Structurez votre activité aujourd’hui sans limiter votre croissance de demain.',
  paragraphs: [
    'Lorsqu’on travaille seul, chaque tâche administrative prend du temps sur le cœur de son activité.',
    'ELFIS aide les indépendants à centraliser progressivement leurs informations, leurs documents et leurs opérations dans un environnement plus structuré.',
    'Vous pouvez commencer simplement avec les fonctionnalités dont vous avez besoin, puis faire évoluer votre organisation lorsque votre activité se développe.',
    'L’objectif est d’éviter d’avoir à reconstruire tout votre système de gestion à chaque nouvelle étape de croissance.',
  ],
} as const

export const LANDING_COMPANIES = {
  eyebrow: 'Entreprises',
  title: 'Donnez à vos équipes un environnement commun.',
  paragraphs: [
    'Lorsqu’une entreprise grandit, le défi n’est plus seulement de disposer de bons outils. Il faut également permettre aux équipes de travailler ensemble sans créer de nouveaux silos.',
    'ELFIS offre une architecture commune dans laquelle chaque métier possède son propre environnement tout en restant rattaché à la même organisation.',
    'Les équipes commerciales travaillent dans Commercial. Les fonctions financières travaillent dans Finance. Les documents peuvent être centralisés dans Documents.',
    'Et l’entreprise conserve une logique commune d’identité, d’accès et d’information.',
  ],
} as const

export const LANDING_AUTOMATION = {
  eyebrow: 'Automatisation & IA',
  title: 'Automatiser ce qui peut l’être. Garder l’humain aux commandes.',
  paragraphs: [
    'L’intelligence artificielle doit simplifier le travail, pas rendre les décisions opaques.',
    'ELFIS intègre progressivement des capacités d’automatisation et d’analyse destinées à assister les utilisateurs dans les tâches répétitives ou nécessitant le traitement d’un grand volume d’informations.',
    'Analyse documentaire, extraction de données, classement, recherche, suggestions ou détection d’incohérences peuvent ainsi réduire certaines tâches manuelles.',
    'Les décisions importantes restent cependant intégrées à des processus contrôlés où l’utilisateur conserve la maîtrise.',
  ],
} as const

export const LANDING_DOC_INTELLIGENCE = {
  title: 'Transformer les documents en informations exploitables.',
  paragraphs: [
    'Une facture, un contrat ou un justificatif contient souvent des informations qui devront ensuite être saisies ailleurs.',
    'ELFIS cherche à réduire cette rupture.',
    'Grâce à l’analyse documentaire, certaines informations peuvent être détectées, structurées et proposées à l’utilisateur afin de préparer les étapes suivantes du processus.',
    'Le document cesse alors d’être uniquement une pièce jointe : il devient une source d’information capable d’alimenter progressivement le reste de l’organisation.',
  ],
} as const

export const LANDING_SEARCH = {
  title: 'Retrouver une information ne devrait pas devenir une enquête.',
  paragraphs: [
    'Lorsque les données sont réparties entre différents outils, retrouver un client, un document ou une opération peut rapidement devenir compliqué.',
    'ELFIS vise à rendre l’information plus accessible depuis un environnement commun et à faciliter progressivement la recherche à travers les différents métiers de l’entreprise.',
    'Le but : passer moins de temps à chercher l’information et davantage de temps à l’utiliser.',
  ],
} as const

export const LANDING_SECURITY = {
  eyebrow: 'Sécurité',
  title: 'Votre entreprise mérite un environnement maîtrisé.',
  paragraphs: [
    'Réunir davantage d’informations dans une plateforme implique de porter une attention particulière au contrôle des accès.',
    'ELFIS Core est construit autour d’une logique d’organisation, d’utilisateurs, de rôles et de permissions afin que les fonctionnalités et informations sensibles restent accessibles uniquement aux personnes autorisées.',
    'Authentification, contrôle des accès, séparation des organisations, traçabilité des opérations importantes et continuité du service font partie des principes qui structurent le développement de la plateforme.',
  ],
  pillars: [
    'Authentification',
    'Rôles et permissions',
    'Isolation des organisations',
    'Traçabilité',
    'Continuité de service',
  ],
} as const

export const LANDING_TRACEABILITY = {
  title: 'Comprendre ce qui s’est passé, quand cela est important.',
  paragraphs: [
    'Certaines opérations professionnelles nécessitent de pouvoir comprendre qui a réalisé une action et comment une information a évolué.',
    'ELFIS intègre progressivement des mécanismes de traçabilité afin de conserver davantage de contexte autour des actions importantes de l’organisation.',
    'Cette approche contribue à renforcer le contrôle interne et à rendre les processus plus faciles à suivre.',
  ],
} as const

export const LANDING_MODULAR = {
  eyebrow: 'Une plateforme modulaire',
  title: 'Commencez avec ce dont vous avez besoin. Faites évoluer le reste avec votre entreprise.',
  paragraphs: [
    'Toutes les entreprises n’ont pas les mêmes besoins au même moment.',
    'Un indépendant n’utilise pas nécessairement les mêmes outils qu’une société composée de plusieurs équipes.',
    'ELFIS est donc pensé comme une plateforme modulaire.',
    'Vous pouvez utiliser les Espaces nécessaires aujourd’hui et enrichir progressivement votre environnement lorsque de nouveaux besoins apparaissent.',
    'Vous ne changez pas de plateforme lorsque votre organisation évolue.',
  ],
  close: 'Votre environnement évolue avec elle.',
} as const

export const LANDING_UPCOMING = {
  eyebrow: 'Espaces à venir',
  title: 'L’écosystème ELFIS continue de grandir.',
  lead:
    'Finance, Commercial et Documents constituent les premiers Espaces de la plateforme. L’architecture ELFIS a cependant été pensée pour accueillir progressivement d’autres fonctions essentielles de l’entreprise.',
  note:
    'Ces Espaces sont présentés comme une vision d’évolution de la plateforme et ne doivent pas être considérés comme déjà disponibles.',
} as const

export const LANDING_WHY = {
  eyebrow: 'Pourquoi ELFIS',
  title: 'Un outil performant est utile. Un système cohérent peut transformer une organisation.',
  paragraphs: [
    'Le problème des entreprises n’est pas toujours l’absence de logiciels.',
    'Il est souvent lié au nombre de logiciels nécessaires pour faire fonctionner une seule organisation.',
    'ELFIS part d’une conviction simple : finance, commerce, documents et opérations devraient pouvoir fonctionner comme différentes parties d’un même système.',
    'C’est pourquoi nous construisons une plateforme commune plutôt qu’une accumulation d’applications indépendantes.',
  ],
} as const

export const LANDING_APPROACH = {
  eyebrow: 'Notre approche',
  title: 'La technologie doit simplifier l’entreprise, pas lui ajouter de la complexité.',
  paragraphs: [
    'Chaque fonctionnalité ELFIS doit répondre à un objectif concret : réduire une friction, améliorer l’accès à l’information, automatiser une tâche répétitive ou permettre une meilleure compréhension de l’activité.',
    'La plateforme doit rester suffisamment simple pour être utilisée au quotidien tout en étant suffisamment structurée pour accompagner une organisation lorsqu’elle devient plus complexe.',
  ],
} as const

export const LANDING_VISION = {
  eyebrow: 'Vision ELFIS',
  title: 'Construire le système opérationnel des entreprises de demain.',
  paragraphs: [
    'Notre ambition est de construire progressivement un environnement capable de relier les principales fonctions d’une entreprise.',
    'Un environnement dans lequel les équipes peuvent travailler sans perdre le contexte.',
    'Dans lequel l’information circule lorsque cela est nécessaire.',
    'Dans lequel les dirigeants peuvent disposer d’une vision plus cohérente de leur organisation.',
    'Et dans lequel de nouveaux métiers peuvent être ajoutés sans recréer un nouvel écosystème à chaque fois.',
    'ELFIS Core n’est donc pas pensé comme une application supplémentaire.',
  ],
  close: 'Il est pensé comme une infrastructure logicielle autour de laquelle l’entreprise peut progressivement s’organiser.',
} as const

export const LANDING_FINAL_CTA = {
  title: 'Votre entreprise mérite mieux qu’une collection d’outils isolés.',
  lead:
    'Regroupez progressivement vos métiers, vos équipes et vos informations dans un environnement conçu pour évoluer avec votre organisation.',
  tagline: 'Une plateforme. Une organisation. Plusieurs expertises.',
  discover: 'Découvrir ELFIS',
  start: 'Commencer',
  login: 'Se connecter',
} as const

export const LANDING_FOOTER = {
  tagline: 'Une plateforme. Une organisation. Plusieurs expertises.',
  columns: [
    {
      title: 'Produit',
      links: [
        { href: '#produit', label: 'La plateforme' },
        { href: '#espaces', label: 'Espaces' },
        { href: '#solutions', label: 'Workflow' },
        { href: '#securite', label: 'Sécurité' },
      ],
    },
    {
      title: 'Espaces',
      links: [
        { href: '#espace-finance', label: 'Finance' },
        { href: '#espace-commercial', label: 'Commercial' },
        { href: '#espace-documents', label: 'Documents' },
        { href: '#espaces-avenir', label: 'Espaces à venir' },
      ],
    },
    {
      title: 'Entreprise',
      links: [
        { href: '#pourquoi', label: 'Pourquoi ELFIS' },
        { href: '#vision', label: 'Vision' },
        { href: '/register', label: 'Commencer' },
        { href: '/login', label: 'Se connecter' },
      ],
    },
  ],
} as const

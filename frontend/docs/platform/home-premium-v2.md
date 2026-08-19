# P2.2 — ELFIS Home Premium V2

## Objectif

Transformer `/home` et le Launcher en expérience premium (Arc / Linear / Notion / Stripe / Vercel / Raycast), **sans** ajouter de logique métier.

Flux inchangé : Landing → Login → `/home` → choix Pilot → `/dashboard` | `/sales`.

## Principe « 1 seconde »

Chaque surface Home / Launcher doit être reconnaissable **ELFIS** même sans logo :

- Navy `#0B1F3A` + accent plateforme `#3D7EFF`
- Respiration / blanc / coins généreux / ombres très douces
- Cartes avec profondeur et accents Pilot (vert Compta, bleu Sales…)
- Pilot Mark **discret** (signature, pas dépendance)
- Typographie expressive + composition Hero haute

## Home Premium

Module `src/home/` :

| Section | Contenu |
|---------|---------|
| Hero | Bonjour, « Une plateforme. Toutes vos expertises. », meta cards Org / Workspace / Connexion |
| Continuer | Grande carte accent Pilot + CTA Continuer → ; sinon Commencer ComptaPilot / Découvrir SalesPilot |
| Applications | Cartes premium : logo, nom, description, 3 capacités, statut, CTA ; grisées si bientôt |
| Timeline | Verticale Aujourd’hui / Hier (mock + badge Aperçu) |
| Notifications | Mini centre : icône, titre, temps, produit, type (Aperçu) |
| Statut | Bandeau discret « Tout fonctionne » |

`data-home="premium-v2"`. Motion légère + `prefers-reduced-motion`.

## Launcher Premium

Desktop : **Dialog centré** ~1040px, backdrop flouté.  
Mobile : Drawer bas.

Contenu :

- Pilot Mark + titre
- Recherche (filtre local, pas de faux résultats)
- Applications récentes
- Toutes les applications (grandes cartes)
- Footer : Marketplace (disabled), Organisation, Paramètres, Compte

`data-launcher="premium-v2"`. Une seule implémentation `AppLauncher` / `AppLauncherPanel`.

## Hors scope

ComptaPilot / SalesPilot métier, Backend, Firebase, CRM, Facturation, Theme Engine, Landing, Login.

## Qualité

- Clavier, ARIA, focus visibles, reduced motion, contrastes
- Tests Home + Launcher panel + build TypeScript

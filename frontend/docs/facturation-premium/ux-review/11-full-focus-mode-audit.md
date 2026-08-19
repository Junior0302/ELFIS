# 11 — Full Focus Mode — Audit (F1.3.1.1)

Correctif UX ciblé : après choix de type, Composer doit occuper un **Full Focus** plein viewport jusqu’à sortie explicite. Pas de second shell — réutilisation / extension du Focus F1.3.1 + Composer Framework.

## Cartographie runtime

| Élément | Composant / fichier | Visible aujourd’hui (F1.3.1) | Visible Full Focus (cible) | Décision | Risque |
|---------|---------------------|------------------------------|----------------------------|----------|--------|
| Route Composer | `/facturation/nouveau?type=` — `App.tsx` → `FacturationComposerPage` | Oui | Oui (même route) | Conserver deep link ; pas de 2e route | Faible |
| Legacy wizard page | `FacturationWizardPage` (non routé) | N/A | N/A | Ignorer ; pas de route legacy active | Nul |
| Shell produit | `WorkspaceLayout` → `PlatformShell` + `ComptaProductNav` | Sidebar Compta visible | **Masquée** | `pathname.startsWith('/facturation/nouveau')` → pas de sidebar | Moyen (régressions Compta ailleurs) |
| PlatformTopbar | `PlatformTopBar` | Complet (menu, Apps, org, notifs, profil) | Minimal inchangé (hamburger, Apps, org, profil, notifs) | Conserver ; pas de fork Topbar | Faible |
| Search topbar | `PlatformSearch` | Oui | Oui (acceptable) | Garder | Nul |
| Guide Banner | `PageGuide` dans `WorkspaceLayout` | Oui | **Masqué** | Condition route Composer | Faible |
| SubscriptionBanner | `SubscriptionBanner` | Oui | Masqué en Focus | Évite bandeau parasite | Faible |
| Nav horizontale Facturation | `FacturationLayout` `fp-spaces__nav` | Déjà `hidden` sur `/nouveau` | Toujours masquée | Conserver | Nul |
| KPI / Overview | `FacturationOverviewPage` | Pas sur Composer | Absentes | RAS | Nul |
| Focus flag body | `document.body.dataset.fpFocus` | Oui si `useComposerFocus` | Oui, forcé tant que sur route | Persistance route-based | Faible |
| `useComposerFocus` | `composer-framework/useComposerFocus.ts` | `initialEnabled: true` | Toujours on sur route | Étendre config (`hideProductSidebar`) | Faible |
| `ComposerLayout` | `ComposerContainer.tsx` | Focus partiel (`elf-cmp--focus`) | Wrappé / étendu par `ComposerFocusLayout` | Réutiliser slots header/editor/preview | Moyen |
| Sidebar wizard 10 steps | `ComposerSidebar` | Déjà off (`showSidebar={false}`) | Off | Conserver | Nul |
| Preview PDF | `ComposerPreview` | Sticky partiel | Panneau ~32–38 %, hauteur viewport | CSS Focus uniquement | Faible |
| Post-création | Message inline / stay | Pas de confirmation structurée | Panel Focus : Ouvrir / Documents / Créer autre | UI only | Faible |
| Exit | `requestExit` + `ConfirmDialog` | OK | OK + Retour header | Conserver dirty check | Faible |
| Refresh / deep link | `?type=` | Recharge Composer + shell classique | Recharge **en Focus** | Shell conditionné path | Faible |
| Pickers / overlays | Customer/Product picker | Overlay | Overlay dans Focus | Pas de changement métier | Faible |
| Relations create | CustomerPicker `allowCreate` | Peut ouvrir flux externe | Retour → même route Focus | Hors scope profond Client | Moyen |

## Cause racine (F1.3.1 GO vs Full Focus)

F1.3.1 masque uniquement la **nav secondaire Facturation**. Le chrome Compta (`WorkspaceLayout` : sidebar + Guide) reste actif → sensation « page classique dans le shell ».

## Stratégie

1. Détecter Full Focus au niveau `WorkspaceLayout` (path) — masquer sidebar, Guide, banner.
2. Étendre `FacturationLayout` / CSS espaces déjà Focus.
3. Introduire `ComposerFocusLayout` (framework) autour du freeform existant.
4. Persistance = **route** + `data-fp-full-focus` ; jamais `disableFocus` tant qu’on reste sur `/nouveau`.
5. Sortie explicite uniquement → Documents / Annuler / Ouvrir doc / Créer autre.

## Hors scope

Moteurs métier, APIs, calculs, PDF engine, Vault, mailer, refonte Client/Produit profonde, F1.4.

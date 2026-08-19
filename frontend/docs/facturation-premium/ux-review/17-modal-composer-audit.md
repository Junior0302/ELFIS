# 17 — Modal Composer Audit (F1.3.1.2)

## Verdict cause exacte

Le passage en **page Composer pleine** ne vient pas du shell Focus lui-même, mais de la **navigation route** après la pop-in type.

| Étape | Comportement actuel (F1.3.1.1) | Effet UX |
|-------|-------------------------------|----------|
| 1 | Documents monté (`FacturationDocumentsPage` → `FacturationPage`) | OK |
| 2 | Clic « Créer un document » → `NewDocumentDialog` (`size="sm"`) | Petite pop-in OK |
| 3 | « Créer le document » → `onOpenChange(false)` **puis** `navigate('/facturation/nouveau?type=…')` | Overlay **fermé** |
| 4 | Route sibling `facturation/nouveau` → `FacturationComposerPage` | **Documents démonté** |
| 5 | `isComposerFullFocusPath` + `FacturationLayout` full-focus | Page Focus plein viewport (intention F1.3.1.1) |

**Cause exacte :** `NewDocumentDialog.create()` ferme l’overlay et remplace la route Documents par `/facturation/nouveau`, ce qui démonte Documents et affiche Composer comme page indépendante (Full Focus). Ce n’est pas un bug Overlay Manager : c’est le contrat F1.3.1.1 (route = Focus).

## Inventaire

| Élément | Fichier | Rôle | Action F1.3.1.2 |
|---------|---------|------|-----------------|
| Petite pop-in | `NewDocumentDialog.tsx` | Choix type | STATE 1 du flux modal unifié |
| Événement Créer | `create()` → navigate `/nouveau` | Quitte Documents | Remplacer par sync URL `/documents/new` **sans** démonter Documents |
| Page Documents | `FacturationDocumentsPage.tsx` / `FacturationPage.tsx` | Liste + trigger | Rester montée ; inert sous modal |
| Route Composer | `App.tsx` `path="nouveau"` | Page Focus | Redirect → `documents/new` ; nested sous Documents |
| ComposerFocusLayout | `composer-framework/ComposerFocusLayout.tsx` | Layout éditeur/preview | Réutilisé **dans** `ComposerDialog` |
| Draft / autosave | `FacturationComposerPage.tsx` | État brouillon | Inchangé métier ; `onRequestClose` modal |
| Retour Documents | `requestExit` / `exitToDocuments` | navigate Documents | Fermer modal + refresh liste (`?doc=`) |
| Overlay / Manager | `Dialog` + `useOverlayBehaviour` | Trap, Escape, scroll lock | Une surface modale continue (type→composer) |
| Focus shell | `WorkspaceLayout.isComposerFullFocusPath` | Masque chrome sur `/nouveau` | Ne plus masquer chrome pour modal ; Documents + overlay |
| Refresh / deep link | `/nouveau?type=` | Full Focus page | `/documents/new?type=` → Documents + ComposerDialog |

## Flash Documents

Séquence actuelle : fermeture dialog → Documents visible un instant → montage page `/nouveau`.  
Cible : **ne pas** fermer l’overlay entre STATE 1 et STATE 2 ; agrandir / remplacer le contenu (150–220 ms).

## Hors scope (rappel)

Pas d’APIs/calculs/PDF engine/tables/Vault/mailer/Billing. Pas design final Client/Produit. Pas F1.4.

# 31 — Rapport GO / NO GO — F1.3.1.3 Composer Modal Workflow

## Verdict : **GO**

## Critères GO (14)

| # | Critère | Statut |
|---|---------|--------|
| 1 | Diagnostic 24 cause exacte OverlayRouteBridge / route_change | GO |
| 2 | Une state machine ComposerModalStage | GO |
| 3 | Petite pop-in ne ferme pas le flux (ENTER_COMPOSER only) | GO |
| 4 | DocumentCreationModalRoot persistant (1 portail) | GO |
| 5 | Grand modal ~92–95vw × 88–92vh | GO |
| 6 | Documents montée derrière (inert / blur) | GO |
| 7 | Router robuste ; URL ne ferme pas le modal | GO |
| 8 | Redirects invalides (vide / sans client / lignes) supprimés | GO |
| 9 | Type persisté dans machine + URL | GO |
| 10 | Transition 150–240 ms + reduced-motion | GO |
| 11 | Erreurs / loading dans le modal | GO |
| 12 | Focus trap / Escape selon stage / restore Documents | GO |
| 13 | Tests MM01–40 + MV01–20 doc | GO |
| 14 | Docs 24–31 + `npm run build` | GO (`tsc -b && vite build` OK 2026-08-02) |

## Fichiers clés

- `workflow/composerModalMachine.ts`
- `ComposerDialog.tsx` (`DocumentCreationModalRoot`)
- `DocumentCreateFlow.tsx`
- `FacturationComposerPage.tsx` (`forcedDocType`, plus de Navigate vide)
- Tests MM + MC (OverlayRouteBridge)
- Docs 24–31

## Hors scope

Pas F1.4. Pas setTimeout anti-fermeture. Pas APIs/calculs/Vault/mailer/Billing. Pas commit.

## STOP

Phase F1.3.1.3 terminée. **Ne pas commencer F1.4.**

> **Note F1.3.2** : le contenu Composer modal est désormais un parcours guidé 6 étapes (docs 32–39). Le root modal de F1.3.1.3 reste la base.

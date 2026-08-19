# 13 — Test plan UXU01–60

Légende : **V1** = Vague 1 (à exécuter maintenant) · **F** = futur Vague 2+

| ID | Cas | Vague | Auto |
|----|-----|-------|------|
| UXU01 | ElfisUnifiedShell monte `data-platform-shell` | V1 | oui |
| UXU02 | Même structure topbar Core/Compta/Sales (menu + brand) | V1 | oui |
| UXU03 | Un seul hamburger topbar (pas toggle sidebar) | V1 | oui |
| UXU04 | Pastille Pilot visible Compta/Sales, masquée Home config | V1 | oui |
| UXU05 | Collapse Compta sync `ps-shell--sidebar-collapsed` | V1 | oui |
| UXU06 | Collapse Sales sync largeur 56px | V1 | oui |
| UXU07 | Tokens PLATFORM_SHELL_DIMENSIONS 240/56/64 | V1 | oui |
| UXU08 | PlatformPageContainer classes up-page | V1 | oui |
| UXU09 | PlatformGrid cols 12/8/4 | V1 | oui |
| UXU10 | GridItem span | V1 | oui |
| UXU11 | PilotTheme Core navy / Compta vert / Sales bleu | V1 | oui |
| UXU12 | Flag UNIFIED_PLATFORM_UI défaut true | V1 | oui |
| UXU13 | Flag off retire up-shell--unified | V1 | oui |
| UXU14 | Routes /home /dashboard /sales inchangées (layouts branchés) | V1 | manuel + smoke |
| UXU15 | build frontend OK | V1 | npm run build |
| UXU16 | Régression UI.P2 hamburger → drawer | V1 | tests existants |
| UXU17 | Régression UI.P1 collapse Compta | V1 | tests existants |
| UXU18–20 | Captures Home / Compta / Sales dashboards | V1 | **manuel STOP** |
| UXU21–30 | PageHeader / KPI row harmonisés | F | — |
| UXU31–40 | Cards / empty states | F | — |
| UXU41–50 | Tables / listes | F | — |
| UXU51–60 | Pages secondaires | F | — |

## Commandes

```bash
cd frontend
npx vitest run src/unified-platform src/platform-shell/redundant-menu-button.test.tsx src/platform-shell/sidebar-collapse.test.tsx
npm run build
```

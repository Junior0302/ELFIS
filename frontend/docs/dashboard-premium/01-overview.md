# 01 — Overview (S1.2.6 Financial Command Center Premium V2)

**Date :** 2026-08-02  
**Route :** `/dashboard`  
**Produit :** ComptaPilot  
**Objectif :** présentation premium (Stripe / Linear / Vercel / Notion / Mercury) **sans** nouvelle fonctionnalité métier.

## Principes

- Données **uniquement** via `financialApi.overview` (Financial Engine).
- Aucun chiffre inventé ; empty states honnêtes et premium.
- Identité ComptaPilot : vert comptable, navy, fond clair.
- Pas de purple-on-white, glow excessif, pills massives.
- `prefers-reduced-motion` respecté.

## Hors périmètre (STOP S1.3)

- Pas d’API / DB / Financial Engine / IA nouveaux.
- Pas de SalesPilot, ELFIS Home, Launcher, Command Center global.
- Pas de logique métier `/finance`.

## Marqueur runtime

`data-fcc-layout="s126"` sur le root FCC.

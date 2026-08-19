# HOME.0 — Test plan

## Automatisé (smoke)

```bash
cd frontend
npx vitest run src/home/ElfisHomePage.test.tsx src/home/lastProduct.test.ts
npx vitest run src/unified-platform/page-frame-layout.test.tsx src/unified-platform/blind-template-identity.test.tsx src/unified-platform/spatial-system.test.tsx
npm run build
```

### Assertions clés `ElfisHomePage.test.tsx`

- Hero cockpit + visual orbit
- Résumé journée + empty finance honnête
- « Vos espaces » présent ; « Vos applications » absent
- Timeline empty réelle
- Intelligence + disclaimer + « Tout traiter » si unread
- Quick actions → routes existantes
- lastProduct → Reprendre / Ouvrir / Historique
- Pas de « 2 factures » / « 3 prospects »

## Viewport checklist (Chris)

| Viewport | Largeur | Checks |
|----------|---------|--------|
| Desktop | ≥ 1440 | Hero 2 colonnes, résumé 4 cartes, secondary sticky |
| Laptop | 1024–1439 | Hero lisible, 4 cartes wrap 2×2, quick actions wrap |
| Tablet | 768–1023 | Hero stack, espaces 1–2 cols, CTA journée visible sans scroll excessif |
| Mobile | ≤ 640 | Une colonne, orbit réduit, continue CTAs wrap |

### Smoke visuelle manuelle

1. `/home` authentifié — pas de KPI inventés
2. Sans `lastProduct` — empty continue excellent
3. Avec `lastProduct=salespilot` — Reprendre Commercial
4. Unread > 0 — signal + « Tout traiter »
5. `prefers-reduced-motion` — orbit sans animation

## STOP validation

Livraison HOME.0 prête pour revue Chris — **pas de commit** tant que non validé.

# Landing ELFIS Core V1 — notes techniques

**Phase :** P1.3  
**Route :** `/` → `HomePage` → `LandingPage`  
**Dossier :** `frontend/src/landing/`

## Architecture

```
landing/
├── LandingPage.tsx
├── landing.css
├── components/   (Logo, HeroPilotCard, Timeline, FeatureCard, PartnerLogos, icons)
└── sections/     (Navbar, Hero, Applications, Workflow, Benefits, Partners, Features, CTA, Footer)
```

## Identité

- Thème plateforme : `RuntimeThemeSync` sur `/` → `elfis-core` (inchangé).
- Logo : **`/favicon.svg`** — même asset que ComptaPilot / shells legacy.
- Couleurs Pilot : modifiers CSS Brand Book (pas de style inline).
- Boutons : classes Design System `.btn` / `.btn.secondary`.

## Motion

CSS only (`transform` / `opacity`).  
`prefers-reduced-motion: reduce` coupe orbites / float / flux.

## Remplacement logos partenaires

Éditer `PartnersSection` : renseigner `src` sur chaque `PartnerLogoItem`.

## Qualité

- TypeScript / `tsc -b` : OK  
- `vite build` : OK  
- Lighthouse (preview local, headless) : Performance **85** · Accessibility **98** · Best Practices **100**

## Hors scope

Brand Book, Theme Engine, Design System core, Pilot Mark assets runtime officiels — non modifiés.

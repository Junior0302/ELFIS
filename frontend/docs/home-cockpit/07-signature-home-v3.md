# Signature Home V3 — le meilleur Home ELFIS

**Date :** 2026-08-04  
**Scope :** `/home` uniquement — pas de commit · FCC / Sales / Facturation inchangés  
**Marker :** `data-home-layout="cockpit-signature-v3"` · `data-cockpit-os="signature-v3"`

## Vision

Home = **cockpit OS 8h00** : calme, maîtrise, intelligence premium.  
Pas un dashboard, pas un app store, pas une landing.  
L’utilisateur traverse des **domaines** d’une entreprise unique ; les Pilots n’apparaissent qu’en microtexte « Propulsé par… ».

## Composition finale (ordre = intention)

| Zone | Question | Surface |
|------|----------|---------|
| **Hero signature** | Important + Attention | Navy dominant, orbit vivant, signaux réels, CTA journée + secondaire |
| **Pulse journée** | Important (glance) | 4 chips horizontaux — pas de KPI inventés |
| **Command deck** | Conseil + gestes | Insight Framework (inline) + Quick Actions — **avant** le remplissage |
| **Continuer** | Reprendre où ? | `lastProduct` réel / empty excellent |
| **Espaces** | Domaines métier | Finance / Commercial / Documents / RH — tiles denses |
| **System rail** | Activité + santé | Timeline + Health intégrés |
| **Ops** | Navigation OS | Micro-bande, pas une carte |

## Wow moments (<5s)

1. Hero navy + atmosphère + orbit micro-animé  
2. Signaux « Aujourd’hui ELFIS a détecté » (ou empty calme)  
3. Command deck : insights déterministes branchés Insight Framework  
4. Entrées staggered ~180–220ms (`prefers-reduced-motion` respecté)

## Honesty map

| Source | Usage Home |
|--------|------------|
| `useAuth` | prénom, org, rôle |
| `useSync` | unread, mode, lastTick |
| `lastProduct` | reprise + pulse domaines |
| `api.listNotifications` | timeline |
| `HOME_APP_CARDS` | routes / disponibilités espaces |
| Signaux dérivés | hero + Intelligence (pas d’IA générative) |

**Jamais :** factures/prospects inventés, voyants Health inventés, mocks timeline.

## Avant (v2) → Après (v3)

| Affaiblissement v2 | Correction v3 |
|--------------------|---------------|
| Command après Continuer/Espaces | Command **en tête** du primary |
| Intelligence = liste texte | **InsightList** Framework |
| Day = 4 mini-cartes | Pulse chips horizontaux |
| Hero OS correct mais plat | Hero **signature** (atmosphère, double CTA) |
| Stack perceptuelle | Peu d’excellentes surfaces + rythme |

## Fichiers

- `ElfisHomePage.tsx`, `CockpitHero.tsx`, `DaySummarySection.tsx`
- `ElfisIntelligenceCard.tsx`, `homeInsights.ts`
- `home.css` (couche Signature V3)
- Tests : `ElfisHomePage.test.tsx`, `homeInsights.test.ts`

## Validation

```bash
cd frontend
npx vitest run src/home
npm run build
```

**STOP revue Chris.**

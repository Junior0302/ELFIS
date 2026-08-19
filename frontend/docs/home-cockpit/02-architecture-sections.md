# HOME.0 — Architecture des sections

```
ElfisHomePage
├── ElfisDashboardTemplate (frame unifié Home/FCC/Sales — structure seule)
│   ├── header → CockpitHero + CockpitHeroVisual
│   ├── metrics → DaySummarySection (4 ElfisSurfaceCard)
│   ├── primary → ContinueWorkCard · SpacesSection · ElfisIntelligenceCard · QuickActionsGrid
│   ├── secondary → GlobalTimeline · HealthCenter
│   └── operations → raccourcis plateforme
└── homeSignals.ts (dérivation honnête)
```

## Sources branchées

| Source | Usage |
|--------|--------|
| `useAuth` | prénom, org, rôle, token |
| `useSync` | unread, mode, lastTick |
| `lastProduct` | reprise session |
| `HOME_APP_CARDS` / catalog | routes & disponibilités espaces |
| `api.listNotifications` | timeline (pas de mock fallback) |

## Composants réutilisés (DS / Unified)

- `ElfisDashboardTemplate`, `ElfisPageFrame` (via template)
- `ElfisSurfaceCard`, `ElfisButtonLink`, `ElfisEmptyState`, `MotionPage`
- `PlatformGrid`, `GridItem`
- `QuickActionCard` (design-system)

## Composants Home (composition cockpit)

- `CockpitHero`, `CockpitHeroVisual`
- `DaySummarySection`, `SpacesSection`
- `ContinueWorkCard` (évolué)
- `GlobalTimeline`, `ElfisIntelligenceCard`
- `QuickActionsGrid`, `HealthCenter`
- `homeSignals.ts`

## Legacy conservé (non affiché cockpit)

- `HomeApplicationsGrid`, `HomeApplicationCard`, `RecentActivityPanel` (mock), `HomeHero` — non montés dans la composition HOME.0

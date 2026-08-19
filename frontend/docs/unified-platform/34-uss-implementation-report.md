# 34 — Implementation report UX.UNIFY.1.2

## GO (14 points)

1. Frame max-width **1680px** sur Home / FCC / Sales  
2. Padding inline 32/24/20/16  
3. Viewport pad **0** (pas de double container)  
4. Sidebar **navy** Core + Compta + Sales  
5. Accent Pilot seulement actif / focus / icône  
6. Sidebar dims UI.P1 240/56 partout (Home plus 190)  
7. Template sections Header→…→RecentActivity  
8. Home composition 8+4 ×3  
9. FCC composition KPI / 8+4 / 6+6 / 8+4  
10. Sales même squelette, pas colonne étroite  
11. MetricCard min 132 ; Chart clamp / weak  
12. Header FR « Tableau de bord » ×3  
13. Tests USS + docs 26–34  
14. Pas de migration pages secondaires  

## STOP

**STOP pour captures / validation Chris (USM).** Pas de commit. Pas pages secondaires.

## Fichiers clés

- `primitives/ElfisPageFrame.tsx`, `ElfisDashboardTemplate.tsx`, `ChartCard.tsx`, `ResponsiveChartFrame.tsx`
- `unified-platform.css`, `platformTokens.ts`
- `ElfisHomePage.tsx`, `FinancialCommandCenter.tsx`, `SalesDashboardPage.tsx`
- `docs/unified-platform/26–34`
- `spatial-system.test.tsx`

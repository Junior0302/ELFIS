# 09 — Intégrations (présentation only)

## Financial Command Center

| Zone | Mapping | Composant |
|------|---------|-----------|
| Priorités du jour | `mapDayPrioritiesToInsights` | `InsightList` + `renderAction` → `Link` |
| Alertes financières | `mapFinancialAlertsToInsights` | `InsightList` |
| Health message + conseils | `mapHealthToInsights` | `InsightList` inline |
| Assistant (tip) | premier `health:tip:*` | `InsightInline` |

**Inchangé :** `buildDayPriorities`, API overview, gauge, calculs KPI.

## Document Composer / validation

`ComposerValidation` délègue à `InsightList` (`variant="inline"`) via `mapComposerIssuesToInsights`.

Contrat `ComposerValidationIssue` **conservé** (pages Facturation inchangées côté données).

## Fallback

Mapper → `null` / filtre → empty state InsightList (message configuré). Aucune donnée synthétique.

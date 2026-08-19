# 02 — Contrat Insight

## Principes

- Produit-agnostique, **indépendant des Pilots**
- Présentation uniquement — pas de calcul, pas d’invention
- Champs optionnels absents = **non affichés**

## Shape

```ts
type Insight = {
  id: string
  type: InsightType
  severity: InsightSeverity
  title: string
  summary: string
  details?: string          // zone « Pourquoi ? »
  source?: InsightSource    // réel uniquement
  confidence?: InsightConfidence  // fournie uniquement
  timestamp?: string
  actions?: InsightAction[]
  dismissible?: boolean
  expandable?: boolean
  context?: InsightContext
  linkedResource?: InsightLinkedResource
}
```

## Règles

| Champ | Règle |
|-------|--------|
| `confidence` | Jamais inventée ; si absente → pas de UI confiance |
| `source` | Uniquement id/label issus de la donnée source |
| `details` | Contenu réel ; collapsible si `expandable !== false` |
| `actions` | Configurables ; libellés standard ou override fourni |
| `linkedResource` | Référence optionnelle — pas de fake id |

## Mappers officiels V1

| Source | Fonction |
|--------|----------|
| `FinancialAlert` | `mapFinancialAlertToInsight` |
| `DayPriority` | `mapDayPriorityToInsight` |
| `HealthScore` + `recommendations[]` | `mapHealthToInsights` |
| `ComposerValidationIssue` | `mapComposerIssueToInsight` |

Retour `null` (ou filtre) si `id` / titre / message manquant.

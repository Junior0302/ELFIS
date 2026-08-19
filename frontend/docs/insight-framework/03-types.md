# 03 — Types & familles

## Familles (`InsightType`)

| Type | Libellé FR | Couleur DS | Icône | Rôle ARIA défaut | Priorité défaut |
|------|------------|------------|-------|------------------|-----------------|
| `information` | Information | `--pilot-info` | info | status | Info |
| `success` | Succès | `--pilot-success` | success | status | Info |
| `attention` | Attention | `--pilot-warning` | attention | status | High |
| `critical` | Critique | `--pilot-danger` | critical | alert | Critical |
| `suggestion` | Suggestion | `--pilot-info` | suggestion | status | Medium |
| `opportunity` | Opportunité | `--pilot-success` | opportunity | status | Medium |
| `analysis` | Analyse | `--pilot-info` | analysis | status | Low |
| `confirmation` | Confirmation | `--pilot-warning` | confirmation | status | Medium |

## Sévérité (`InsightSeverity`)

`critical` → `high` → `medium` → `low` → `info`

La sévérité **override** le rang d’affichage (`sortInsightsByPriority`). Un type `suggestion` avec `severity: 'critical'` remonte en tête.

## Mapping sources → type / severity

| Source | → type | → severity |
|--------|--------|------------|
| Alert `critical` | critical | critical |
| Alert `warning` | attention | high |
| Alert `info` | information | info |
| Priority `normal` | suggestion | medium |
| Composer `error` | critical | critical |
| Composer `warning` | attention | high |
| Composer `suggestion` | suggestion | medium |
| Health message | analysis | low |
| Health tip | suggestion | medium |

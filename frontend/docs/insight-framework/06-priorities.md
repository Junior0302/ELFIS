# 06 — Priorités

## Hiérarchie d’affichage

| Rang | Severity | Usage typique |
|------|----------|---------------|
| 0 | `critical` | Blocage / risque immédiat |
| 1 | `high` | Vigilance forte |
| 2 | `medium` | Suggestion / opportunité |
| 3 | `low` | Analyse secondaire |
| 4 | `info` | Information neutre |

API : `severityRank`, `compareInsightPriority`, `sortInsightsByPriority`.

## Distinction OverlayPriority

La priorité **overlay** du Design System (`passive|floating|panel|modal|critical`) gère le **stack UI** des couches — ce n’est **pas** la priorité métier Insight. Ne pas mélanger les enums.

## FCC

`DayPriority.level` est mappé vers `InsightSeverity` (`normal` → `medium`) sans changer `buildDayPriorities` (calculs inchangés).

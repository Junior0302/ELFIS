# 11 — Plan de tests IF01–IF40

Tous les items : **À tester manuellement** (complément des tests Vitest automatisés).

| ID | Scénario | À tester manuellement |
|----|----------|------------------------|
| IF01 | InsightCard information | Rendu badge Information + summary |
| IF02 | InsightCard succès | Couleur success DS |
| IF03 | InsightCard attention | Warning tone |
| IF04 | InsightCard critique | `role="alert"` + danger |
| IF05 | Suggestion | Badge Suggestion |
| IF06 | Opportunité | Badge Opportunité |
| IF07 | Analyse | Badge Analyse |
| IF08 | Confirmation | Badge Confirmation |
| IF09 | Severity Critical en tête de liste | Tri correct |
| IF10 | Severity Info en bas | Tri correct |
| IF11 | Confiance absente | Aucun texte « Confiance » |
| IF12 | Confiance fournie | Affichage Élevée/Moyenne/Faible |
| IF13 | Source absente | Pas de footer source |
| IF14 | Source réelle | Affichage discret |
| IF15 | Zone Pourquoi ? fermée | Details masqués |
| IF16 | Zone Pourquoi ? ouverte | Details visibles + aria |
| IF17 | Action Voir | Label + clic |
| IF18 | Action Corriger | Label |
| IF19 | Action Ignorer | dismissible |
| IF20 | Action Réessayer | onClick |
| IF21 | Action Ouvrir | href / Link FCC |
| IF22 | Action Comprendre | Label |
| IF23 | InsightInline Composer | Issues validation |
| IF24 | InsightBanner | Layout bandeau |
| IF25 | InsightToast | status + live |
| IF26 | InsightList vide | emptyMessage |
| IF27 | InsightStack max | Truncation visuelle |
| IF28 | Focus clavier actions | Tab + Enter |
| IF29 | Reduced motion | Pas d’animation |
| IF30 | Contraste critique | Lisible |
| IF31 | FCC priorités | Mapping DayPriority |
| IF32 | FCC alertes | Mapping FinancialAlert |
| IF33 | FCC health tips | Conseils moteur Insights |
| IF34 | Composer error | Type critical |
| IF35 | Composer suggestion | Type suggestion |
| IF36 | Mapper alerte invalide | null / empty |
| IF37 | Pas de régression KPI FCC | Valeurs Engine |
| IF38 | Pas de régression Composer focus | Mode focus OK |
| IF39 | Widget containers FCC | Toujours présents |
| IF40 | Build production | `npm run build` OK |

## Automatisés

`frontend/src/insight-framework/insight-framework.test.tsx` — contrat, mappers, composants.

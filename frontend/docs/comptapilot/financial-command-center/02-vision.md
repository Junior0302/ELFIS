# 02 — Vision

## Problème

L’ancien `/dashboard` mélangeait onboarding ELFIS (LaunchDashboard), centre de commande générique et un résumé financier. L’utilisateur comptable ne voyait pas immédiatement quoi décider.

## Vision V1

Le **Financial Command Center** est la **page d’accueil opérationnelle** de ComptaPilot :

- **Situation** en un coup d’œil (KPI Engine)
- **Décision** (priorités + alertes)
- **Compréhension** (Health Score avec disclaimer)
- **Exécution** (actions comptables / financières uniquement)
- **Explication** (Assistant financier existant)

## Principes

1. **Source unique** : Financial Engine via `financialApi` — zéro chiffre inventé côté UI.
2. **Décision first** : la section « Décider » est priorisée sur mobile.
3. **Framework générique** : widgets ELFIS réutilisables hors Compta (autres pilots plus tard).
4. **Séparation d’intensité** : `/dashboard` = command center ; `/finance` = analyse complète.
5. **Pas d’onboarding produit** sur cette surface — le setup org reste dans ELFIS Core.
